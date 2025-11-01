from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BotStrategy(ABC):
    """Abstract base class for bot communication strategies"""
    
    @abstractmethod
    def send_message(self, text: str, channel: Optional[str] = None) -> str:
        """Send a message and return its timestamp"""
        pass
    
    @abstractmethod
    def send_reply(self, text: str, thread_ts: str, channel: Optional[str] = None, broadcast: bool = False) -> Optional[str]:
        """Send a threaded reply and return its timestamp"""
        pass
    
    @abstractmethod
    def get_recent_messages(self, limit: int = 10, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent messages with their replies"""
        pass
    
    @abstractmethod
    def delete_message(self, ts: str, channel: Optional[str] = None) -> bool:
        """Delete a message by timestamp"""
        pass
    
    @abstractmethod
    def get_message_by_ts(self, ts: str, channel: Optional[str] = None) -> str:
        """Get a specific message by timestamp"""
        pass
    
    @abstractmethod
    def send_error_message(self, message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
        """Send an error message"""
        pass
    
    @abstractmethod
    def send_success_message(self, message: str, ts: Optional[str] = None, channel: Optional[str] = None) -> None:
        """Send a success message"""
        pass
