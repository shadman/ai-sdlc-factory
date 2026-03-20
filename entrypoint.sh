#!/bin/bash
# Authenticate the GitHub CLI
echo $GITHUB_TOKEN | gh auth login --with-token
# Run the actual application
python ai-agents-core/jira_listener.py