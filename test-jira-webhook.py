import requests
import json

# Point where you hosted jira listner
# Adjust port if necessary
URL = "http://localhost:8000/webhook/jira"

def simulate_in_progress():
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "ECO-101",
            "fields": {
                "summary": "Add a discount code field to the checkout page",
                "status": {"name": "In Progress"},
                "components": [{"name": "Frontend"}, {"name": "Backend"}]
            }
        }
    }
    print("🚀 Simulating 'In Progress' status...")
    response = requests.post(URL, json=payload)
    print(f"Response: {response.json()}")

def simulate_proceed_comment():
    payload = {
        "webhookEvent": "comment_created",
        "issue": {"key": "ECO-101"},
        "comment": {
            "body": "This plan looks solid. Proceed."
        }
    }
    print("\n✅ Simulating 'Proceed' comment...")
    response = requests.post(URL, json=payload)
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    # 1. First, start the analysis
    simulate_in_progress()
    
    print("\n--- Wait for Analyst to finish (Check Docker logs) ---")
    print("--- Once Analyst posts to Redis, run the Proceed simulation ---")
    
    # 2. Uncomment the line below to simulate your approval after the Analyst is done
    # simulate_proceed_comment()
