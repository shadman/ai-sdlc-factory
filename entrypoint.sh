#!/bin/bash
# Authenticate the GitHub CLI
echo $GITHUB_TOKEN | gh auth login --with-token
# Change into the agent module directory so Python can resolve local imports (e.g. main.py)
cd /app/ai-agents-core
# Start the FastAPI webhook listener
uvicorn jira_listener:app --host 0.0.0.0 --port 8000

uvicorn ai-agents-core.jira_listener:app --host 0.0.0.0 --port 8000