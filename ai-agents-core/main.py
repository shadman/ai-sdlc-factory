import os
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from phoenix.trace.langchain import LangChainInstrumentor
from crewai_tools import FileReadTool, JiraTool, ShellTool
from redis import Redis

# 1. Load Environment Variables
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-coder-v2:lite")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317")

# 2. Initialize Redis
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# 3. Phoenix Instrument immediately
LangChainInstrumentor(endpoint=PHOENIX_ENDPOINT).instrument()

# 4. Configuration: Optimized for 16GB RAM
local_llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_HOST, timeout=300)

# 5. Tools initialization
file_tool = FileReadTool()
jira_tool = JiraTool()
shell_tool = ShellTool()

# --- AGENT DEFINITIONS ---

analyst_agent = Agent(
    role='Lead SDLC Analyst',
    goal='Analyze Jira tickets and codebase to provide a confidence score and technical plan.',
    backstory="Expert architect. You read repo-specific AGENTS.md files to ensure constraints are met.",
    tools=[file_tool, jira_tool],
    llm=local_llm,
    verbose=True
)

backend_agent = Agent(
    role='Python Backend Developer',
    goal='Implement FastAPI logic and Postgres schema changes.',
    backstory="Follows /backend/AGENTS.md. Expert in Pydantic and SQLAlchemy.",
    tools=[file_tool, shell_tool],
    llm=local_llm,
    verbose=True
)

frontend_agent = Agent(
    role='Angular Frontend Developer',
    goal='Create Angular standalone components and services.',
    backstory="Follows /frontend/AGENTS.md. Expert in Signals, RxJS, and Tailwind.",
    tools=[file_tool, shell_tool],
    llm=local_llm,
    verbose=True
)

integrator_agent = Agent(
    role='System Integration Specialist',
    goal='Ensure the API contract between Backend and Frontend is perfect.',
    backstory="You bridge the gap. You ensure JSON keys match between Python and TypeScript.",
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

git_agent = Agent(
    role='Git Operations Manager',
    goal='Manage branches and PRs using GitHub credentials.',
    backstory="""You manage version control. 
    Before pushing, you MUST set git config user.email and user.name.
    You use the GITHUB_TOKEN to authenticate. You always create branches named feature/ISSUE-KEY.
    You navigate to /app/repos/backend or /app/repos/frontend to execute commands.
    You navigate to the repo folder and use git remote set-url origin to inject the GITHUB_TOKEN before pushing, ensuring a headless environment can authenticate.""",
    tools=[shell_tool],
    llm=local_llm,
    verbose=True
)

doc_agent = Agent(
    role='Documentation Architect',
    goal='Maintain the Living Documentation in AGENTS.md and README.md.',
    backstory="You ensure that every code change is reflected in the repo's manual history.",
    tools=[file_tool, shell_tool],
    llm=local_llm,
    verbose=True
)

reviewer_agent = Agent(
    role='Senior Staff Engineer',
    goal='Final peer review and PR approval.',
    backstory="""You are the final human-like quality check. 
    If a security scan or integration fails, you check the Phoenix trace logs 
    at http://phoenix:6006 to identify the exact step where logic deviated.""",
    llm=local_llm,
    verbose=True
)

# --- THE FACTORY CLASS ---
class AIFactory:
    def __init__(self, issue_key, summary=None):
        self.issue_key = issue_key
        self.summary = summary or redis_client.hget(f"task:{issue_key}", "summary")

    def set_state(self, state):
        """Helper to update Redis state for monitoring."""
        redis_client.hset(f"task:{self.issue_key}", "state", state)
        print(f"--- 🔄 STATE: {state} ---")

    def run_analysis(self):
        """Phase 1: ANALYZING -> AWAITING_APPROVAL"""
        task = Task(
            description=f"Analyze {self.issue_key}: {self.summary}. Provide Plan and Score.",
            expected_output="A Technical Plan with a Confidence Score.",
            agent=analyst_agent
        )
        crew = Crew(agents=[analyst_agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        
        redis_client.hset(f"task:{self.issue_key}", "plan", str(result))
        self.set_state("awaiting_approval")
        return result

    def run_full_production_chain(self, issue_key, plan):
        """Phase 2: Full Factory Lifecycle"""
        
        # 1. CODING
        dev_task = Task(
            description=f"Implement {issue_key} logic in backend and frontend based on {plan}.",
            expected_output="New code written to local files in /app/repos/.",
            agent=backend_agent
        )
        Crew(agents=[backend_agent, frontend_agent], tasks=[dev_task]).kickoff()

        # 2. INTEGRATING
        self.set_state("integrating")
        int_task = Task(
            description="Verify API contract between Python and Angular repositories.",
            expected_output="Verification report.",
            agent=integrator_agent
        )
        Crew(agents=[integrator_agent], tasks=[int_task]).kickoff()

        # 3. SECURITY_SCANNING
        self.set_state("security_scanning")
        sec_task = Task(
            description="Run bandit on /app/repos/backend and npm audit on /app/repos/frontend.",
            expected_output="Security scan report.",
            agent=security_agent
        )
        Crew(agents=[security_agent], tasks=[sec_task]).kickoff()

        # 4. REVIEWING (Branching, PR Creation, and Documentation)
        self.set_state("reviewing")
        
        doc_task = Task(
            description="Update AGENTS.md history section in the affected repositories.",
            expected_output="Updated markdown files.",
            agent=doc_agent
        )

        git_task = Task(
            description=f"Create branch 'feature/{issue_key}', commit changes, and submit PRs using 'gh pr create'.",
            expected_output="Confirmed Pull Request URLs.",
            agent=git_agent
        )

        rev_task = Task(
            description="Final review of code, documentation changes, and Pull Requests.",
            expected_output="Final approval stamp and PR URLs.",
            agent=reviewer_agent,
            context=[doc_task, git_task] # Reviewer waits for Doc and Git to finish
        )

        Crew(
            agents=[doc_agent, git_agent, reviewer_agent], 
            tasks=[doc_task, git_task, rev_task],
            process=Process.sequential # RAM safety
        ).kickoff()

        # 5. COMPLETED
        self.set_state("completed")