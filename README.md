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