import os
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from crewai_tools import FileReadTool, JiraTool, ShellTool

# 1. Configuration: Optimized for 16GB RAM
local_llm = Ollama(
    model="deepseek-coder-v2:lite", 
    base_url="http://ollama:11434",
    timeout=300
)

# 2. Tools initialization
file_tool = FileReadTool()
jira_tool = JiraTool()
shell_tool = ShellTool()

# --- AGENT DEFINITIONS ---

analyst_agent = Agent(
    role='Lead SDLC Analyst',
    goal='Analyze Jira tickets and codebases to provide a confidence score and technical plan.',
    backstory="""Expert architect. You read repo-specific AGENTS.md files to 
    ensure constraints are met. You calculate the 'Confidence Score' for the human.""",
    tools=[file_tool, jira_tool],
    llm=local_llm,
    verbose=True
)

backend_agent = Agent(
    role='Python Backend Developer',
    goal='Implement FastAPI logic and Postgres schema changes.',
    backstory="Follows /backend/AGENTS.md. Experts in Pydantic and SQLAlchemy.",
    tools=[file_tool],
    llm=local_llm,
    verbose=True
)

frontend_agent = Agent(
    role='Angular Frontend Developer',
    goal='Create Angular standalone components and services.',
    backstory="Follows /frontend/AGENTS.md. Expert in Signals, RxJS, and Tailwind.",
    tools=[file_tool],
    llm=local_llm,
    verbose=True
)

integrator_agent = Agent(
    role='System Integration Specialist',
    goal='Ensure the API contract between Backend and Frontend is perfect.',
    backstory="""You follow the Integration Protocol in ai-agents-core/AGENTS.md. 
    You ensure JSON keys match between Python and TypeScript.""",
    llm=local_llm,
    verbose=True
)

security_agent = Agent(
    role='SecOps Specialist',
    goal='Scan for vulnerabilities using Bandit and NPM Audit.',
    backstory="Audit the code in /app/repos. You are the safety gate.",
    tools=[shell_tool, file_tool],
    llm=local_llm,
    verbose=True
)

doc_agent = Agent(
    role='Documentation Architect',
    goal='Update README.md and AGENTS.md files.',
    backstory="Ensure the Living Documentation is updated in both repos.",
    tools=[file_tool, shell_tool],
    llm=local_llm,
    verbose=True
)

reviewer_agent = Agent(
    role='Senior Staff Engineer',
    goal='Final peer review and Reflection gate.',
    backstory="The final human-like quality check before PR creation.",
    llm=local_llm,
    verbose=True
)

# --- TASK DEFINITIONS ---

def create_analysis_task(issue_key, summary):
    return Task(
        description=f"Analyze {issue_key}: {summary}. Read AGENTS.md in all repos and provide Score & Plan.",
        expected_output="A Technical Plan with a Confidence Score.",
        agent=analyst_agent
    )

def create_development_task(issue_key, plan):
    return Task(
        description=f"Implement {issue_key} according to plan: {plan}. Follow repo-specific AGENTS.md.",
        expected_output="Code implemented in both repo volumes.",
        agent=backend_agent
    )

# --- THE FACTORY CLASS ---

class AIFactory:
    def __init__(self, issue_key, summary):
        self.issue_key = issue_key
        self.summary = summary

    def run_analysis(self):
        """Phase 1: Analysis & Scoring (Triggered by 'In Progress')"""
        task = create_analysis_task(self.issue_key, self.summary)
        crew = Crew(
            agents=[analyst_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        return crew.kickoff()

    def run_full_production_chain(self, issue_key, plan):
        """Phase 2: Full Implementation (Triggered by 'Proceed')"""
        
        dev_task = create_development_task(issue_key, plan)
        
        int_task = Task(
            description="Verify API contract between Python and Angular. Ensure models match perfectly.",
            expected_output="Contract verification report.",
            agent=integrator_agent
        )
        
        sec_task = Task(
            description="Run shell tools (Bandit/NPM Audit) to scan for vulnerabilities.",
            expected_output="Security scan report. Block if High vulnerabilities found.",
            agent=security_agent
        )
        
        doc_task = Task(
            description="Update repo-specific AGENTS.md and README.md with new changes.",
            expected_output="Updated documentation in repos.",
            agent=doc_agent
        )
        
        rev_task = Task(
            description="Final Peer Review and Reflection Gate.",
            expected_output="Approval for PR.",
            agent=reviewer_agent
        )

        production_crew = Crew(
            agents=[backend_agent, frontend_agent, integrator_agent, security_agent, doc_agent, reviewer_agent],
            tasks=[dev_task, int_task, sec_task, doc_task, rev_task],
            process=Process.sequential
        )
        return production_crew.kickoff()