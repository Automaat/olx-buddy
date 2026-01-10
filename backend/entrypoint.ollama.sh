#!/bin/bash
set -e

echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama to be ready..."
until curl -s http://localhost:11434/api/tags >/dev/null 2>&1; do
    sleep 1
done

echo "Pulling llama3.2-vision model..."
ollama pull llama3.2-vision

echo "Ollama is ready with llama3.2-vision model"
wait $OLLAMA_PID
