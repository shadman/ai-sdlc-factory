#!/bin/bash
# Authenticate the GitHub CLI (only if token is available)
if [ -n "$GITHUB_TOKEN" ]; then
    echo $GITHUB_TOKEN | gh auth login --with-token
fi
# Change into the agent module directory so Python can resolve local imports (e.g. main.py)
cd /app/ai-agents-core
# Start the FastAPI webhook listener
uvicorn jira_listener:app --host 0.0.0.0 --port 7860
