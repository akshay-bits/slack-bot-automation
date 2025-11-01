# Import SSL configuration FIRST - before any other imports
import json
import logging
import os

import boto3
from validation import validate_slack_event

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# AWS Lambda client for invoking worker
lambda_client = boto3.client("lambda")
LAMBDA_HANDLER = os.environ.get("LAMBDA_HANDLER", "qa-slack-bot-worker")



def lambda_function(event, context):
    """
    Gateway Lambda: Handles Slack webhooks with deduplication and forwards to worker.
    """
    # Log the received raw event
    logger.info(
        "Gateway received event: %s | Request ID: %s",
        json.dumps(event),
        getattr(context, "aws_request_id", "N/A"),
    )
    logger.info("🔒 SSL configuration loaded")

    # Parse Slack payload
    try:
        body = json.loads(event.get("body", "{}"))
        logger.info(
            "Parsed Slack payload: %s",
            json.dumps(body),
        )
    except json.JSONDecodeError as e:
        logger.error("JSON parse error: %s", str(e))
        return {"statusCode": 400, "body": "Invalid JSON"}

    # EVENT VALIDATION: Validate Slack payload structure
    is_valid, validation_message = validate_slack_event(body)
    if not is_valid:
        logger.warning("Invalid Slack event: %s", validation_message)
        return {"statusCode": 400, "body": f"Invalid event: {validation_message}"}

    logger.info("Event validation passed: %s", validation_message)

    # Handle Slack URL verification
    if body.get("type") == "url_verification" and "challenge" in body:
        challenge = body["challenge"]
        logger.info(
            "Responding to Slack URL verification with challenge: %s", challenge
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": challenge,
        }

    # Handle actual event callbacks
    if body.get("type") == "event_callback":
        # Forward to worker lambda (async invocation)
        logger.info("Forwarding NEW event to worker Lambda: %s", LAMBDA_HANDLER)

        try:
            response = lambda_client.invoke(
                FunctionName=LAMBDA_HANDLER,
                InvocationType="Event",  # Async invocation
                Payload=json.dumps(body),  # Forward complete Slack payload
            )

            logger.info("Event forwarded successfully to worker lambda")
            logger.info(
                "Worker invoke response status: %s",
                response.get("StatusCode"),
            )

        except Exception as e:
            logger.error(f"Failed to invoke worker lambda: {str(e)}")
            # Still return 200 to Slack to prevent retries
            return {
                "statusCode": 200,
                "body": json.dumps({"ok": True, "worker_error": str(e)}),
            }

        return {"statusCode": 200, "body": json.dumps({"ok": True})}

    # Unexpected Slack payload
    logger.warning(f"Unsupported Slack event type: {json.dumps(body)}")
    return {
        "statusCode": 400,
        "body": json.dumps({"error": "Unsupported Slack request type"}),
    }
