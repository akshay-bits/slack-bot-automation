import os
from click import prompt
from services.sheets_service.sheets_singletone import SheetsSingleton
from config.settings import WORKFLOW_API_URL, AGENT_API_URL
import requests
from services.logger.logger_service import default_logger
from ai_agents.crew import LatestAiDevelopmentCrew
from core.singletone import Singleton
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


TARGET_WEBSITE_URL = os.getenv('TARGET_WEBSITE_URL')

class GeneratePagesWorkflow(Singleton):
    """Workflow for generating pages"""

    def __init__(self, sheets_singleton: SheetsSingleton):
        """Initialize the workflow"""
        self.sheets_singleton = sheets_singleton
        self.crew = LatestAiDevelopmentCrew()

    def generate_pages(self, worksheet_name='Page-Requests') -> int:
        """Generate pages"""
        try:
            default_logger.info(f"Fetching sheets data from worksheet '{worksheet_name}' with status='pending'")
            sheets_data = self.sheets_singleton.get_sheet_data_by_status(worksheet_name, status='pending')
            default_logger.info(f"Successfully fetched {len(sheets_data)} sheets with status='pending'")
        except Exception as e:
            default_logger.error(f"Error fetching sheets data: {e}")
            raise
        
        count = 0
        try:
            
            default_logger.info(f"Generating pages for {len(sheets_data)} sheets")
            if len(sheets_data) == 0:
                default_logger.warning(f"No sheets found with status='pending' in worksheet '{worksheet_name}'")
                return 0
            if self.sheets_singleton.update_sheet_status(worksheet_name, sheet, 'running', sheet.get('requestId')):
                default_logger.info(f"Updated sheet status to 'running' for {worksheet_name} with request_id: {sheet.get('requestId')}")
                count += 1
            else:
                default_logger.error(f"Failed to update sheet status to 'running' for {worksheet_name} with request_id: {sheet.get('requestId')}")
            for sheet in sheets_data:
                default_logger.info(f"Processing sheet data: {sheet}")
                prompt = self.generate_prompt_with_crew(
                        website_url=TARGET_WEBSITE_URL,
                        page_names=sheet.get('page_names', ''),
                        injury_types=sheet.get('injury_types', ''),
                        locations=sheet.get('locations', ''),
                        personas=sheet.get('personas', '')
                )
                api_response = self.generate_page_api(chat_id=sheet.get('chat_id', ''),pages=prompt.get('pages', ''))
                default_logger.info(f"API response: {api_response}")
                if self.sheets_singleton.update_sheet_status(worksheet_name, sheet, 'generated', sheet.get('requestId')):
                    default_logger.info(f"Updated sheet status to 'generated' for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    count += 1
                else:
                    default_logger.error(f"Failed to update sheet status to 'generated' for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    continue

                if self.sheets_singleton.update_sheet_data(
                    worksheet_name, 
                    sheet_record={
                        "location": sheet.get('location', ''),
                        "injuryType": sheet.get('injuryType', ''),
                        "createdDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "path": api_response.get('result', '').get('path', ''),
                        "demoUrlLink": api_response.get('result', '').get('chat_result', '').get('latestVersion', '').get('demoUrl', ''),
                    }, 
                    request_id=sheet.get('requestId')
                ):
                    default_logger.info(f"Updated sheet data for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    count += 1
                else:
                    default_logger.error(f"Failed to update sheet data for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    continue

            return count
        except Exception as e:
            default_logger.error(f"Error generating pages: {e}")
            return 0

    def generate_prompt_with_crew(self, website_url: str, page_names: str, injury_types: str, locations: str, personas: str) -> str:
        """Generate layout prompt using existing CrewAI setup"""
        try:
            result =self.crew.crew().kickoff(
                inputs={
                    "website_url": website_url,
                    "page_names": page_names,
                    "injury_types": injury_types,
                    "locations": locations,
                    "personas": personas
                }
            )
            return result
        except Exception as e:
            default_logger.error(f"Error generating page: {e}")
            return False

    def generate_page_api(self, chat_id: str, pages: str) -> bool:
        """Generate a page"""
        try:
            response = requests.post(
                f'{WORKFLOW_API_URL}/create-page',
                json={
                    "chat_id": chat_id,
                    "pages": pages
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            default_logger.error(f"Error generating page: {e}")
            return False