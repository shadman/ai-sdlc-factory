import os
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from crewai_tools import FileReadTool, JiraTool

# 1. Configuration: Connect to local Ollama
# DeepSeek-Coder-V2 is excellent for reasoning and code
local_llm = Ollama(model="deepseek-coder-v2:lite", base_url="http://ollama:11434")

# 2. Tools initialization
# FileReadTool allows agents to read your AGENTS.md files
file_tool = FileReadTool()
# Note: JiraTool requires JIRA_DOMAIN, JIRA_USERNAME, and JIRA_API_TOKEN in .env
jira_tool = JiraTool()

# --- AGENT DEFINITIONS ---

analyst_agent = Agent(
    role='Lead SDLC Analyst',
    goal='Analyze Jira tickets and codebases to provide a confidence score and technical plan.',
    backstory="""You are an expert at system architecture. You check repo-specific AGENTS.md 
    files to ensure all constraints are met before any coding starts.""",
    tools=[file_tool, jira_tool],
    llm=local_llm,
    verbose=True,
    allow_delegation=False
)

backend_agent = Agent(
    role='Python Backend Developer',
    goal='Implement secure and scalable Python FastAPI logic.',
    backstory="""You follow PEP8 and the rules in python-backend/AGENTS.md. 
    You focus on Postgres migrations and API performance.""",
    tools=[file_tool],
    llm=local_llm,
    verbose=True
)

frontend_agent = Agent(
    role='Angular Frontend Developer',
    goal='Create high-quality Angular components.',
    backstory="""You follow Angular 17+ standards and the rules in angular-frontend/AGENTS.md. 
    You focus on Standalone components and Tailwind CSS.""",
    tools=[file_tool],
    llm=local_llm,
    verbose=True
)

# --- TASK DEFINITIONS ---

def create_analysis_task(issue_key, summary):
    return Task(
        description=f"""Analyze Jira ticket {issue_key}: {summary}.
        1. Read /app/repos/backend/AGENTS.md and /app/repos/frontend/AGENTS.md.
        2. Scan the current codebase for these repositories.
        3. Calculate a Confidence Score (0-100%).
        4. Draft a Technical Plan.
        
        Output format for Jira:
        Confidence Score: [X]%
        Technical Plan: [Brief steps]
        Risk Level: [Low/Med/High]
        'Type Proceed to start coding.'
        """,
        expected_output="A structured report with a confidence score and plan.",
        agent=analyst_agent,
        output_file=f"logs/analysis_{issue_key}.md"
    )

def create_development_task(issue_key, plan):
    return Task(
        description=f"""Based on the plan: {plan}, implement the changes.
        - Backend Agent: Update Python code following /backend/AGENTS.md.
        - Frontend Agent: Update Angular code following /frontend/AGENTS.md.
        - Integration: Ensure API contracts match between repos.
        """,
        expected_output="Code implemented in separate feature branches with passing logic.",
        agent=backend_agent # CrewAI allows multiple agents to be assigned via 'context' or separate tasks
    )

# --- ORCHESTRATION ---

class AIFactory:
    def __init__(self, issue_key, summary):
        self.issue_key = issue_key
        self.summary = summary

    def run_analysis(self):
        """Phase 1: Analysis & Scoring"""
        analysis_task = create_analysis_task(self.issue_key, self.summary)
        
        crew = Crew(
            agents=[analyst_agent],
            tasks=[analysis_task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        
        # Post the result to Jira (Tool usage)
        # jira_tool.post_comment(issue=self.issue_key, body=result)
        return result

    def run_production(self, approved_plan):
        """Phase 2: Coding (Triggered by 'Proceed' comment)"""
        dev_task = create_development_task(self.issue_key, approved_plan)
        
        crew = Crew(
            agents=[backend_agent, frontend_agent],
            tasks=[dev_task],
            process=Process.sequential # Keeps RAM usage low
        )
        return crew.kickoff()
