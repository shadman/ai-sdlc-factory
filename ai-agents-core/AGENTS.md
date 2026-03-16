# 🤖 AI Factory Orchestrator Manual (v4.0)

The "Brain" of the ecosystem. This service manages AI agents that write, test, repair, and document code across multiple repositories.

## 🎯 Mission
You are the management layer of a multi-repo AI SDLC. You coordinate between Python (Backend) and Angular (Frontend) while maintaining a 100% synchronized API contract and a clean Git history within 16GB RAM constraints.

## 🏗️ Architecture
- **Orchestrator (`ai-agents-core`)**: Centralized agent logic, Redis state management, and Jira webhooks.
- **Managed Repos**: Independent Backend and Frontend repositories with integrated CI/CD hooks.
- **Observability**: Real-time tracing via **Arize Phoenix** (http://localhost:6006).

## ⚡ Key Features
- **Autonomous Repair**: AI agents use a `RepairTool` to patch CI failures without human intervention.
- **Multi-Repo Context**: Agents dynamically target `/app/repos/backend` or `/app/repos/frontend`.
- **Human-in-the-Loop**: Agents handle the heavy lifting, but human approval is required for PR merges.

## 🏗️ Orchestration & State Machine (Redis)
You must update the Redis key `task:[ISSUE_KEY]` at every transition.
- **`analyzing`**: Analyst mapping impacts and reading repo laws.
- **`awaiting_approval`**: Waiting for Human "Proceed" comment in Jira.
- **`coding`**: Backend/Frontend agents writing logic to local volumes.
- **`integrating`**: Integrator verifying the API contract/JSON keys.
- **`security_scanning`**: SecOps running Bandit and NPM Audit.
- **`reviewing`**: Documentation updates, Branching, and PR creation.
- **`completed`**: All PRs submitted and final approval logged.

## 🚦 Routing & RAM Logic
- **Sequential Execution:** Never run parallel tasks. Use `Process.sequential` to protect system memory.
- **Component Routing:** If Jira `components` is "Backend" only, do not spin up the Frontend agent.

## 📊 Phase 1: Analyst Confidence Scoring
- **Rubric:** Clarity (40pt), Context (30pt), Safety (30pt).
- **Threshold:** If Score < 75, do not offer "Proceed". Request **"Clarification"** from the human.

## 💻 Phase 2: Specialized Development & Integration
- **Backend Agent:** Strictly `/app/repos/backend`. Use Type Hints & Pydantic.
- **Frontend Agent:** Strictly `/app/repos/frontend`. Use Standalone Components & Signals.
- **Integrator Agent:** - Verify `snake_case` (Python) to `camelCase` (Angular) mapping.
    - Match FastAPI decorators to Angular `ApiService` paths.

## 🛡️ Phase 3: Git, Documentation & Gatekeeping
- **Doc Agent:** - Append changes to the "History" section of the repo-specific `AGENTS.md`.
    - Synchronize `README.md` with any new environment variables.
- **Git Operations Manager:**
    - **Authentication:** Use `GITHUB_TOKEN` from the environment.
    - **Workflow:** 1. Set `git config user.email` and `user.name`.
        2. Create branch `feature/[ISSUE_KEY]`.
        3. Commit all changes.
        4. Push and execute `gh pr create --title "[ISSUE_KEY] Implementation" --body "Automated PR by AI Factory"`.
- **Security Agent:** Block the PR if `Bandit` returns "High" severity or if `NPM Audit` finds critical vulnerabilities.
- **Reviewer Agent:** Perform a "Reflection" step. Verify that the generated PR URLs match the requested changes in the Jira ticket.

## 🚀 Getting Started
1. **Start the Factory**: 
   `docker-compose --profile ai up -d`
2. **Access Phoenix UI**: 
   `http://localhost:6006`
3. **Onboarding**: 
   See [CI_INSTRUCTIONS.md](ai-agents-core/CI_INSTRUCTIONS.md) to link your repositories.

## 🛠️ Tech Stack
- **CrewAI**: Multi-agent orchestration.
- **Ollama**: Local LLM execution.
- **FastAPI**: Webhook listener for Jira and CI events.
- **Redis**: State machine for agent tasks.

## 📁 Workspace Paths
- **Backend Repo:** `/app/repos/backend`
- **Frontend Repo:** `/app/repos/frontend`
- **State Store:** `redis:6379`
- **LLM Endpoint:** `http://ollama:11434`

By Shadman Jamil (https://github.com/shadman)