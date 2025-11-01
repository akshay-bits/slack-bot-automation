from pipe.prompts.completion_prompts import (
    AVAILABLE_COMMANDS,
    AVAILABLE_COMMANDS_LIST,
    COMMAND_EXAMPLES,
)
from pipe.services.slack_service import send_success_message


def build_success_message(
    command_type, execution_id, question_or_query, answer_length, duration
):
    """
    Build formatted success message for Q&A interactions.

    Args:
        command_type: 'ask' or 'browse'
        execution_id: Unique execution identifier
        question_or_query: The question asked or search query
        answer_length: Length of the response
        duration: Processing duration in seconds

    Returns:
        str: Formatted success message
    """
    if command_type == "ask":
        truncated_question = (
            question_or_query[:100] + "..."
            if len(question_or_query) > 100
            else question_or_query
        )
        return (
            f"Question Answered Successfully!\n"
            f"Question: {truncated_question}\n"
            f"Response: {answer_length} characters\n"
            f"Execution ID: {execution_id}\n"
            f"Duration: {duration:.2f} seconds"
        )
    elif command_type == "browse":
        truncated_query = (
            question_or_query[:100] + "..."
            if len(question_or_query) > 100
            else question_or_query
        )
        return (
            f"Browse Completed Successfully!\n"
            f"Query: {truncated_query}\n"
            f"Results: {answer_length} characters\n"
            f"Execution ID: {execution_id}\n"
            f"Duration: {duration:.2f} seconds"
        )
    else:
        return (
            f"Command Completed Successfully!\n"
            f"Execution ID: {execution_id}\n"
            f"Duration: {duration:.2f} seconds"
        )


def show_available_commands(ts):
    """
    Show available commands when an unknown command is received.

    Args:
        ts: Slack timestamp for threading
    """
    commands_text = "\n".join(AVAILABLE_COMMANDS_LIST)
    msg = AVAILABLE_COMMANDS.format(commands=commands_text)
    return send_success_message(msg, ts)


def show_command_examples(command_type, ts):
    """
    Show examples for a specific command type.

    Args:
        command_type: 'ask' or 'search'
        ts: Slack timestamp for threading
    """
    if command_type in COMMAND_EXAMPLES:
        examples = COMMAND_EXAMPLES[command_type]
        examples_text = "\n".join([f"• `{example}`" for example in examples])
        msg = f"Examples for /{command_type} command:\n{examples_text}"
        return send_success_message(msg, ts)
    else:
        return show_available_commands(ts)


def format_error_message(error_type, error_details=None):
    """
    Format error messages consistently.

    Args:
        error_type: Type of error (e.g., 'ai_error', 'empty_question')
        error_details: Additional error details

    Returns:
        str: Formatted error message
    """
    error_messages = {
        "empty_question": (
            "Please provide a question after the /ask command\n"
            "Example: `/ask What is Python?`"
        ),
        "empty_search": (
            "Please provide a search query after the /search command\n"
            "Example: `/search latest Python news`"
        ),
        "ai_error": f"AI service error: {error_details}",
        "processing_error": f"Error processing request: {error_details}",
        "unknown_command": "Unknown command. Use one of the available commands below:",
        "general_error": f"Error: {error_details}",
    }

    return error_messages.get(error_type, f"Unexpected error: {error_details}")


def truncate_text(text, max_length=100, suffix="..."):
    """
    Truncate text to a maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_duration(seconds):
    """
    Format duration in a human-readable way.

    Args:
        seconds: Duration in seconds (float)

    Returns:
        str: Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def validate_command_input(command_type, input_text):
    """
    Validate input for different command types.

    Args:
        command_type: 'ask' or 'search'
        input_text: User input to validate

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not input_text or not input_text.strip():
        if command_type == "ask":
            return False, format_error_message("empty_question")
        elif command_type == "search":
            return False, format_error_message("empty_search")
        else:
            return False, format_error_message("general_error", "Empty input")

    # Add more validation rules as needed
    if len(input_text.strip()) > 2000:  # Reasonable limit
        return False, format_error_message(
            "general_error", "Input too long (max 2000 characters)"
        )

    return True, None
