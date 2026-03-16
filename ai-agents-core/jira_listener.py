import os, json, logging
import uuid 
from fastapi import FastAPI, Request, BackgroundTasks
from redis import Redis
from main import AIFactory

# Load Environment
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Setup Logging for Visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jira_listener")

app = FastAPI()
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    # --- HANDLER FOR CI/CD AUTO-REPAIR (Test Failure) ---
    # This handles both Jira-based and Jira-less repos
    if payload.get("event") == "test_failed":
        issue = payload.get("issue", {})
        issue_key = issue.get("key") or f"INTERNAL-{uuid.uuid4().hex[:6].upper()}"
        repo_context = payload.get("repo", "backend")
        logs = payload.get("logs", "No logs provided.")

        logger.info(f"🛠️ CI/CD Auto-Repair triggered for {issue_key} in {repo_context}")
        redis_client.hset(f"task:{issue_key}", "state", "repairing")

        # Prepend logs to the plan so the Agent sees them
        repair_plan = f"CI Failure detected. Error Logs:\n{logs}"
        background_tasks.add_task(trigger_production_with_repo, issue_key, repo_context, repair_plan)

        return {"status": "repairing", "issue_key": issue_key}

    # --- HANDLER FOR JIRA WEBHOOKS ---
    issue = payload.get("issue", {})
    issue_key = issue.get("key")
    if not issue_key: return {"status": "ignored"}

    event_type = payload.get("webhookEvent")
    fields = issue.get("fields", {})
    status = fields.get("status", {}).get("name")
    summary = fields.get("summary", "")
    components = [c.get("name") for c in fields.get("components", [])]

    repo_context = "backend"
    if any(c.lower() == "frontend" for c in components):
        repo_context = "frontend"

    # --- STATE 1: Analyzing (Triggered by 'In Progress') ---
    if status == "In Progress" and event_type == "jira:issue_updated":
        logger.info(f"🚀 Initializing Analysis for {issue_key}")
        
        # Save initial context to Redis
        redis_client.hset(f"task:{issue_key}", mapping={
            "state": "analyzing", # <--- STATE: analyzing
            "components": json.dumps(components),
            "repo_context": repo_context, 
            "summary": summary
        })
        
        background_tasks.add_task(trigger_analyst, issue_key, repo_context, summary)
        return {"status": "analyzing"}

    # --- STATE 3: Coding (Triggered by Human 'Proceed') ---
    if event_type == "comment_created":
        comment = payload.get("comment", {}).get("body", "").lower()
        
        if "proceed" in comment:
            current_state = redis_client.hget(f"task:{issue_key}", "state")
            
            # Security check: Only start coding if we are currently awaiting approval
            if current_state == "awaiting_approval":
                logger.info(f"✅ Human approval received for {issue_key}. Starting Production.")
                
                # Move to coding immediately to lock the state
                redis_client.hset(f"task:{issue_key}", "state", "coding") # <--- STATE: coding
                
                plan = redis_client.hget(f"task:{issue_key}", "plan")
                background_tasks.add_task(trigger_production_with_repo, issue_key, repo_context, plan)
                return {"status": "coding"}
            
            else:
                logger.warning(f"⚠️ 'Proceed' ignored for {issue_key}. Current state is {current_state}, not 'awaiting_approval'.")

    return {"status": "ignored"}

# --- HANDOFF WRAPPERS ---

def trigger_analyst(issue_key, repo_context, summary):
    """
    Executes Analyst Phase.
    Moves state: analyzing -> awaiting_approval (via run_analysis)
    """
    try:
        factory = AIFactory(issue_key, repo_context, summary)
        # Inside run_analysis, it will finish by setting state to 'awaiting_approval'
        factory.run_analysis()
    except Exception as e:
        logger.error(f"❌ Analysis failed for {issue_key}: {str(e)}")

def trigger_production_with_repo(issue_key, repo_context, plan):
    """
    Executes the Production Chain.
    Moves states: coding -> integrating -> security_scanning -> reviewing -> completed
    """
    try:
        factory = AIFactory(issue_key, repo_context=repo_context)
        # This method handles all remaining internal state transitions
        factory.run_full_production_chain(issue_key, plan)
    except Exception as e:
        logger.error(f"❌ Production Chain failed for {issue_key} ({repo_context}): {e}")