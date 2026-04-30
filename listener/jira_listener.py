import os, json, logging, uuid
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from redis import Redis

# --- Environment ---
REDIS_URL      = os.getenv("REDIS_URL")           # e.g. rediss://default:<pwd>@host:port (Redis Cloud)
REDIS_HOST     = os.getenv("REDIS_HOST", "redis")
REDIS_PORT     = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")       # fallback if not using full URL
AGENTS_API_URL = os.getenv("AGENTS_API_URL", "http://agents-api:9000")

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jira_listener")

# --- Redis (read-only — state checks only) ---
if REDIS_URL:
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                         decode_responses=True, ssl=True)

app = FastAPI()

# --- Health check (browser-friendly GET) ---
@app.get("/health")
async def health():
    return {"status": "ok", "message": "Jira webhook listener is alive"}

# --- Main Jira Webhook (POST) ---
@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    # --- CI/CD Auto-Repair (test_failed events from your CI pipeline) ---
    if payload.get("event") == "test_failed":
        issue = payload.get("issue", {})
        issue_key = issue.get("key") or f"INTERNAL-{uuid.uuid4().hex[:6].upper()}"
        repo_context = payload.get("repo", "backend")
        logs = payload.get("logs", "No logs provided.")
        repair_plan = f"CI Failure detected. Error Logs:\n{logs}"

        logger.info(f"🛠️ CI/CD Auto-Repair triggered for {issue_key}")
        background_tasks.add_task(call_agents_produce, issue_key, [repo_context], repair_plan)
        return {"status": "repairing", "issue_key": issue_key}

    # --- Standard Jira Webhook ---
    issue = payload.get("issue", {})
    issue_key = issue.get("key")
    if not issue_key:
        return {"status": "ignored"}

    event_type = payload.get("webhookEvent")
    fields     = issue.get("fields", {})
    status     = fields.get("status", {}).get("name")
    summary    = fields.get("summary", "")
    components = [c.get("name", "").lower() for c in fields.get("components", [])]
    labels     = [l.lower() for l in fields.get("labels", [])]

    repo_contexts = []
    if "backend"  in components or "backend"  in labels: repo_contexts.append("backend")
    if "frontend" in components or "frontend" in labels: repo_contexts.append("frontend")
    if not repo_contexts:
        repo_contexts = ["backend"]
        logger.info(f"⚠️ No context labels on {issue_key}, defaulting to ['backend']")

    # STATE 1: In Progress -> trigger analysis
    if status == "In Progress" and event_type == "jira:issue_updated":
        logger.info(f"🚀 Triggering analysis for {issue_key}")
        background_tasks.add_task(call_agents_analyze, issue_key, repo_contexts, summary)
        return {"status": "analyzing", "contexts": repo_contexts}

    # STATE 2: Human comments 'proceed' -> trigger production
    if event_type == "comment_created":
        comment = payload.get("comment", {}).get("body", "").lower()
        if "proceed" in comment:
            current_state     = redis_client.hget(f"task:{issue_key}", "state")
            saved_contexts    = redis_client.hget(f"task:{issue_key}", "repo_contexts")
            plan              = redis_client.hget(f"task:{issue_key}", "plan")
            resolved_contexts = json.loads(saved_contexts) if saved_contexts else repo_contexts

            if current_state == "awaiting_approval":
                logger.info(f"✅ Approval received for {issue_key}. Triggering production.")
                background_tasks.add_task(call_agents_produce, issue_key, resolved_contexts, plan)
                return {"status": "coding"}
            else:
                logger.warning(f"⚠️ 'Proceed' ignored — {issue_key} state is '{current_state}', expected 'awaiting_approval'")

    return {"status": "ignored"}

# --- HTTP calls to agents-api (run in background thread) ---

def call_agents_analyze(issue_key: str, repo_contexts: list, summary: str):
    try:
        resp = requests.post(
            f"{AGENTS_API_URL}/agents/analyze",
            json={"issue_key": issue_key, "repo_contexts": repo_contexts, "summary": summary},
            timeout=30
        )
        resp.raise_for_status()
        logger.info(f"📡 agents-api accepted analyze for {issue_key}: {resp.json()}")
    except Exception as e:
        logger.error(f"❌ Failed to reach agents-api (analyze) for {issue_key}: {e}")

def call_agents_produce(issue_key: str, repo_contexts: list, plan: str):
    try:
        resp = requests.post(
            f"{AGENTS_API_URL}/agents/produce",
            json={"issue_key": issue_key, "repo_contexts": repo_contexts, "plan": plan},
            timeout=30
        )
        resp.raise_for_status()
        logger.info(f"📡 agents-api accepted produce for {issue_key}: {resp.json()}")
    except Exception as e:
        logger.error(f"❌ Failed to reach agents-api (produce) for {issue_key}: {e}")
