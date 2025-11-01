# src/ai-agents/crew.py
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, WebsiteSearchTool, ScrapeWebsiteTool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os

@CrewBase
class LatestAiDevelopmentCrew():
	"""LatestAiDevelopment crew"""
	agents: List[BaseAgent]
	tasks: List[Task]

	@agent
	def prompt_generator(self) -> Agent:
		return Agent(
			config=self.agents_config['prompt_generator'],
			verbose=True,
			tools=[ScrapeWebsiteTool()],
			llm=LLM(
				model="anthropic/claude-3-haiku-20240307",
				api_key=os.getenv("ANTHROPIC_API_KEY")
			)
		)

	@task
	def prompt_generation_task(self) -> Task:
		return Task(
			config=self.tasks_config['prompt_generation_task'],
		)


	@crew
	def crew(self) -> Crew:
		"""Creates the LatestAiDevelopment crew"""
		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=True,
		)