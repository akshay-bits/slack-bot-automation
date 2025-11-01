from datetime import datetime, timedelta
from typing import Any, Dict

from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from pipe.services.logger_service import default_logger
from pipe.services.mongo_service import fetch_from_mongo, insert_into_mongo
from pipe.services.sheets_service import append_data

QA_LOG_COLLECTION = "qa_interactions"


def log_question_answer(log_data: Dict[str, Any]) -> bool:
    """
    Log question-answer interaction to both MongoDB and Google Sheets.

    Args:
        log_data: Dictionary containing:
            - question: The user's question/query
            - answer: The AI's response
            - user_id: ID of the user
            - execution_id: Unique execution identifier
            - command_type: 'ask' or 'browse'
            - timestamp: When the interaction occurred

    Returns:
        bool: True if logging was successful, False otherwise
    """
    mongo_success = False
    sheets_success = False

    try:
        # Log to MongoDB with retry logic
        mongo_success = log_to_mongodb(log_data)
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        default_logger.warning(
            f"MongoDB connection failed for {log_data['execution_id']}: {str(e)}"
        )
        mongo_success = False
    except Exception as e:
        default_logger.error(
            f"MongoDB logging failed for {log_data['execution_id']}: {str(e)}"
        )
        mongo_success = False

    try:
        # Log to Google Sheets as backup
        sheets_success = log_to_sheets(log_data)
    except Exception as e:
        default_logger.error(
            f"Google Sheets logging failed for {log_data['execution_id']}: " f"{str(e)}"
        )
        sheets_success = False

    # Log success status
    if mongo_success and sheets_success:
        default_logger.info(
            f"Successfully logged interaction {log_data['execution_id']} to both "
            f"MongoDB and Sheets"
        )
        return True
    elif mongo_success or sheets_success:
        service = "MongoDB" if mongo_success else "Google Sheets"
        default_logger.warning(
            f"Partial logging success for {log_data['execution_id']}: only "
            f"{service} succeeded"
        )
        return True  # Consider partial success as success
    else:
        default_logger.error(
            f"Complete logging failure for {log_data['execution_id']}: both "
            f"MongoDB and Sheets failed"
        )
        return False


def log_to_mongodb(log_data: Dict[str, Any]) -> bool:
    """
    Log interaction data to MongoDB with connection retry.

    Args:
        log_data: Interaction data dictionary

    Returns:
        bool: True if successful, False otherwise
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Prepare document for MongoDB
            mongo_document = {
                "execution_id": log_data["execution_id"],
                "user_id": log_data["user_id"],
                "command_type": log_data["command_type"],
                "question": log_data["question"],
                "answer": log_data["answer"],
                "timestamp": log_data["timestamp"],
                "character_count": {
                    "question": len(log_data["question"]),
                    "answer": len(log_data["answer"]),
                },
            }

            # Insert into MongoDB
            result = insert_into_mongo(QA_LOG_COLLECTION, mongo_document)

            if result:
                default_logger.info(
                    f"Successfully logged to MongoDB: {log_data['execution_id']}"
                )
                return True
            else:
                default_logger.error(
                    f"Failed to insert to MongoDB: {log_data['execution_id']}"
                )
                return False

        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            default_logger.warning(
                f"MongoDB connection attempt {attempt + 1} failed for "
                f"{log_data.get('execution_id', 'unknown')}: {str(e)}"
            )
            if attempt == max_retries - 1:
                default_logger.error(
                    f"MongoDB logging failed after {max_retries} attempts: "
                    f"{log_data.get('execution_id', 'unknown')}"
                )
                return False
        except Exception as e:
            default_logger.error(
                f"MongoDB logging error for "
                f"{log_data.get('execution_id', 'unknown')}: {str(e)}"
            )
            return False

    return False


def log_to_sheets(log_data: Dict[str, Any]) -> bool:
    """
    Log interaction data to Google Sheets.

    Args:
        log_data: Interaction data dictionary

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Prepare row for Google Sheets
        sheet_row = {
            "Timestamp": log_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "Execution ID": log_data["execution_id"],
            "User ID": log_data["user_id"],
            "Command Type": log_data["command_type"],
            "Question/Query": log_data["question"],
            "Answer/Results": log_data["answer"],
            "Question Length": len(log_data["question"]),
            "Answer Length": len(log_data["answer"]),
            "Date": log_data["timestamp"].strftime("%Y-%m-%d"),
            "Time": log_data["timestamp"].strftime("%H:%M:%S"),
        }

        # Append to Google Sheets
        append_data([sheet_row])

        default_logger.info(
            f"Successfully logged to Google Sheets: {log_data['execution_id']}"
        )
        return True

    except Exception as e:
        default_logger.error(
            f"Google Sheets logging error for "
            f"{log_data.get('execution_id', 'unknown')}: {str(e)}"
        )
        return False


def get_user_interaction_history(user_id: str, limit: int = 10) -> list:
    """
    Get recent interaction history for a specific user.

    Args:
        user_id: ID of the user
        limit: Number of recent interactions to retrieve

    Returns:
        list: List of interaction documents
    """
    try:
        query = {"user_id": user_id}
        sort = [("timestamp", -1)]  # Most recent first

        interactions = fetch_from_mongo(QA_LOG_COLLECTION, query, sort)

        # Limit results
        return interactions[:limit] if interactions else []

    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        default_logger.warning(
            f"MongoDB connection failed fetching user history for {user_id}: "
            f"{str(e)}"
        )
        return []
    except Exception as e:
        default_logger.error(f"Error fetching user history for {user_id}: {str(e)}")
        return []


def get_interaction_stats(days: int = 7) -> Dict[str, Any]:
    """
    Get interaction statistics for the last N days.

    Args:
        days: Number of days to include in stats

    Returns:
        dict: Statistics dictionary
    """
    try:
        from pipe.services.mongo_service import fetch_from_mongo

        since_date = datetime.now() - timedelta(days=days)
        query = {"timestamp": {"$gte": since_date}}

        interactions = fetch_from_mongo(QA_LOG_COLLECTION, query)

        if not interactions:
            return {"total": 0, "ask_count": 0, "browse_count": 0, "unique_users": 0}

        ask_count = sum(1 for i in interactions if i.get("command_type") == "ask")
        browse_count = sum(1 for i in interactions if i.get("command_type") == "browse")
        unique_users = len(
            set(i.get("user_id") for i in interactions if i.get("user_id"))
        )

        return {
            "total": len(interactions),
            "ask_count": ask_count,
            "browse_count": browse_count,
            "unique_users": unique_users,
            "days": days,
        }

    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        default_logger.warning(
            f"MongoDB connection failed getting interaction stats: {str(e)}"
        )
        return {"error": "Database connection issue"}
    except Exception as e:
        default_logger.error(f"Error getting interaction stats: {str(e)}")
        return {"error": str(e)}
