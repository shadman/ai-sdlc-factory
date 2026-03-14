# 🏭 Agentic SDLC Factory (Full-Stack)

This is a localized, AI-driven development environment designed to automate the lifecycle of an E-commerce platform (Angular & Python) using a multi-repo agentic squad.

---

## 🏗️ 1. System Architecture & Workflow

The factory operates as a **State Machine** orchestrated by Redis and CrewAI.

### 📊 Operational Flow
1. **Trigger:** Human moves Jira ticket to **"In Progress"**.
2. **Analyze:** **Analyst Agent** reads repo-specific `AGENTS.md` and posts a **Confidence Score** + **Plan** to Jira.
3. **Wait:** Factory enters `awaiting_approval` state in Redis.
4. **Authorize:** Human comments **"Proceed"** on the ticket.
5. **Execute:** - **Backend Agent** writes Python logic.
    - **Frontend Agent** writes Angular components.
    - **Integrator Agent** ensures API contract synchronization.
6. **Verify:** **Security Agent** (Bandit/NPM Audit) and **Reviewer Agent** validate the work.
7. **Document:** **Doc Agent** updates `AGENTS.md` history.
8. **Finalize:** PR is created and state is marked `completed`.

---

## 🛠️ 2. Tech Stack
| Component | Technology |
| :--- | :--- |
| **LLM Engine** | Ollama (DeepSeek-Coder-V2:Lite) |
| **Orchestrator** | CrewAI |
| **State/Memory** | Redis |
| **Backend** | Python FastAPI + Postgres |
| **Frontend** | Angular 17+ (Standalone, Tailwind) |
| **Observability** | Arize Phoenix (Port 6006) |

---

## 📂 3. Project Structure
```text
.
├── /angular-frontend      # Frontend Repo (Rules in AGENTS.md)
├── /python-backend        # Backend Repo (Rules in AGENTS.md)
├── /ai-agents-core        # Factory Brain
│   ├── AGENTS.md          # Factory SOPs (Standard Operating Procedures)
│   ├── main.py            # CrewAI Squad Definition
│   ├── jira_listener.py   # FastAPI Webhook Gateway
│   └── requirements.txt   # Core Dependencies
├── docker-compose.yml     # Infrastructure (Profiles: 'default', 'ai')
└── README.md              # This file
```


## 🚀 4. Setup Instructions (16GB RAM Optimized)
### Step 1: Launch Infrastructure
Run the app core and the AI factory using Docker profiles.

```
# Start E-commerce App
docker-compose up -d db backend-api frontend-ui

# Start AI Squad & Brain
docker-compose --profile ai up -d
```

### Step 2: Initialize the Brain
Download the specialized coding model into the local Ollama container:

```
docker exec -it ai-brain ollama pull deepseek-coder-v2:lite
```

### Step 3: Configure Environment
Create a .env file in ./ai-agents-core/:

```
JIRA_DOMAIN=yourdomain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-token
REDIS_HOST=redis
PHOENIX_HOST=http://phoenix:6006
```

## 🤖 5. Interacting with the Factory

### The "Confidence Score" Protocol
When the Analyst posts a report, look for the Confidence Score:

Score > 85%: Low risk. Safe to "Proceed".

Score 75% - 85%: Moderate risk. Review the "Technical Plan" carefully before proceeding.

Score < 75%: The AI is confused. Do not type "Proceed". Instead, provide more details in the Jira ticket description.

### The "AGENTS.md" Law
Each repo contains an AGENTS.md. This is the Source of Truth for the AI.

If you want the AI to use a specific library (e.g., ngx-charts), add it to the AGENTS.md of that repo.

If you change the database schema, update the Backend AGENTS.md.

## 📈 6. Monitoring & Troubleshooting
Real-time Thinking: View agent traces at http://localhost:6006.

Logs: Check container logs: docker logs -f ai-squad.

Redis State: Inspect current task state: docker exec -it ai-state redis-cli hgetall task:[YOUR-TICKET-ID].


# The System Architecture
## Operational Flow Diagram
This diagram shows how a Jira ticket transforms into verified code.

```mermaid
sequenceDiagram
    participant H as Human (Jira)
    participant L as FastAPI Listener
    participant R as Redis (State)
    participant A as AI Analyst
    participant D as AI Dev Squad
    participant G as Gatekeepers (Sec/Review)

    H->>L: Move Ticket to "In Progress"
    L->>R: Initialize State (analyzing)
    L->>A: Trigger Analysis
    A->>A: Read Repo AGENTS.md
    A->>H: Post Plan & Confidence Score
    
    Note over H,A: Human Review Gap
    
    H->>L: Comment "Proceed"
    L->>R: Update State (authorized)
    L->>D: Trigger Dev/Integrator
    D->>D: Write Code (BE/FE)
    D->>G: Run Security & Peer Review
    G->>R: Update State (completed)
    G->>H: Create PR & Post Success
```

## Next Step for Team: 
Ensure your Jira Webhooks are pointing to http://[YOUR-IP]:8000/webhook/jira.

```
### What would you like me to do next?
Would you like me to generate a **GitHub Actions workflow** to automate the final deployment once the Reviewer Agent approves the PR?
```


