import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .base import BotStrategy

load_dotenv()

# Constants
CHANNEL_REQUIRED_ERROR = "Channel must be provided."


class SlackBotStrategy(BotStrategy):
    """Slack implementation of BotStrategy"""
    
    def __init__(self, token: Optional[str] = None, default_channel: Optional[str] = None):
        """Initialize Slack bot strategy"""
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.default_channel = default_channel or f"#{os.getenv('SLACK_CHANNEL_ID')}"
        
        if not self.token:
            raise ValueError("Missing SLACK_BOT_TOKEN environment variable.")
        if not self.default_channel:
            raise ValueError("Missing SLACK_CHANNEL_ID environment variable.")
        
        self.client = WebClient(token=self.token)
    
    def send_message(self, text: str, channel: Optional[str] = None) -> str:
        """Send a message and return its timestamp"""
        target_channel = channel or self.default_channel
        if not text:
            raise ValueError("Message text must be provided.")
        if not target_channel:
            raise ValueError(CHANNEL_REQUIRED_ERROR)

        try:
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=text,
                unfurl_links=False,
                unfurl_media=False,
            )
            if isinstance(response.data, dict):
                ts = response.data.get("ts")
                if not ts:
                    raise RuntimeError("Slack response missing 'ts'")
                return ts
            else:
                raise RuntimeError("Unexpected response data type from Slack API")
        except SlackApiError as e:
            raise SlackApiError(f"Slack API Error: {e.response['error']}", e.response)


    def send_reply(self, text: str, thread_ts: str, channel: Optional[str] = None, broadcast: bool = False) -> Optional[str]:
        """Send a threaded reply and return its timestamp"""
        target_channel = channel or self.default_channel
        if not text or not thread_ts or not target_channel:
            raise ValueError("Text, thread_ts, and channel are all required.")

        try:
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=text,
                thread_ts=thread_ts,
                reply_broadcast=broadcast,
                unfurl_links=False,
                unfurl_media=False,
            )
            if isinstance(response.data, dict):
                return response.data.get("ts")
            else:
                return None
        except SlackApiError as e:
            raise SlackApiError(f"Slack API Error: {e.response['error']}", e.response)


    def get_recent_messages(self, limit: int = 10, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent messages with their replies"""
        target_channel = channel or self.default_channel
        if not target_channel:
            raise ValueError(CHANNEL_REQUIRED_ERROR)

        try:
            messages = self._fetch_messages(target_channel, limit)
            return self._process_messages_with_replies(messages, target_channel)
        except SlackApiError as e:
            raise SlackApiError(f"Slack API Error: {e.response['error']}", e.response)
    
    def _fetch_messages(self, channel: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch messages from channel"""
        response = self.client.conversations_history(channel=channel, limit=limit)
        if isinstance(response.data, dict):
            return response.data.get("messages", [])
        return []
    
    def _process_messages_with_replies(self, messages: List[Dict[str, Any]], channel: str) -> List[Dict[str, Any]]:
        """Process messages and fetch their replies"""
        result = []
        for msg in messages:
            if not self._is_valid_message(msg):
                continue
            
            parent_ts = msg.get("ts")
            parent_text = msg.get("text", "")
            replies = self._fetch_replies(msg, channel)
            result.append({"ts": parent_ts, "text": parent_text, "replies": replies})
        return result
    
    def _is_valid_message(self, msg: Dict[str, Any]) -> bool:
        """Check if message has required fields"""
        return bool(msg.get("ts") and msg.get("text"))
    
    def _fetch_replies(self, msg: Dict[str, Any], channel: str) -> List[Dict[str, Any]]:
        """Fetch replies for a message"""
        if msg.get("reply_count", 0) == 0:
            return []
        
        try:
            replies_response = self.client.conversations_replies(
                channel=channel, ts=msg.get("ts"), limit=100
            )
            if isinstance(replies_response.data, dict):
                replies_msgs = replies_response.data.get("messages", [])[1:]  # skip parent itself
            else:
                replies_msgs = []
            
            return [
                {"ts": reply["ts"], "text": reply["text"]}
                for reply in replies_msgs
                if reply.get("ts") and reply.get("text")
            ]
        except SlackApiError:
            return []


    def delete_message(self, ts: str, channel: Optional[str] = None) -> bool:
        """Delete a message by timestamp"""
        target_channel = channel or self.default_channel
        if not ts:
            raise ValueError("Message timestamp (ts) is required.")
        if not target_channel:
            raise ValueError(CHANNEL_REQUIRED_ERROR)

        try:
            response = self.client.chat_delete(channel=target_channel, ts=ts)
            if isinstance(response.data, dict):
                return response.data.get("ok", False)
            else:
                return False
        except SlackApiError as e:
            raise SlackApiError(f"Slack API Error: {e.response['error']}", e.response)


    def send_error_message(self, message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
        """Send an error message"""
        error_text = f"Error: {message}"
        if ts:
            self.send_reply(error_text, ts, channel)
        else:
            self.send_message(error_text, channel)

    def send_success_message(self, message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
        """Send a success message"""
        if ts:
            self.send_reply(message, ts, channel)
        else:
            self.send_message(message, channel)


    def get_message_by_ts(self, ts: str, channel: Optional[str] = None) -> str:
        """Get a specific message by timestamp"""
        target_channel = channel or self.default_channel
        if not ts:
            raise ValueError("Message timestamp (ts) must be provided.")
        if not target_channel:
            raise ValueError(CHANNEL_REQUIRED_ERROR)

        try:
            # Use conversations_replies to fetch the thread (parent + replies)
            response = self.client.conversations_replies(channel=target_channel, ts=ts, limit=1000)
            if isinstance(response.data, dict):
                messages = response.data.get("messages", [])
            else:
                messages = []
            for msg in messages:
                if msg.get("ts") == ts:
                    return msg.get("text", "")
            return ""
        except SlackApiError as e:
            raise SlackApiError(f"Slack API Error: {e.response['error']}", e.response)


# Legacy function wrappers for backward compatibility
def send_slack_message(text: str) -> str:
    """Legacy function - use SlackBotStrategy.send_message instead"""
    strategy = SlackBotStrategy()
    return strategy.send_message(text)


def send_slack_reply(text: str, thread_ts: str, broadcast: bool = False) -> Optional[str]:
    """Legacy function - use SlackBotStrategy.send_reply instead"""
    strategy = SlackBotStrategy()
    return strategy.send_reply(text, thread_ts, broadcast=broadcast)


def get_recent_messages(limit: int = 10) -> List[Dict[str, Any]]:
    """Legacy function - use SlackBotStrategy.get_recent_messages instead"""
    strategy = SlackBotStrategy()
    return strategy.get_recent_messages(limit)


def delete_message(ts: str) -> bool:
    """Legacy function - use SlackBotStrategy.delete_message instead"""
    strategy = SlackBotStrategy()
    return strategy.delete_message(ts)


def send_error_message(message: str, ts: Optional[str] = None) -> None:
    """Legacy function - use SlackBotStrategy.send_error_message instead"""
    strategy = SlackBotStrategy()
    strategy.send_error_message(message, ts)


def send_success_message(message: str, ts: Optional[str] = None) -> None:
    """Legacy function - use SlackBotStrategy.send_success_message instead"""
    strategy = SlackBotStrategy()
    strategy.send_success_message(message, ts)


def get_message_by_ts(ts: str) -> str:
    """Legacy function - use SlackBotStrategy.get_message_by_ts instead"""
    strategy = SlackBotStrategy()
    return strategy.get_message_by_ts(ts)


if __name__ == "__main__":
    # Test the new strategy pattern
    strategy = SlackBotStrategy()
    ts = strategy.send_message("This is a test message!")
    print(f"Message sent with timestamp: {ts}")
    data = strategy.send_reply("This is a test reply!", ts)
    print(f"Threaded reply sent with timestamp: {data}")
