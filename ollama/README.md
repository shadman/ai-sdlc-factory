---
title: Ollama LLM Server
emoji: 🧠
colorFrom: orange
colorTo: red
sdk: docker
app_port: 11434
pinned: false
---

# 🧠 Ollama LLM Server

Standalone local LLM server powered by [Ollama](https://ollama.com).
Automatically pulls and serves the configured model on first start.
No token limits, no API costs — runs entirely within the container.

---

## What It Does

- Starts the Ollama server on port `11434`
- Pulls the configured model on first run (cached in volume for restarts)
- Exposes a standard OpenAI-compatible REST API consumed by the agents-api

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `deepseek-coder-v2:lite` | Model to pull and serve |

### Setting secrets on Hugging Face

Go to your Space → **Settings → Variables and Secrets** and add:

```
OLLAMA_MODEL   deepseek-coder-v2:lite
```

Other model options:

| Model | Size | Best For |
|---|---|---|
| `deepseek-coder-v2:lite` | ~9GB | Code generation (recommended) |
| `llama3.1:8b` | ~5GB | General tasks, faster |
| `codellama:13b` | ~8GB | Code tasks alternative |
| `deepseek-coder:6.7b` | ~4GB | Lightest option |

---

## API

Once running, the Ollama API is available at the Space URL:

```
GET  /api/tags          # list available models
POST /api/generate      # generate a completion
POST /api/chat          # chat completion
```

In your agents-api Space, set:

```
OLLAMA_HOST    https://your-org-ai-sdlc-ollama.hf.space
LLM_PROVIDER   ollama
LLM_MODEL      deepseek-coder-v2:lite
```

---

## Important — First Start

On the first run the container will **download the model** before becoming
available. This can take several minutes depending on model size and network
speed. Subsequent restarts are instant as the model is cached.

> **No GPU on HF free tier:** Inference runs on CPU and will be slower than
> a local GPU setup. For faster responses consider using
> [Groq](https://console.groq.com) (free, no limits) as an alternative.

---

## Local Development

```bash
cp .env.sample .env
docker-compose up -d --build
# Watch model download progress:
docker logs -f ai-brain
```

API available at: [http://localhost:11434/api/tags](http://localhost:11434/api/tags)
