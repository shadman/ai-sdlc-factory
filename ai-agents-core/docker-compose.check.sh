#!/bin/bash
# docker-compose.check.sh - Validation Script

echo "🔍 Validating AI Factory Environment..."

REQUIRED_VARS=(
    "JIRA_URL" "JIRA_USER" "JIRA_API_TOKEN" 
    "GITHUB_TOKEN" "OLLAMA_HOST" "REDIS_HOST"
)

MISSING=0
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ MISSING: $var"
        MISSING=$((MISSING + 1))
    else
        echo "✅ FOUND: $var"
    fi
done

if [ $MISSING -eq 0 ]; then
    echo "🚀 All systems go! Starting Docker Compose..."
    docker-compose --profile ai up -d
else
    echo "🛑 Error: $MISSING variables missing. Please check your .env file."
    exit 1
fi