#!/bin/bash
set -e

echo "Installing curl..."
apt-get update -qq && apt-get install -y -qq curl >/dev/null 2>&1

echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama to be ready..."
MAX_WAIT_SECONDS=60
WAITED_SECONDS=0
until curl -sf http://localhost:11434/api/tags >/dev/null; do
    sleep 1
    WAITED_SECONDS=$((WAITED_SECONDS + 1))
    if [ "$WAITED_SECONDS" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "Error: Ollama did not become ready within ${MAX_WAIT_SECONDS} seconds." >&2
        exit 1
    fi
done

echo "Checking for llama3.2-vision model..."
set +e
if ollama list 2>/dev/null | awk '{print $1}' | grep -qx 'llama3.2-vision'; then
    echo "Model llama3.2-vision already present, skipping pull."
else
    echo "Pulling llama3.2-vision model..."
    if ! ollama pull llama3.2-vision; then
        echo "Warning: Failed to pull llama3.2-vision model. Continuing without it." >&2
    fi
fi
set -e

echo "Ollama is ready with llama3.2-vision model"
wait $OLLAMA_PID
