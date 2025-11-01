from ai_agents.crew import LatestAiDevelopmentCrew
from config.settings import TARGET_WEBSITE_URL
from dotenv import load_dotenv

load_dotenv()

def generate_prompt_from_website(website_url: str = None):
    """
    Generate a prompt by scraping and analyzing a website's tone and content.
    
    Args:
        website_url (str): The URL to scrape and analyze. If None, uses TARGET_WEBSITE_URL from settings.
    
    Returns:
        str: Generated prompt based on website analysis
    """
    if website_url is None:
        website_url = TARGET_WEBSITE_URL
    
    crew = LatestAiDevelopmentCrew()
    
    # Run the web scraping and prompt generation tasks
    result = crew.crew().kickoff(
        inputs={
            'website_url': website_url,
            'page_names': 'Back Injury at Work',
            'injury_types': 'Workers Comp',
            'locations': 'Atlanta, Georgia',
            'personas': 'Workers'
        }
    )
    print("Result: ", result)
    return result

def run():
    """
    Run the crew with default AI Agents topic.
    """
    inputs = {
        'topic': 'AI Agents'
    }
    LatestAiDevelopmentCrew().crew().kickoff(inputs=inputs)

if __name__ == "__main__":
    # You can specify a custom URL or use the one from settings
    custom_url = "https://demo-kzmp1bc9kbq922f43sqb.vusercontent.net"  # Example URL
    output = generate_prompt_from_website(custom_url)
    print("Output: ", output)