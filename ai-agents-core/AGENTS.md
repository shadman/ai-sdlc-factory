# AI Factory Orchestrator Manual (v2.0)

## Orchestration Logic
- **Routing:** Use Jira `components` to decide which developer agents to activate.
- **Dependency:** If both `Frontend` and `Backend` are present, the **Integrator Agent** must define the API contract before coding starts.

## Phase 1: Analyst Confidence Scoring
You must calculate a score (0-100) based on:
1. **Clarity (40pts):** Are the requirements in the Jira ticket unambiguous?
2. **Context (30pts):** Do you have access to all relevant files in `/repos`?
3. **Safety (30pts):** Does the plan comply with the tech-specific `AGENTS.md`?
*If Score < 75, do not ask for "Proceed." Ask for "Clarification."*

## Phase 2: Specialized Development
- **Backend Agent:** Focus strictly on `/repos/backend`. Use Python type hints.
- **Frontend Agent:** Focus strictly on `/repos/frontend`. Use Angular Standalone components.
- **Integrator Agent:** Must verify that the Frontend service calls match the Backend controller routes.

## Phase 3: Gatekeeping
- **Security Agent:** Mandatory scan using `Bandit` (Python) and `NPM Audit` (Angular).
- **Doc Agent:** Must append the change summary to the "History" section of the repo's `AGENTS.md`.

