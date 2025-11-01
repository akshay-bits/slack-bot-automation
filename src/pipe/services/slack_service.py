from typing import Optional

from services.bot_service.bot_singleton import bot_service


def send_success_message(message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
    bot_service.send_success_message(message, ts, channel)


