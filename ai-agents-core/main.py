import os
import json
from tabnanny import verbose
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from phoenix.trace.langchain import LangChainInstrumentor
from crewai_tools import FileReadTool, JiraTool, ShellTool
from redis import Redis
from tools.jira_tools import JiraCommentTool

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

# 5. Jira tool to handle comments
jira_comment_tool = JiraCommentTool()

# 6. Tools initialization
file_tool = FileReadTool()
jira_tool = JiraTool()
shell_tool = ShellTool()

# --- AGENT DEFINITIONS ---

analyst_agent = Agent(
    role='Lead SDLC Analyst',
    goal='Analyze Jira tickets and codebase to provide a confidence score and technical plan.',
    backstory="Expert architect. You read repo-specific AGENTS.md files to ensure constraints are met.",
    tools=[file_tool, jira_tool, jira_comment_tool], 
    llm=local_llm,
    verbose=True
)

backend_agent = Agent(
    role='Python Backend Developer',
    goal='Implement FastAPI logic and Postgres schema changes.',
    backstory="""Change directory to {working_dir} and implement the logic.
    Follows /backend/AGENTS.md. Expert in Pydantic and SQLAlchemy.
    IMPORTANT: All file reads and shell commands must be scoped strictly to the path 
    provided by the Orchestrator (e.g., /app/repos/backend). 
    Never navigate outside of this directory.""",
    tools=[file_tool, shell_tool],
    llm=local_llm,
    verbose=True
)

frontend_agent = Agent(
    role='Angular Frontend Developer',
    goal='Create Angular standalone components and services.',
    backstory="""Change directory to {working_dir} and implement the logic.
    Follows /frontend/AGENTS.md. Expert in Signals, RxJS, and Tailwind.
    IMPORTANT: All file reads and shell commands must be scoped strictly to the path 
    provided by the Orchestrator (e.g., /app/repos/frontend). 
    Never navigate outside of this directory.""",
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
    goal='Scan for vulnerabilities using Bandit and NPM Audit (if present).',
    backstory="""Change directory to {working_dir} and implement the logic.
    Audit the code in /app/repos. You are the safety gate.
    ALWAYS perform security scans (bandit/npm audit) inside the working directory 
    provided by the Orchestrator. Do not scan the root directory.""",
    tools=[shell_tool, file_tool],
    llm=local_llm,
    verbose=True
)

git_agent = Agent(
    role='Git Operations Manager',
    goal='Manage branches and PRs using GitHub credentials.',
    backstory="""You manage version control for product repos. You are a multi-repo Git Master.
    BEFORE performing ANY git operations, verify your current working directory 
    matches the Orchestrator's target path. Only execute git commands within the product repository directory.
    Before pushing, you MUST set git config user.email and user.name.
    You use the GITHUB_TOKEN to authenticate. You always create branches named feature/ISSUE-KEY.
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
    tools=[jira_comment_tool], 
    llm=local_llm,
    verbose=True
)

# --- THE FACTORY CLASS ---
class AIFactory:
    def __init__(self, issue_key, repo_context="backend", summary=None):
        self.issue_key = issue_key
        self.repo_context = repo_context 
        # This tells agents exactly where to work
        self.working_dir = f"/app/repos/{repo_context}" 
        self.summary = summary or redis_client.hget(f"task:{self.issue_key}", "summary")

    # In your tasks, use self.working_dir to scope the FileReadTool or ShellTool

    def set_state(self, state):
        """Helper to update Redis state for monitoring."""
        redis_client.hset(f"task:{self.issue_key}", "state", state)
        print(f"--- 🔄 STATE: {state} ---")

    def run_analysis(self):
        inputs = {'working_dir': self.working_dir, 'issue_key': self.issue_key}

        """Phase 1: ANALYZING -> AWAITING_APPROVAL"""
        task = Task(
            description=f"""Analyze {self.issue_key}: {self.summary}. 
            1. Create a Technical Plan and Score.
            2. Use JiraCommentTool to post the plan as a comment on {self.issue_key}.""",
            expected_output="A Technical Plan with a Confidence Score post to Jira ticket.",
            agent=analyst_agent
        )
        crew = Crew(agents=[analyst_agent], tasks=[task], verbose=True)
        result = crew.kickoff(inputs=inputs)
        
        redis_client.hset(f"task:{self.issue_key}", "plan", str(result))
        self.set_state("awaiting_approval")
        return result

    def run_full_production_chain(self, issue_key, plan):
        """Phase 2: Full Factory Lifecycle"""
        
        # 1. CODING
        active_dev = backend_agent if self.repo_context == "backend" else frontend_agent
        
        # Pass the context here!
        inputs = {'working_dir': self.working_dir, 'issue_key': self.issue_key}

        dev_task = Task(
            description=f"Implement {self.issue_key} logic in {self.working_dir} based on {plan}.",
            expected_output="New code written to local files in /app/repos/.",
            agent=active_dev
        )

        # --- Logic to handle failure ---
        try:
            Crew(agents=[active_dev], tasks=[dev_task], verbose=True).kickoff(inputs=inputs)
        except Exception as e:
            # If coding fails, trigger the repair tool
            repair_task = Task(
                description=f"Fix the error that occurred: {str(e)} in {self.working_dir}",
                agent=active_dev,
                expected_output="Repaired code."
            )
            Crew(agents=[active_dev], tasks=[repair_task], verbose=True).kickoff(inputs=inputs)


        # 2. INTEGRATING
        self.set_state("integrating")
        int_task = Task(
            description="Verify API contract between Python and Angular repositories.",
            expected_output="Verification report.",
            agent=integrator_agent
        )
        Crew(agents=[integrator_agent], tasks=[int_task], verbose=True).kickoff(inputs=inputs)

        # 3. SECURITY_SCANNING
        self.set_state("security_scanning")
        sec_task = Task(
            description="Run bandit on /app/repos/backend and npm audit on /app/repos/frontend.",
            expected_output="Security scan report.",
            agent=security_agent
        )
        Crew(agents=[security_agent], tasks=[sec_task], verbose=True).kickoff(inputs=inputs)

        # 4. REVIEWING (Branching, PR Creation, and Documentation)
        self.set_state("reviewing")
        
        doc_task = Task(
            description="Update AGENTS.md history section in the affected repositories.",
            expected_output="Updated markdown files.",
            agent=doc_agent
        )

        git_task = Task(
            description=f"""Navigate to {self.working_dir}, create branch 'feature/{self.issue_key}', commit, and submit PR for {self.repo_context}.
            IMPORTANT: Once the PR is merged by a human, trigger a notification 
            to the deployment server to start the build.""",
            expected_output="Confirmed Pull Request URLs.",
            agent=git_agent
        )

        rev_task = Task(
            description="Final review of code, documentation changes, and Pull Requests.",
            expected_output="Final approval stamp and PR URLs.",
            agent=reviewer_agent,
            context=[doc_task, git_task] # Reviewer waits for Doc and Git to finish
        )

        finish_task = Task(
            description=f"Post a summary comment on {self.issue_key} with the PR link and final status.",
            expected_output="Comment posted.",
            agent=reviewer_agent
        )

        Crew(
            agents=[doc_agent, git_agent, reviewer_agent], 
            tasks=[doc_task, git_task, rev_task, finish_task],
            process=Process.sequential # RAM safety
        ).kickoff(inputs=inputs)

        # 5. COMPLETED
        self.set_state("completed")