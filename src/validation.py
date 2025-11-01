import typing as _t


def validate_slack_event(body: _t.Dict[str, _t.Any]) -> tuple[bool, str]:
    """Validate Slack event payload structure.

    Returns a tuple: (is_valid, message)
    """
    if not isinstance(body, dict):
        return False, "Body is not a dictionary"

    # Check for required Slack event fields
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        if not event:
            return False, "Missing event field in event_callback"

        # Validate app_mention events
        if event.get("type") == "app_mention":
            required_fields = ["type", "ts", "user", "text"]
            missing_fields = [field for field in required_fields if not event.get(field)]
            if missing_fields:
                return False, f"Missing required fields in app_mention: {missing_fields}"

        return True, "Valid event_callback"

    elif body.get("type") == "url_verification":
        if not body.get("challenge"):
            return False, "Missing challenge field in url_verification"
        return True, "Valid url_verification"

    else:
        return False, f"Unsupported event type: {body.get('type')}"


