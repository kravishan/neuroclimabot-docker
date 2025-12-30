#!/bin/bash

echo "🤖 Setting up Ollama LLM..."
echo ""

# Check if Ollama container is running
if ! docker ps | grep -q neuroclima-ollama; then
    echo "❌ Ollama container is not running. Please run './start.sh' first."
    exit 1
fi

echo "📥 Downloading Mistral 7B model (this may take a while)..."
docker exec -it neuroclima-ollama ollama pull mistral:7b

echo ""
echo "✅ Ollama model downloaded successfully!"
echo ""
echo "Available models:"
docker exec neuroclima-ollama ollama list
echo ""
echo "💡 You can now use the application with local LLM support"
