# src/ai-agents/crew.py
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, WebsiteSearchTool, ScrapeWebsiteTool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from pathlib import Path
import os
import yaml

# Get the project root directory (3 levels up from this file)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CONFIG_DIR = Path(__file__).parent / "config"
_PUBLISH_PAGE_CREW_DIR = Path(__file__).parent / "publish_page_crew"

# Custom tasks config file path
_CUSTOM_TASKS_FILE = _PUBLISH_PAGE_CREW_DIR.resolve() / "tasks.yml"

@CrewBase
class PublishPagesCrew():
	"""PublishPagesCrew crew for publishing pages"""
	# Use shared agents config but separate tasks config
	agents: str = str(_CONFIG_DIR.resolve() / "agents.yaml")
	tasks: str = str(_PUBLISH_PAGE_CREW_DIR.resolve() / "tasks.yml")

	@agent
	def prompt_generator(self) -> Agent:
		return Agent(
			config=self.agents_config['publish_page_agent'],
			verbose=True,
			tools=[ScrapeWebsiteTool()],
			llm=LLM(
				model="anthropic/claude-3-haiku-20240307",
				api_key=os.getenv("ANTHROPIC_API_KEY")
			)
		)

	@task
	def prompt_generation_task(self) -> Task:
		# Load custom tasks config
		with open(_CUSTOM_TASKS_FILE, 'r') as f:
			custom_tasks_config = yaml.safe_load(f)
		task_config = custom_tasks_config['prompt_hide_pending_code']
		# Get the agent
		agent = self.agents_config[task_config['agent']]
		return Task(
			description=task_config['description'],
			expected_output=task_config['expected_output'],
			agent=self.prompt_generator(),
		)
    
	@crew
	def crew(self) -> Crew:
		"""Creates the PublishPagesCrew crew"""
		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=True,
		)