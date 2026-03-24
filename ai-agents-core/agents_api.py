import os, json, logging
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List
from redis import Redis
from main import AIFactory

# --- Environment ---
REDIS_URL      = os.getenv("REDIS_URL")           # e.g. rediss://default:<pwd>@host:port
REDIS_HOST     = os.getenv("REDIS_HOST", "redis")
REDIS_PORT     = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agents_api")

app = FastAPI()
if REDIS_URL:
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)

# --- Request Models ---
class AnalyzeRequest(BaseModel):
    issue_key: str
    repo_contexts: List[str]
    summary: str

class ProduceRequest(BaseModel):
    issue_key: str
    repo_contexts: List[str]
    plan: str

# --- Health ---
@app.get("/health")
async def health():
    return {"status": "ok", "service": "agents-api"}

# --- Endpoints ---

@app.post("/agents/analyze")
async def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Trigger Phase 1: Analysis.
    Saves initial context to Redis and kicks off the analyst agent.
    State flow: analyzing -> awaiting_approval
    """
    redis_client.hset(f"task:{req.issue_key}", mapping={
        "state": "analyzing",
        "repo_contexts": json.dumps(req.repo_contexts),
        "summary": req.summary
    })
    background_tasks.add_task(run_analysis, req.issue_key, req.repo_contexts, req.summary)
    logger.info(f"🚀 Analysis queued for {req.issue_key}")
    return {"status": "analyzing", "issue_key": req.issue_key}

@app.post("/agents/produce")
async def produce(req: ProduceRequest, background_tasks: BackgroundTasks):
    """
    Trigger Phase 2: Full Production Chain.
    Covers: coding -> integrating -> security_scanning -> reviewing -> completed
    Also handles CI/CD auto-repair (test_failed events).
    """
    redis_client.hset(f"task:{req.issue_key}", "state", "coding")
    background_tasks.add_task(run_production, req.issue_key, req.repo_contexts, req.plan)
    logger.info(f"🏭 Production chain queued for {req.issue_key}")
    return {"status": "coding", "issue_key": req.issue_key}

# --- Background Workers ---

def run_analysis(issue_key: str, repo_contexts: list, summary: str):
    try:
        factory = AIFactory(issue_key, repo_contexts, summary)
        factory.run_analysis()
        logger.info(f"✅ Analysis completed for {issue_key}")
    except Exception as e:
        logger.error(f"❌ Analysis failed for {issue_key}: {str(e)}")
        redis_client.hset(f"task:{issue_key}", "state", "analysis_failed")

def run_production(issue_key: str, repo_contexts: list, plan: str):
    try:
        factory = AIFactory(issue_key, repo_contexts=repo_contexts)
        factory.run_full_production_chain(issue_key, repo_contexts, plan)
        logger.info(f"✅ Production chain completed for {issue_key}")
    except Exception as e:
        logger.error(f"❌ Production chain failed for {issue_key}: {e}")
        redis_client.hset(f"task:{issue_key}", "state", "production_failed")
