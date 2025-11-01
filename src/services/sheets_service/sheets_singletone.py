from core.singletone import Singleton
from services.sheets_service.base import SheetsStrategy


class SheetsSingleton(Singleton):
    """Singleton class for sheets service"""
    
    _instance = None
    
    def __init__(self, strategy: SheetsStrategy = None):
        """Initialize the sheets service"""
        if not hasattr(self, '_sheets_initialized'):
            if strategy is None:
                raise ValueError("Strategy must be provided on first initialization")
            self.strategy = strategy
            self._sheets_initialized = True
        elif strategy is not None:
            # Update strategy if provided on subsequent calls
            self.strategy = strategy

    def get_sheet_data(self, worksheet_name: str) -> list[dict]:
        """Get data from the sheet"""
        return self.strategy.get_sheet_data(worksheet_name)

    def get_sheet_data_by_status(self, worksheet_name: str, status: str) -> list[dict]:
        """Get sheets by status"""
        return self.strategy.get_sheet_data_by_status(worksheet_name, status)

    def update_sheet_status(self, worksheet_name: str, sheet_record: dict, status: str, request_id: str) -> bool:
        """Update sheet status for a specific record"""
        return self.strategy.update_sheet_status(worksheet_name, sheet_record, status, request_id)
    
    def update_sheet_data(self, worksheet_name: str, sheet_record: dict, request_id: str) -> bool:
        """Update sheet data for a specific record"""
        return self.strategy.update_sheet_data(worksheet_name, sheet_record, request_id)


if __name__ == "__main__":
    import os
    from config.settings import BASE_DIR, SPREADSHEET_ID
    from services.sheets_service.google_sheet_stratergy import GoogleSheetStrategy
    # BASE_DIR is src/, go one level up to project root
    project_root = os.path.dirname(BASE_DIR)
    sheets_singleton=SheetsSingleton(
                        strategy=GoogleSheetStrategy(
                        credentials_file=f"{project_root}/google_credentials.json",
                        sheet_id=SPREADSHEET_ID, 
                            scopes=["https://www.googleapis.com/auth/spreadsheets"]
                        )
                    )
    result = sheets_singleton.update_sheet_status(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, status="running", request_id="1234567890")
    print("result: ", result)
    sheets_singleton.get_sheet_data_by_status(worksheet_name="Page-Requests", status="running")
    sheets_singleton.get_sheet_data(worksheet_name="Page-Requests")
    sheets_singleton.update_sheet_status(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, status="generated", request_id="1234567890")
    sheets_singleton.get_sheet_data_by_status(worksheet_name="Page-Requests", status="generated")
    sheets_singleton.get_sheet_data(worksheet_name="Page-Requests")
    sheets_singleton.update_sheet_status(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, status="failed", request_id="1234567890")
    sheets_singleton.get_sheet_data_by_status(worksheet_name="Page-Requests", status="failed")
    sheets_singleton.get_sheet_data(worksheet_name="Page-Requests")
    sheets_singleton.update_sheet_status(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, status="pending", request_id="1234567890")
    sheets_singleton.get_sheet_data_by_status(worksheet_name="Page-Requests", status="pending")
    sheets_singleton.get_sheet_data(worksheet_name="Page-Requests")

    result = sheets_singleton.update_sheet_data(worksheet_name="Page-Requests", sheet_record={"location": "India", "injuryType": "head-injury"}, request_id="2")
    print("result: ", result)
