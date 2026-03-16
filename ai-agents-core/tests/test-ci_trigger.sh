#!/bin/bash
# test_trigger.sh - Simulate a CI/CD Test Failure

echo "🚀 Simulating Backend Test Failure..."

curl -X POST http://localhost:8000/webhook/jira \
     -H "Content-Type: application/json" \
     -d '{
           "issue": {"key": "FACTORY-101"}, 
           "event": "test_failed",
           "repo": "backend"
         }'

echo -e "\n✅ Trigger sent. Check the Factory logs!"