# 🚀 AI Factory: Repository Integration Guide

This guide covers how to connect a new repository (Backend or Frontend) to the AI Factory Orchestrator.

## 1. Setup the CI/CD Hook
To enable AI-assisted auto-healing, add the following file to your repository:
`/.github/workflows/ci.yml`

* **For Backend:** Use the Python/Pytest CI template.
* **For Frontend:** Use the Node/Angular CI template.

## 2. Setup the Deployment Hook
To automate shipping code after a successful merge, add:
`/.github/workflows/deploy.yml`

* **Requirement:** Ensure `DEPLOYMENT_WEBHOOK_URL` is set in your GitHub Repository Secrets.

## 3. Configuration & Secrets
Each repository must have these GitHub Action Secrets:
- `GITHUB_TOKEN`: PAT with 'repo' scope.
- `DOCKER_USERNAME` / `DOCKER_PASSWORD`: (Backend only) For container registry access.
- `DEPLOYMENT_WEBHOOK_URL`: Your server's endpoint for `docker pull && docker-compose up -d`.

## 4. The Workflow
1. **Ticket Creation:** A Jira ticket is moved to **"In Progress"**.
2. **Analysis:** The `Analyst Agent` creates a technical plan (viewable in Jira/Phoenix).
3. **Coding:** The `Backend/Frontend Agent` implements the logic.
4. **Self-Healing:** If CI tests fail, the Factory automatically applies a patch.
5. **Approval:** The `Reviewer Agent` checks logs in Arize Phoenix (http://localhost:6006) and opens a PR.
6. **Deployment:** Once merged to `main`, the `deploy.yml` pipeline triggers automatically.

## 5. Troubleshooting
If the AI is not healing your code:
- Check the **Redis** state: `redis-cli hget task:[ISSUE_KEY] state`
- Check the **Arize Phoenix** logs at `http://localhost:6006` to see what the agent "thought" when it tried to repair the code.
- Ensure the `ai-squad` container has permission to write to your repository branch.

---
*Questions? Contact the AI Factory Team.*