import json
import re
import traceback

from dotenv import load_dotenv
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from services.logger.logger_service import default_logger
from services.bot_service import bot_service
from utils.mongo_wrapper import (
    generate_execution_id,
    mark_execution_failed,
    save_execution_start,
)
from utils.utils import show_available_commands
from workflows.generate_pages import GeneratePagesWorkflow
from services.sheets_service.sheets_singletone import SheetsSingleton
from services.sheets_service.google_sheet_stratergy import GoogleSheetStrategy
from config.settings import SPREADSHEET_ID, BASE_DIR
from workflows.publish_approved import PublishApprovedWorkflow

load_dotenv()


def lambda_function(event, context=None):
    """
    Worker Lambda: Processes Slack events forwarded from gateway lambda.
    Handles all business logic: AI calls, MongoDB, Slack responses.
    """
    default_logger.info(f"Worker lambda received event: {json.dumps(event)}")
    default_logger.info("SSL configuration loaded")

    try:
        # Event comes from gateway lambda, not API Gateway
        # Gateway forwards the complete Slack payload
        if isinstance(event, dict) and "event" in event:
            # Direct Slack payload from gateway
            event_data = event.get("event", {})
        else:
            # Fallback: try to parse if it's a string
            if isinstance(event, str):
                event = json.loads(event)
                event_data = event.get("event", {})
            else:
                default_logger.error("Invalid event format received from gateway")
                return {"status": "error", "message": "Invalid event format"}

        event_type = event_data.get("type")
        ts = event_data.get("ts")
        user_id = event_data.get("user", "unknown")
        event_text = event_data.get("text", "")

        default_logger.info(
            f"Processing event type: {event_type}, ts: {ts}, user: {user_id}"
        )

        # Handle both app_mention events and message events that mention the bot
        # Slack sometimes sends message events even when bot is mentioned
        is_bot_mentioned = (
            event_type == "app_mention" or 
            (event_type == "message" and event_text and "<@" in event_text and not event_data.get("bot_id"))
        )

        if is_bot_mentioned:
            # Extract command from message
            print("event_data: ", event_data)
            markdown_text = event_data.get("text", "").strip()

            # Remove bot mention FIRST before markdown processing
            text = re.sub(r"<@[^>]+>", "", markdown_text).strip()
            text = re.sub(r"[`*_>]", "", text).strip()

            if not text:
                default_logger.warning("No command text found")
                return {"status": "success", "message": "Empty command processed"}

            # Split command and args
            lines = text.splitlines()
            command_line = lines[0].strip()
            command_parts = command_line.split()
            command = command_parts[0]
            command_args = command_parts[1:] if len(command_parts) > 1 else []
            additional_lines = [line.strip() for line in lines[1:] if line.strip()]
            # Process commands
            if command == "/generatepages":
                default_logger.info("Processing /generate_pages command")

                # Combine command args and additional lines to form the question

                # Generate execution id and save start record
                execution_id = generate_execution_id()
                save_execution_start(
                    execution_id=execution_id,
                    workflow_type="generate_pages",
                    triggered_by=user_id,
                    slack_command=text,
                )

                # Process command (this will send Slack responses)
                workflow = GeneratePagesWorkflow(
                    sheets_singleton=SheetsSingleton(
                        strategy=GoogleSheetStrategy(
                            credentials_file=f"{BASE_DIR}/google_credentials.json",
                            sheet_id=SPREADSHEET_ID, 
                            scopes=["https://www.googleapis.com/auth/spreadsheets"]
                        )
                    )
                )
                
                # Generate pages (now synchronous, no event loop needed)
                count, demo_url_link = workflow.generate_pages()
                bot_service.send_message(f"{count} pages are generated successfully demo url: {demo_url_link}", ts)
                return {"status": "success", "message": "Pages generated successfully"}

            elif command == "/publish_approved":
                # Combine command args and additional lines to form the search query
                default_logger.info("Processing /publish_approved command")

                # Generate execution id and persist start record
                execution_id = generate_execution_id()
                save_execution_start(
                    execution_id=execution_id,
                    workflow_type="search_query",
                    triggered_by=user_id,
                    slack_command=text,
                )

                publish_workflow = PublishApprovedWorkflow(
                    sheets_singleton=SheetsSingleton(
                        strategy=GoogleSheetStrategy(
                            credentials_file=f"{BASE_DIR}/google_credentials.json",
                            sheet_id=SPREADSHEET_ID, 
                            scopes=["https://www.googleapis.com/auth/spreadsheets"]
                        )
                    )
                )

                count, url = publish_workflow.publish_approved()
                bot_service.send_message(f"{count} pages are generated successfully publish url: {url}", ts)
                return {
                    "status": "success",
                    "message": f"Search processed (ID: {execution_id})",
                }
            
            # elif command == "/create_landing_page":
            #     default_logger.info("Processing /create_landing_page command")
            #     # TODO: Implement create_landing_page workflow
            #     bot_service.send_message("Create landing page feature coming soon!", ts)
            #     return {
            #         "status": "success",
            #         "message": "Create landing page command received",
            #     }
            else:
                # Handle unknown commands
                show_available_commands(ts)
                return {
                    "status": "success",
                    "message": f"Unknown command handled: {command}",
                }
        else:
            # For non-app_mention events, just return success
            default_logger.info(f"Ignoring non-app_mention event: {event_type}")
            return {"status": "success", "message": "Non-mention event ignored"}

    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        error_msg = "Database connection temporarily unavailable"
        default_logger.error(f"MongoDB connection error: {str(e)}")
        if "ts" in locals():
            bot_service.send_error_message(error_msg, ts)
        return {"status": "error", "message": error_msg}

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        stack_trace = traceback.format_exc()

        default_logger.error(f"Worker lambda error: {error_type} - {error_msg}")
        default_logger.error(f"Stack trace:\n{stack_trace}")

        # Try to send error message to Slack
        if "ts" in locals():
            bot_service.send_error_message(f"Error processing command: {error_msg}", ts)

        # Try to mark execution as failed
        if "execution_id" in locals():
            mark_execution_failed(execution_id=execution_id, error_message=error_msg)

        return {"status": "error", "message": f"Processing failed: {error_type}"}
