import os
import re
import json
import time
import logging

# Disable CrewAI's interactive tracing prompt and telemetry — required for server/HF deployment
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"
# Give CrewAI a writable storage dir — avoids portalocker file-lock errors in containers
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai")

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool
from redis import Redis
from tools.jira_tools import JiraCommentTool
from tools.shell_tool import ShellExecutionTool

# 1. Load Environment Variables
REDIS_HOST   = os.getenv("REDIS_HOST", "redis")
REDIS_PORT   = int(os.getenv("REDIS_PORT", 6379))
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://ollama:11434")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")   # ollama | groq | openai
LLM_MODEL    = os.getenv("LLM_MODEL", "deepseek-coder-v2:lite")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317")

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_URL      = os.getenv("REDIS_URL")  # e.g. rediss://default:<pwd>@host:port (Redis Cloud)

# 2. Initialize Redis
if REDIS_URL:
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                         decode_responses=True, ssl=True)

# 3. Phoenix Instrumentation (optional — skipped gracefully if endpoint not set or unreachable)
if PHOENIX_ENDPOINT:
    try:
        from phoenix.trace.langchain import LangChainInstrumentor
        LangChainInstrumentor(endpoint=PHOENIX_ENDPOINT).instrument()
        print(f"✅ Phoenix tracing enabled → {PHOENIX_ENDPOINT}")
    except ImportError:
        try:
            os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", PHOENIX_ENDPOINT)
            from phoenix.otel import register
            from openinference.instrumentation.langchain import LangChainInstrumentor
            tracer_provider = register(set_global_tracer_provider=False)
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            print(f"✅ Phoenix tracing enabled → {PHOENIX_ENDPOINT}")
        except Exception as e:
            print(f"⚠️ Phoenix tracing unavailable: {e}. Continuing without observability.")
    except Exception as e:
        print(f"⚠️ Phoenix tracing unavailable: {e}. Continuing without observability.")
else:
    print("⚠️ PHOENIX_COLLECTOR_ENDPOINT not set — tracing disabled.")

# 4. LLM Configuration
# - Local:  LLM_PROVIDER=ollama  + OLLAMA_HOST
# - Cloud:  LLM_PROVIDER=groq    + GROQ_API_KEY     (recommended for Hugging Face)
#           LLM_PROVIDER=openai  + OPENAI_API_KEY
if LLM_PROVIDER == "ollama":
    local_llm = LLM(model=f"ollama/{LLM_MODEL}", base_url=OLLAMA_HOST, timeout=300)
else:
    # LiteLLM picks up API keys from env automatically (GROQ_API_KEY, GEMINI_API_KEY, etc.)
    # max_retries + rpm handle free-tier rate limits (e.g. Gemini 15 RPM)
    local_llm = LLM(
        model=f"{LLM_PROVIDER}/{LLM_MODEL}",
        timeout=300,
        max_retries=10,          # retry on 429s automatically
        rpm=4,                   # conservative throttle — well under Gemini's 20 RPM free tier
    )

logger = logging.getLogger("ai_factory")

# --- RETRY HELPER ---
def _parse_retry_after(err_str):
    """Extract the server-suggested retry delay from the error message."""
    match = re.search(r'retry in (\d+(?:\.\d+)?)\s*s', err_str, re.IGNORECASE)
    if match:
        return int(float(match.group(1))) + 5  # add 5s safety buffer
    return None

def run_crew_with_retry(crew, inputs, max_retries=8, base_wait=30):
    """
    Runs crew.kickoff() with smart retry on rate limit (429) errors.
    Uses the server's suggested retry delay when available, otherwise
    exponential backoff capped at 60s.
    """
    for attempt in range(max_retries):
        try:
            return crew.kickoff(inputs=inputs)
        except Exception as e:
            err = str(e)
            is_rate_limit = any(x in err for x in [
                "429", "RESOURCE_EXHAUSTED", "rate limit",
                "rate_limit", "quota", "RateLimitError"
            ])
            if is_rate_limit and attempt < max_retries - 1:
                # Prefer the server's suggested wait, cap backoff at 60s
                wait = _parse_retry_after(err) or min(base_wait * (2 ** attempt), 60)
                logger.warning(f"⏳ Rate limit — attempt {attempt + 1}/{max_retries}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise  # re-raise non-rate-limit errors immediately
    raise RuntimeError(f"Crew failed after {max_retries} retries due to rate limiting.")

# 5. Jira tool to handle comments
jira_comment_tool = JiraCommentTool()

# 6. Tools initialization
file_tool = FileReadTool()
shell_tool = ShellExecutionTool()

# --- AGENT DEFINITIONS ---

analyst_agent = Agent(
    role='Lead SDLC Analyst',
    goal='Analyze Jira tickets and codebase to provide a confidence score and technical plan.',
    backstory="""Expert architect. Product repositories are located under /app/repos/.
    ALWAYS use full absolute paths when reading files.
    For example: /app/repos/backend/AGENTS.md, /app/repos/frontend/AGENTS.md.
    Never use relative paths like 'backend/AGENTS.md'.
    Create a new branch for every change and its pull request, you can not push into the main/master branch directly without approval.""",
    tools=[file_tool, jira_comment_tool],
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
    goal='Ensure the API contract between Backend (/app/repos/backend), and Frontend (/app/repos/frontend) is perfect.',
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
    Before pushing a newly created branch, you MUST set git config user.email and user.name.
    You use the GITHUB_TOKEN to authenticate. You always create branches named feature/ISSUE-KEY from master branch.
    You navigate to the repo folder and use git remote set-url origin to inject the GITHUB_TOKEN before pushing, ensuring a headless environment can authenticate. Create a proper PR for final review by human""",
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
    If a security scan or integration fails, you check the Phoenix trace logs to identify the exact step where logic deviated.""",
    tools=[file_tool, jira_comment_tool, shell_tool], 
    llm=local_llm,
    verbose=True
)

# --- THE FACTORY CLASS ---
class AIFactory:
    def __init__(self, issue_key, repo_contexts=["backend"], summary=None):
        self.issue_key = issue_key
        self.repo_contexts = repo_contexts if isinstance(repo_contexts, list) else [repo_contexts]
        # This tells agents exactly where to work
        self.primary_dir = f"/app/repos/{self.repo_contexts[0]}"
        self.summary = summary or redis_client.hget(f"task:{self.issue_key}", "summary")

    # In your tasks, use self.working_dir to scope the FileReadTool or ShellTool

    def set_state(self, state):
        """Helper to update Redis state for monitoring."""
        redis_client.hset(f"task:{self.issue_key}", "state", state)
        print(f"--- 🔄 STATE: {state} ---")

    def run_analysis(self):
        inputs = {'working_dir': self.primary_dir, 'issue_key': self.issue_key, 'repo_contexts': self.repo_contexts}
        repos_str = ", ".join(self.repo_contexts)

        """Phase 1: ANALYZING -> AWAITING_APPROVAL"""
        # Build explicit file paths for all repo contexts
        repo_paths = ", ".join([f"/app/repos/{ctx}" for ctx in self.repo_contexts])
        agents_md_paths = " and ".join([f"/app/repos/{ctx}/AGENTS.md" for ctx in self.repo_contexts])

        task = Task(
            description=f"""Analyze Jira ticket {self.issue_key} for these repositories: {repos_str}.
            Summary: {self.summary}.

            Repository files are located at: {repo_paths}
            IMPORTANT: Use these EXACT absolute paths when reading files:
            - AGENTS.md: {agents_md_paths}
            - README.md: replace AGENTS.md with README.md in the paths above

            Steps:
            1. Read each AGENTS.md file using its full absolute path to understand constraints.
            2. Create a Technical Plan and Confidence Score covering all affected repos.
            3. Use JiraCommentTool to post the plan and score as a comment on {self.issue_key}.""",
            expected_output="A multi-repo Technical Plan with a Confidence Score posted to the Jira ticket.",
            agent=analyst_agent
        )
        crew = Crew(agents=[analyst_agent], tasks=[task], verbose=True, memory=False, cache=False)
        result = run_crew_with_retry(crew, inputs)
        
        redis_client.hset(f"task:{self.issue_key}", "plan", str(result))
        self.set_state("awaiting_approval")
        return result

    def run_full_production_chain(self, issue_key, repo_contexts, plan):
        """Phase 2: Full Factory Lifecycle"""

        for context in repo_contexts:
            working_dir = f"/app/repos/{context}"
            branch_name = f"feature/{issue_key}"
            inputs = {'working_dir': working_dir, 'issue_key': issue_key}

            # 0. BRANCHING — create feature branch BEFORE any code is written
            self.set_state(f"branching_{context}")
            branch_task = Task(
                description=f"""Navigate to {working_dir} and prepare the feature branch:
                1. git checkout master
                2. git pull origin master
                3. git checkout -b {branch_name}
                4. Confirm with: git branch --show-current
                Do NOT skip any step. All code changes must land on this branch.""",
                expected_output=f"Branch {branch_name} created and checked out in {working_dir}.",
                agent=git_agent
            )
            run_crew_with_retry(Crew(agents=[git_agent], tasks=[branch_task], verbose=True, memory=False, cache=False), inputs)

            # 1. CODING (now on feature branch)
            self.set_state(f"coding_{context}")
            active_dev = backend_agent if context == "backend" else frontend_agent

            dev_task = Task(
                description=f"Implement {issue_key} logic in {working_dir} based on {plan}.",
                expected_output="New code written to local files in /app/repos/.",
                agent=active_dev
            )
            try:
                run_crew_with_retry(Crew(agents=[active_dev], tasks=[dev_task], verbose=True, memory=False, cache=False), inputs)
            except Exception as e:
                repair_task = Task(
                    description=f"Fix the error that occurred: {str(e)} in {working_dir}",
                    agent=active_dev,
                    expected_output="Repaired code."
                )
                run_crew_with_retry(Crew(agents=[active_dev], tasks=[repair_task], verbose=True, memory=False, cache=False), inputs)

            # 2. INTEGRATING
            self.set_state(f"integrating_{context}")
            int_task = Task(
                description="Verify API contract between Python and Angular repositories.",
                expected_output="Verification report.",
                agent=integrator_agent
            )
            run_crew_with_retry(Crew(agents=[integrator_agent], tasks=[int_task], verbose=True, memory=False, cache=False), inputs)

            # 3. SECURITY SCANNING
            self.set_state(f"security_scanning_{context}")
            scan_cmd = "bandit -r ." if context == "backend" else "npm audit"
            sec_task = Task(
                description=f"Change directory to {working_dir} and run: {scan_cmd}",
                expected_output="Security scan report.",
                agent=security_agent
            )
            run_crew_with_retry(Crew(agents=[security_agent], tasks=[sec_task], verbose=True, memory=False, cache=False), inputs)

            # 4. REVIEWING — commit, push, open PR, update docs
            self.set_state(f"reviewing_{context}")

            doc_task = Task(
                description=f"Update AGENTS.md history section in {working_dir}.",
                expected_output="Updated markdown files.",
                agent=doc_agent
            )

            git_task = Task(
                description=f"""Navigate to {working_dir}. The branch {branch_name} already exists and is checked out.
                DO NOT create a new branch. Execute these steps in order:
                1. git add -A
                2. git commit -m "feat({context}): {issue_key} - AI-generated implementation"
                3. git push origin {branch_name}
                4. gh pr create --title "feat: {issue_key}" --body "AI-generated implementation. Awaiting human review." --base master
                Return the Pull Request URL.""",
                expected_output=f"Pull Request URL for {branch_name} → master.",
                agent=git_agent
            )

            rev_task = Task(
                description="Final review of code, documentation changes, and Pull Requests.",
                expected_output="Final approval stamp and PR URLs.",
                agent=reviewer_agent,
                context=[doc_task, git_task]
            )

            finish_task = Task(
                description=f"Post a summary comment on {self.issue_key} with the PR link and final status.",
                expected_output="Comment posted to Jira.",
                agent=reviewer_agent
            )

            run_crew_with_retry(
                Crew(
                    agents=[doc_agent, git_agent, reviewer_agent],
                    tasks=[doc_task, git_task, rev_task, finish_task],
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                    cache=False
                ),
                inputs
            )

            # 5. COMPLETED
            self.set_state(f"completed_{context}")
