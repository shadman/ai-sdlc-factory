---
title: Jira Webhook Listener
emoji: 🎧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# 🎧 Jira Webhook Listener

Lightweight standalone FastAPI service that receives Jira webhook events and
delegates all AI agent work to the Agents API via HTTP. No AI dependencies —
just a thin router between Jira and your agent squad.

---

## Architecture

```
Jira ──POST──▶ jira-listener :8000 ──POST──▶ agents-api :9000
                    │
                    └── reads Redis Cloud (state checks only)
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhook/jira` | Health check — open in browser to confirm it's alive |
| POST | `/webhook/jira` | Main Jira webhook receiver |

---

## Event Handling

| Jira Event | Trigger Condition | Calls |
|---|---|---|
| `jira:issue_updated` | Status → `In Progress` | `POST /agents/analyze` |
| `comment_created` | Comment contains `proceed` | `POST /agents/produce` |
| Custom `test_failed` | CI pipeline event | `POST /agents/produce` with logs |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `REDIS_URL` | ✅ | Redis Cloud URL — `rediss://default:<pwd>@<host>:<port>` |
| `AGENTS_API_URL` | ✅ | Full URL of the agents-api service |
| `REDIS_HOST` | fallback | Only if not using `REDIS_URL` |
| `REDIS_PORT` | fallback | Default `6379` |
| `REDIS_PASSWORD` | fallback | Only if not using `REDIS_URL` |

### Setting secrets on Hugging Face

Go to your Space → **Settings → Variables and Secrets** and add:

```
REDIS_URL        rediss://default:<password>@<host>:<port>
AGENTS_API_URL   https://your-org-ai-sdlc-agents.hf.space
```

---

## Jira Webhook Configuration

In Jira → **Settings → System → Webhooks**, create a new webhook:

- **URL:** `https://your-org-jira-listener.hf.space/webhook/jira`
- **Events:** Issue updated, Comment created

---

## Local Development

```bash
cp .env.sample .env
# Fill in REDIS_URL and AGENTS_API_URL
docker-compose up -d --build
```

Health check: [http://localhost:8000/webhook/jira](http://localhost:8000/webhook/jira)

---

## Notes

- This service has **no AI dependencies** — image is under 200MB
- Redis is used **read-only** here (state writes happen in agents-api)
- `AGENTS_API_URL` can point to local, remote, or Hugging Face — just a URL
