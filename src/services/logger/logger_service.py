import logging
import os
import sys
from typing import Any, Optional

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields for AWS Lambda."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add AWS Lambda specific fields
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add environment information
        log_record["environment"] = os.environ.get("ENVIRONMENT", "unknown")
        log_record["aws_request_id"] = getattr(record, "aws_request_id", None)
        log_record["function_name"] = os.environ.get(
            "AWS_LAMBDA_FUNCTION_NAME", "unknown"
        )
        log_record["function_version"] = os.environ.get(
            "AWS_LAMBDA_FUNCTION_VERSION", "unknown"
        )

        # Add workflow context if available
        if hasattr(record, "workflow_id"):
            log_record["workflow_id"] = record.workflow_id
        if hasattr(record, "campaign_id"):
            log_record["campaign_id"] = record.campaign_id


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with JSON formatting.

    Args:
        name: Logger name
        level: Log level (defaults to LOG_LEVEL environment variable)

    Returns:
        Configured logger instance
    """
    # Get log level from environment or use default
    log_level = level if level is not None else os.environ.get("LOG_LEVEL", "INFO")

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Create JSON formatter
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s", timestamp=True
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


def log_with_context(
    logger: logging.Logger, level: str, message: str, **context: Any
) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **context: Additional context fields
    """
    # Create a log record with extra fields
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )

    # Add context fields to the record
    for key, value in context.items():
        setattr(record, key, value)

    # Log the record
    logger.handle(record)


def log_workflow_start(
    logger: logging.Logger, workflow_id: str, workflow_type: str, **context: Any
) -> None:
    """
    Log workflow start event.

    Args:
        logger: Logger instance
        workflow_id: Workflow identifier
        workflow_type: Type of workflow
        **context: Additional context
    """
    log_with_context(
        logger,
        "INFO",
        f"Workflow started: {workflow_type}",
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        event_type="workflow_start",
        **context,
    )


def log_workflow_complete(
    logger: logging.Logger,
    workflow_id: str,
    workflow_type: str,
    duration: float,
    **context: Any,
) -> None:
    """
    Log workflow completion event.

    Args:
        logger: Logger instance
        workflow_id: Workflow identifier
        workflow_type: Type of workflow
        duration: Workflow duration in seconds
        **context: Additional context
    """
    log_with_context(
        logger,
        "INFO",
        f"Workflow completed: {workflow_type} in {duration:.2f}s",
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        duration=duration,
        event_type="workflow_complete",
        **context,
    )


def log_workflow_error(
    logger: logging.Logger,
    workflow_id: str,
    workflow_type: str,
    error: Exception,
    **context: Any,
) -> None:
    """
    Log workflow error event.

    Args:
        logger: Logger instance
        workflow_id: Workflow identifier
        workflow_type: Type of workflow
        error: Exception that occurred
        **context: Additional context
    """
    log_with_context(
        logger,
        "ERROR",
        f"Workflow failed: {workflow_type} - {str(error)}",
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        error_type=type(error).__name__,
        error_message=str(error),
        event_type="workflow_error",
        **context,
    )


def log_api_call(
    logger: logging.Logger,
    service: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration: float,
    **context: Any,
) -> None:
    """
    Log API call event.

    Args:
        logger: Logger instance
        service: Service name (e.g., 'dropbox', 'openai')
        endpoint: API endpoint
        method: HTTP method
        status_code: HTTP status code
        duration: Request duration in seconds
        **context: Additional context
    """
    level = "ERROR" if status_code >= 400 else "INFO"
    log_with_context(
        logger,
        level,
        f"API call to {service} {endpoint}: {method} {status_code} ({duration:.2f}s)",
        service=service,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration=duration,
        event_type="api_call",
        **context,
    )


# Create default logger
default_logger = setup_logger("qa_slack_bot")
