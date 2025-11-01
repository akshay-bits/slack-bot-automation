from dotenv import load_dotenv
import os

load_dotenv()

WORKFLOW_API_URL = os.getenv('WORKFLOW_API_URL')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
AGENT_API_URL = os.getenv('AGENT_API_URL')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Website scraping configuration - can be set via environment variable
TARGET_WEBSITE_URL = os.getenv('TARGET_WEBSITE_URL', 'https://glolaw.com')