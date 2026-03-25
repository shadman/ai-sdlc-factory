#!/bin/bash
set -e

MODEL="${OLLAMA_MODEL:-deepseek-coder-v2:lite}"

echo "🧠 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait until the server is accepting connections
echo "⏳ Waiting for Ollama to be ready..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Ollama server is up."

# Pull model only if not already cached in the volume
if ollama list | grep -q "${MODEL%%:*}"; then
    echo "✅ Model '$MODEL' already present — skipping pull."
else
    echo "📦 Pulling model: $MODEL (this may take a few minutes on first run)..."
    ollama pull "$MODEL"
    echo "✅ Model '$MODEL' ready."
fi

# Hand back to the Ollama server process
wait $OLLAMA_PID
