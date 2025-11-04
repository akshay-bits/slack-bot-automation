import os
from typing import Optional
from click import prompt
from services.sheets_service.sheets_singletone import SheetsSingleton
from config.settings import WORKFLOW_API_URL, AGENT_API_URL
import requests
from services.logger.logger_service import default_logger
from ai_agents.publish_pages_crew import PublishPagesCrew
from core.singletone import Singleton
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TARGET_WEBSITE_URL = os.getenv('TARGET_WEBSITE_URL')
class PublishApprovedWorkflow(Singleton):
    """Workflow for publishing approved pages"""

    def __init__(self, sheets_singleton: SheetsSingleton):
        """Initialize the workflow"""
        self.sheets_singleton = sheets_singleton
        self.crew = PublishPagesCrew()

    def publish_approved(self, worksheet_name='Page-Requests') -> tuple[int, str]:
        """Publish approved pages"""
        try:
            default_logger.info(f"Fetching sheets data from worksheet '{worksheet_name}' with status='pending'")
            sheets_data = self.sheets_singleton.get_sheet_data_by_status(worksheet_name, status='pending')
            default_logger.info(f"Successfully fetched {len(sheets_data)} sheets with status='pending'")
        except Exception as e:
            default_logger.error(f"Error fetching sheets data: {e}")
            raise
        
        count = 0
        try:
            default_logger.info(f"Publishing {len(sheets_data)} sheets")
            if len(sheets_data) == 0:
                default_logger.warning(f"No pending records found '{worksheet_name}'")
            crew_input=[]
            chat_id = None
            for sheet in sheets_data:
                default_logger.info(f"Processing sheet data: {sheet}")
                chat_id = sheet.get('chat_id', '')
                crew_input.append({
                    "page_names":sheet.get('page_names', ''),
                    "injury_types":sheet.get('injury_types', ''),
                    "locations":sheet.get('locations', ''),
                })
            prompt = self.hide_pending_code_prompt_with_crew(
                        website_url=TARGET_WEBSITE_URL,
                        pages=crew_input
            )
            if not prompt:
                default_logger.error(f"Failed to generate prompt")
                return 0, "failed to generate prompt"
            api_response = self.publish_page_api(chat_id=chat_id,prompt=prompt.get('prompt', ''))
            if not api_response:
                default_logger.error(f"Failed to publish pages")
                return 0, "failed to publish pages"
            default_logger.info(f"API response: {api_response}")
            deployment_url = api_response.get('deploymentUrl', '')
            for sheet in sheets_data:
                if self.sheets_singleton.update_sheet_status(worksheet_name, sheet, 'published', sheet.get('requestId')):
                    default_logger.info(f"Updated sheet status to 'published' for {worksheet_name} with request_id: {sheet.get('requestId')}")
                else:
                    default_logger.error(f"Failed to update sheet status to 'published' for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    continue
                if self.sheets_singleton.update_sheet_data(
                    worksheet_name, 
                    sheet_record={
                        "publishUrlLink": deployment_url,
                    }, 
                    request_id=sheet.get('requestId')
                ):
                    default_logger.info(f"Updated sheet data for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    count += 1
                else:
                    default_logger.error(f"Failed to update sheet data for {worksheet_name} with request_id: {sheet.get('requestId')}")
                    continue
            return count, deployment_url
        except Exception as e:
            default_logger.error(f"Error publishing approved pages: {e}")
            return 0,''
        
    def publish_page_api(self, chat_id: str, prompt: str) -> Optional[dict]:
        """Publish a page and return the deployment url"""
        try:
                response = requests.post(
                    f'{WORKFLOW_API_URL}/publish',
                    json={
                        "chat_id": chat_id,
                        "prompt": prompt
                    }
                )
                return response.json()
        except Exception as e:
                default_logger.error(f"Error publishing page: {e}")
                return None
        
    def hide_pending_code_prompt_with_crew(self, website_url: str, pages: list) -> Optional[dict]:
        """Generate layout prompt using existing CrewAI setup"""
        try:
            result =self.crew.crew().kickoff(
                    inputs={
                        "website_url": website_url,
                        "pages": pages
                    }
            )
            return result.json()
        except Exception as e:
                default_logger.error(f"Error generating page: {e}")
                return None