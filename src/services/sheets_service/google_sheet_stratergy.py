from services.sheets_service.base import SheetsStrategy
from gspread import Client, authorize, exceptions
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import List
from services.logger.logger_service import default_logger


class GoogleSheetStrategy(SheetsStrategy):
    """Google Sheet Strategy for sheet operations"""
    def __init__(self, credentials_file: str, sheet_id: str, scopes: List[str]):
        """Initialize the sheet strategy"""
        self.credentials_file = credentials_file
        self.scopes = scopes
        self.client = self.create_connection(self.scopes)
        self.sheet_id = sheet_id
    
    def create_connection(self, scopes: List[str]) -> Client:
        """Create a new connection"""
        try:
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=self.scopes)
            return authorize(creds)
        except FileNotFoundError:
            raise RuntimeError("Credentials file 'credentials.json' not found")
        except ValueError as e:
            raise RuntimeError(f"Invalid credentials format: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create connection: {e}")

    def get_sheet_data(self, worksheet_name: str) -> list[dict]:
        """Get data from the sheet"""
        try:
            if not self.sheet_id:
                raise RuntimeError(f"SPREADSHEET_ID is not set. Please check your environment variables.")
            return self.client.open_by_key(self.sheet_id).worksheet(worksheet_name).get_all_records()
        except exceptions.SpreadsheetNotFound as e:
            raise RuntimeError(f"Sheet with ID {self.sheet_id} not found: {e}")
        except exceptions.WorksheetNotFound as e:
            raise RuntimeError(f"Worksheet '{worksheet_name}' not found in spreadsheet: {e}")
        except exceptions.APIError as e:
            raise RuntimeError(f"Google Sheets API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to get sheet data: {e}")

    def get_sheet_data_by_status(self, worksheet_name: str, status: str) -> list[dict]:
        """Get sheets by status"""
        try:
            if not self.sheet_id:
                raise RuntimeError(f"SPREADSHEET_ID is not set. Please check your environment variables.")
            worksheet = self.client.open_by_key(self.sheet_id).worksheet(worksheet_name)
            all_records = worksheet.get_all_records()
            
            # Log available columns for debugging
            if all_records:
                available_columns = list(all_records[0].keys())
                default_logger.info(f"Available columns in worksheet '{worksheet_name}': {available_columns}")
                default_logger.info(f"Total records fetched: {len(all_records)}")
                # Log sample record for debugging
                default_logger.info(f"Sample record (first row): {all_records[0]}")
            
            # Filter records by status - check case-insensitive and handle variations
            filtered_records = []
            for record in all_records:
                record_status = record.get('status', record.get('Status', ''))
                if str(record_status).lower() == str(status).lower():
                    filtered_records.append(record)
            
            default_logger.info(f"Filtered {len(filtered_records)} records with status='{status}'")
            return filtered_records
        except exceptions.SpreadsheetNotFound as e:
            raise RuntimeError(f"Spreadsheet with ID {self.sheet_id} not found. Check SPREADSHEET_ID and ensure service account has access: {e}")
        except exceptions.WorksheetNotFound as e:
            raise RuntimeError(f"Worksheet '{worksheet_name}' not found in spreadsheet: {e}")
        except exceptions.APIError as e:
            raise RuntimeError(f"Google Sheets API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to get sheet data by status: {e}")
    
    def update_sheet_status(self, worksheet_name: str, sheet_record: dict, status: str, request_id: str) -> bool:
        """Update the status (and optionally other columns) for a given request_id"""
        try:
            default_logger.info(f"Updating sheet status for worksheet '{worksheet_name}' and request_id: {request_id}")
            
            if not self.sheet_id:
                raise RuntimeError("SPREADSHEET_ID is not set. Please check your environment variables.")
            
            # Open the spreadsheet and worksheet
            spreadsheet = self.client.open_by_key(self.sheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Get all records to find the row to update
            all_records = worksheet.get_all_records()
            
            # Find the row index (gspread uses 1-based indexing, header is row 1)
            row_index = None
            for idx, record in enumerate(all_records, start=2):  # Start at 2 because row 1 is header
                record_id = str(record.get('requestId', '')).strip()
                if record_id == str(request_id).strip():
                    row_index = idx
                    break
            
            if row_index is None:
                default_logger.warning(f"Request ID '{request_id}' not found in worksheet '{worksheet_name}'")
                return False
            
            # Get the header row to find column indices
            header_row = worksheet.row_values(1)
            
            # Update status column
            worksheet.update_cell(row_index, header_row.index('status') + 1, status)
            default_logger.info(f"Updated status to '{status}' in row {row_index}, column {header_row.index('status') + 1}")
            
            # Update any other fields from sheet_record
            for field_name, field_value in sheet_record.items():
                if field_name.lower() == 'status':
                    continue  # Already handled
                
                if field_name in header_row:
                    col_index = header_row.index(field_name) + 1
                    worksheet.update_cell(row_index, col_index, field_value)
                    default_logger.info(f"Updated '{field_name}' to '{field_value}' in row {row_index}, column {col_index}")
                else:
                    default_logger.warning(f"Column '{field_name}' not found in worksheet, skipping")
            
            default_logger.info(f"Successfully updated sheet for request_id: {request_id}")
            return True

        except exceptions.SpreadsheetNotFound as e:
            default_logger.error(f"Spreadsheet with ID {self.sheet_id} not found: {e}")
            return False
        except exceptions.WorksheetNotFound as e:
            default_logger.error(f"Worksheet '{worksheet_name}' not found: {e}")
            return False
        except exceptions.APIError as e:
            default_logger.error(f"Google Sheets API error: {e}")
            return False
        except Exception as e:
            default_logger.error(f"Failed to update sheet status: {e}")
            import traceback
            default_logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    def update_sheet_data(self, worksheet_name: str, sheet_record: dict, request_id: str) -> bool:
        """Update sheet data for a specific record - supports updating multiple fields at once"""
        try:
            default_logger.info(f"Updating sheet data for worksheet '{worksheet_name}' and request_id: {request_id}")
            default_logger.info(f"Fields to update: {list(sheet_record.keys())}")
            
            if not self.sheet_id:
                raise RuntimeError("SPREADSHEET_ID is not set. Please check your environment variables.")
            
            # Open the spreadsheet and worksheet
            spreadsheet = self.client.open_by_key(self.sheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Get all records to find the row to update
            all_records = worksheet.get_all_records()
            
            # Find the row index (gspread uses 1-based indexing, header is row 1)
            row_index = None
            for idx, record in enumerate(all_records, start=2):  # Start at 2 because row 1 is header
                record_id = str(record.get('requestId', '')).strip()
                if record_id == str(request_id).strip():
                    row_index = idx
                    break
            
            if row_index is None:
                default_logger.warning(f"Request ID '{request_id}' not found in worksheet '{worksheet_name}'")
                return False
            
            # Get the header row to find column indices
            header_row = worksheet.row_values(1)
            
            # Update all fields from sheet_record that exist in the header
            updated_fields = []
            for field_name, field_value in sheet_record.items():
                # Skip requestId as it's used for lookup, not updating
                if field_name.lower() == 'requestid' or field_name == 'request_id':
                    continue
                
                # Find column index (case-insensitive matching)
                col_index = None
                for idx, header in enumerate(header_row):
                    if header.lower().strip() == field_name.lower().strip():
                        col_index = idx + 1  # gspread uses 1-based indexing
                        break
                
                if col_index:
                    worksheet.update_cell(row_index, col_index, field_value)
                    updated_fields.append(f"{field_name}={field_value}")
                    default_logger.info(f"Updated '{field_name}' to '{field_value}' in row {row_index}, column {col_index}")
                else:
                    default_logger.warning(f"Column '{field_name}' not found in worksheet headers, skipping. Available columns: {header_row}")
            
            if updated_fields:
                default_logger.info(f"Successfully updated {len(updated_fields)} field(s) for request_id '{request_id}': {', '.join(updated_fields)}")
                return True
            else:
                default_logger.warning(f"No fields were updated for request_id '{request_id}'. Check field names match header columns.")
                return False

        except exceptions.SpreadsheetNotFound as e:
            default_logger.error(f"Spreadsheet with ID {self.sheet_id} not found: {e}")
            return False
        except exceptions.WorksheetNotFound as e:
            default_logger.error(f"Worksheet '{worksheet_name}' not found: {e}")
            return False
        except exceptions.APIError as e:
            default_logger.error(f"Google Sheets API error: {e}")
            return False
        except Exception as e:
            default_logger.error(f"Failed to update sheet data: {e}")
            import traceback
            default_logger.error(f"Traceback: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    import os
    from config.settings import BASE_DIR, SPREADSHEET_ID
    google_sheet_strategy = GoogleSheetStrategy(
        credentials_file=f"{BASE_DIR}/google_credentials.json",
        sheet_id=SPREADSHEET_ID, 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    result = google_sheet_strategy.update_sheet_data(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, request_id="1")
    print("result: ", result)
    data = google_sheet_strategy.get_sheet_data(worksheet_name="Page-Requests")
    print("data: ", data)
    data_by_status = google_sheet_strategy.get_sheet_data_by_status(worksheet_name="Page-Requests", status="running")
    print("data_by_status: ", data_by_status)
    result = google_sheet_strategy.update_sheet_status(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, status="running", request_id="1")
    print("result: ", result)
    data = google_sheet_strategy.get_sheet_data(worksheet_name="Page-Requests")
    print("data: ", data)
    data_by_status = google_sheet_strategy.get_sheet_data_by_status(worksheet_name="Page-Requests", status="running")
    print("data_by_status: ", data_by_status)
    result = google_sheet_strategy.update_sheet_data(worksheet_name="Page-Requests", sheet_record={"requestId": "1"}, request_id="1")
    print("result: ", result)
    data = google_sheet_strategy.get_sheet_data(worksheet_name="Page-Requests")
    print("data: ", data)
    data_by_status = google_sheet_strategy.get_sheet_data_by_status(worksheet_name="Page-Requests", status="running")
    print("data_by_status: ", data_by_status)
