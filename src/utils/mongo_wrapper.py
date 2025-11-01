import secrets
import string
from datetime import datetime
from typing import Any, Dict, Optional

from pipe.services.mongo_service import (
    fetch_from_mongo,
    insert_into_mongo,
    update_in_mongo,
)

EXECUTIONS_COLLECTION = "executions"

CONSTANTS_COLLECTION = "constants"


def generate_execution_id() -> str:
    """Generate an 8-character uppercase alphanumeric execution ID (uuid-like)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def save_execution_start(
    *,
    execution_id: str,
    workflow_type: str,
    triggered_by: Optional[str],
    slack_command: str,
    workflow_metadata: Optional[Dict[str, Any]] = None,
):
    """
    Create a new execution record with status "running".

    Schema stored in the collection `executions`:
    - execution_id, workflow_type, status, triggered_by, slack_command,
      workflow_metadata, execution_start, execution_end, error_message
    """
    document = {
        "execution_id": execution_id,
        "workflow_type": workflow_type,
        "status": "running",
        "triggered_by": triggered_by,
        "slack_command": slack_command,
        "workflow_metadata": workflow_metadata or {},
        "execution_start": datetime.now(),
        "execution_end": None,
        "error_message": None,
    }
    return insert_into_mongo(EXECUTIONS_COLLECTION, document)


def mark_execution_failed(*, execution_id: str, error_message: Optional[str] = None):
    """Mark an execution as failed and set execution_end timestamp."""
    match = {"execution_id": execution_id}
    update = {
        "$set": {
            "status": "failed",
            "execution_end": datetime.now(),
            "error_message": error_message,
        }
    }
    return update_in_mongo(EXECUTIONS_COLLECTION, match, update)


def mark_execution_completed(
    *, execution_id: str, workflow_metadata_updates: Optional[Dict[str, Any]] = None
):
    """Mark an execution as completed and optionally merge workflow_metadata
    updates."""
    match = {"execution_id": execution_id}
    update_set = {
        "status": "completed",
        "execution_end": datetime.now(),
    }
    if workflow_metadata_updates:
        # Overwrite/merge fields under workflow_metadata
        for key, value in workflow_metadata_updates.items():
            update_set[f"workflow_metadata.{key}"] = value

    update = {"$set": update_set}
    return update_in_mongo(EXECUTIONS_COLLECTION, match, update)


def get_running_executions(folder_path: Optional[str] = None):
    """
    Return running executions optionally filtered by folder_path.
    folder_path should be the plain folder (without leading slash);
    we match against workflow_metadata.dropbox_folder_path which stores
    "/{folder_path}".
    """
    query: Dict[str, Any] = {"status": "running"}
    if folder_path:
        query["workflow_metadata.dropbox_folder_path"] = f"/{folder_path}"
    return fetch_from_mongo(
        EXECUTIONS_COLLECTION, query, sort=[("execution_start", -1)]
    )


def get_constant_value(key: str) -> Optional[str]:
    """
    Get a constant value by key from the constants collection.

    Args:
        key (str): The constant key to look up

    Returns:
        Optional[str]: The constant value if found, None otherwise
    """
    documents = fetch_from_mongo(CONSTANTS_COLLECTION, {"key": key})
    if documents:
        return documents[0].get("value")
    return None


def set_constant_value(key: str, value: str) -> str:
    """
    Set a constant value by key in the constants collection.
    Creates new document if key doesn't exist, updates existing if it does.

    Args:
        key (str): The constant key
        value (str): The constant value to set

    Returns:
        str: The previous value if it existed, "not set" if this is a new key
    """
    # Get current value first
    current_value = get_constant_value(key)

    if current_value is not None:
        # Update existing document
        update_in_mongo(CONSTANTS_COLLECTION, {"key": key}, {"$set": {"value": value}})
        return current_value
    else:
        # Insert new document
        insert_into_mongo(CONSTANTS_COLLECTION, {"key": key, "value": value})
        return "not set"
