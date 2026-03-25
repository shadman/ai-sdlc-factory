---
title: Phoenix Observability
emoji: 📊
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 6006
pinned: false
---

# 📊 Phoenix Observability

Standalone [Arize Phoenix](https://phoenix.arize.com) observability server.
Traces every agent step, LLM call, tool use, and token count across the
entire AI SDLC pipeline — in real time.

---

## What It Traces

Every action from the agents-api is captured:

- LLM prompts and completions (with token counts)
- Each CrewAI agent execution step
- Tool calls (shell, file read, Jira comment)
- Full task chains from analysis → branching → coding → PR

---

## Ports

| Port | Purpose |
|---|---|
| `6006` | Phoenix web UI — browse traces |
| `4317` | OTLP gRPC collector — agents send traces here |
| `4318` | OTLP HTTP collector — alternative transport |

---

## Connecting agents-api

In your agents-api Space → **Settings → Variables and Secrets**, add:

```
PHOENIX_ENDPOINT   https://your-org-ai-sdlc-phoenix.hf.space/v1/traces
```

Or leave `PHOENIX_ENDPOINT` **blank** to disable tracing entirely — agents
will run normally, just without observability.

> **Alternative:** Use [Arize Phoenix Cloud](https://app.phoenix.arize.com)
> (free hosted tier) instead of self-hosting. Set:
> ```
> PHOENIX_ENDPOINT   https://app.phoenix.arize.com/v1/traces
> PHOENIX_API_KEY    your-api-key
> ```

---

## No Secrets Required

Phoenix runs fully open with no authentication by default.
No environment variables are needed to start this Space.

---

## Local Development

```bash
docker-compose up -d
# UI: http://localhost:6006
# Set in root .env: PHOENIX_ENDPOINT=http://localhost:4317
```

---

## Usage

Once running open the UI and you will see:

- **Traces** tab — full execution tree per Jira ticket
- **LLM** tab — model calls with latency and token usage
- **Spans** — individual tool and agent steps with inputs/outputs

This is especially useful for debugging why an agent made a wrong decision
or why a task failed mid-chain.
