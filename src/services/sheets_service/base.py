from abc import ABC, abstractmethod
from sqlite3 import connect

class SheetsStrategy(ABC):
    """Interface for sheet operations"""
    @abstractmethod
    def create_connection(self, scopes: str) -> str:
        """Create a new connection"""
        pass

    @abstractmethod
    def get_sheet_data(self) -> list[dict]:
        """Get data from the sheet"""
        pass

    @abstractmethod
    def get_sheet_data_by_status(self, worksheet_name: str, status: str) -> list[dict]:
        """Get sheets by status"""
        pass

    @abstractmethod
    def update_sheet_status(self, worksheet_name: str, sheet_record: dict, status: str, request_id: str) -> bool:
        """Update sheet status for a specific record"""
        pass

    @abstractmethod
    def update_sheet_data(self, worksheet_name: str, sheet_record: dict, request_id: str) -> bool:
        """Update sheet data for a specific record"""
        pass