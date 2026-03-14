import os
import json
import logging
from fastapi import FastAPI, Request, BackgroundTasks
from redis import Redis
from main import AIFactory # Importing the CrewAI logic we built

app = FastAPI()
# host="redis" because it's inside the docker-compose network
redis_client = Redis(host="redis", port=6379, decode_responses=True)
logger = logging.getLogger("uvicorn")

@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    issue = payload.get("issue", {})
    issue_key = issue.get("key")
    
    if not issue_key:
        return {"status": "Ignored"}

    event_type = payload.get("webhookEvent")
    status = issue.get("fields", {}).get("status", {}).get("name")

    # --- FLOW 1: INITIAL TRIGGER (STATUS CHANGE) ---
    if status == "In Progress" and event_type == "jira:issue_updated":
        summary = issue.get("fields", {}).get("summary", "")
        components = [c.get("name") for c in issue.get("fields", {}).get("components", [])]
        
        # Store initial context in Redis
        redis_client.hset(f"task:{issue_key}", mapping={
            "summary": summary,
            "components": json.dumps(components),
            "state": "analyzing"
        })
        
        background_tasks.add_task(trigger_analyst, issue_key, summary)
        return {"status": "Analyst Started"}

    # --- FLOW 2: APPROVAL TRIGGER (COMMENT) ---
    if event_type == "comment_created":
        comment_body = payload.get("comment", {}).get("body", "").lower()
        if "proceed" in comment_body:
            # Check if we have an analyzed plan in Redis
            task_data = redis_client.hgetall(f"task:{issue_key}")
            if task_data and task_data.get("state") == "awaiting_approval":
                background_tasks.add_task(trigger_developer, issue_key, task_data.get("plan"))
                return {"status": "Developers Authorized"}
            else:
                return {"status": "Error", "reason": "No approved plan found in Redis for this ticket"}

    return {"status": "Ignored"}

def trigger_analyst(issue_key, summary):
    factory = AIFactory(issue_key, summary)
    plan_output = factory.run_analysis()
    
    # SAVE the Analyst's plan to Redis so the Dev Agent can read it later
    redis_client.hset(f"task:{issue_key}", mapping={
        "plan": str(plan_output),
        "state": "awaiting_approval"
    })
    logger.info(f"Analysis saved for {issue_key}. Awaiting 'Proceed' comment.")

def trigger_developer(issue_key, plan):
    factory = AIFactory(issue_key, "Execute approved plan")
    factory.run_production(plan)
    redis_client.hset(f"task:{issue_key}", "state", "coding")
