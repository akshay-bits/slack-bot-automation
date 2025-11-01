from typing import Optional, Dict, Any, List
from .base import BotStrategy
from .slack_bot_stratergy import SlackBotStrategy
from core.singletone import Singleton

class BotServiceSingleton(Singleton):
    """Singleton class for managing bot service instances"""
    
    _instance: Optional['BotServiceSingleton'] = None
    _strategy: Optional[BotStrategy] = None


    def __init__(self):
        """Initialize the singleton with default strategy"""
        if not hasattr(self, '_initialized'):
            self._strategy = None
            self._initialized = True
    
    def set_strategy(self, strategy: BotStrategy) -> None:
        """Set the bot strategy"""
        self._strategy = strategy
    
    def get_strategy(self) -> BotStrategy:
        """Get the current bot strategy, create default if none exists"""
        if self._strategy is None:
            self._strategy = SlackBotStrategy()
        return self._strategy
    
    def send_message(self, text: str, channel: Optional[str] = None) -> str:
        """Send a message using the current strategy"""
        return self.get_strategy().send_message(text, channel)
    
    def send_reply(self, text: str, thread_ts: str, channel: Optional[str] = None, broadcast: bool = False) -> Optional[str]:
        """Send a reply using the current strategy"""
        return self.get_strategy().send_reply(text, thread_ts, channel, broadcast)
    
    def get_recent_messages(self, limit: int = 10, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent messages using the current strategy"""
        return self.get_strategy().get_recent_messages(limit, channel)
    
    def delete_message(self, ts: str, channel: Optional[str] = None) -> bool:
        """Delete a message using the current strategy"""
        return self.get_strategy().delete_message(ts, channel)
    
    def get_message_by_ts(self, ts: str, channel: Optional[str] = None) -> str:
        """Get a message by timestamp using the current strategy"""
        return self.get_strategy().get_message_by_ts(ts, channel)
    
    def send_error_message(self, message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
        """Send an error message using the current strategy"""
        self.get_strategy().send_error_message(message, ts, channel)
    
    def send_success_message(self, message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
        """Send a success message using the current strategy"""
        self.get_strategy().send_success_message(message, ts, channel)
    
    def reset(self) -> None:
        """Reset the singleton instance (useful for testing)"""
        BotServiceSingleton._instance = None
        BotServiceSingleton._strategy = None


# Global instance for easy access
bot_service = BotServiceSingleton()
