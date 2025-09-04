#!/bin/bash
# Ollama Model Setup Script for ABM (legacy banners removed)
# This script pulls and configures the LLM models needed for dialogue classification

set -e

echo "🤖 Setting up Ollama models for ABM..."

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be available..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  echo "   Waiting for Ollama service..."
  sleep 5
done
echo "✅ Ollama is ready!"

# Pull lightweight model for dialogue classification (good for fallback scenarios)
echo "📥 Pulling Llama 3.2 3B model for dialogue classification..."
ollama pull llama3.2:3b

# Alternative: Pull Phi-3 Mini (even more lightweight, good for classification tasks)
echo "📥 Pulling Phi-3 Mini for fast inference..."
ollama pull phi3:mini

# Create custom modelfile for dialogue classification if needed
cat > /tmp/dialogue-classifier.Modelfile << 'EOF'
FROM llama3.2:3b

PARAMETER temperature 0.1
PARAMETER top_k 10
PARAMETER top_p 0.1
PARAMETER repeat_penalty 1.1

SYSTEM """You are a dialogue classification specialist for audiobooks. Your job is to classify text segments as either 'dialogue' or 'narration' with high accuracy.

Rules:
1. Dialogue: Direct speech by characters, typically marked by quotes
2. Narration: Descriptive text, exposition, action descriptions
3. Mixed: Segments containing both dialogue and narration

Respond with only: dialogue, narration, or mixed

Be concise and accurate. Focus on the primary content type in ambiguous cases."""
EOF

echo "🎯 Creating specialized dialogue classification model..."
ollama create dialogue-classifier -f /tmp/dialogue-classifier.Modelfile

# Test the models
echo "🧪 Testing model functionality..."
echo "Testing basic model response..."
echo "\"Hello, how are you?\" she asked with a smile." | ollama run llama3.2:3b "Classify this text as 'dialogue', 'narration', or 'mixed':"

echo "✅ Ollama setup complete!"
echo ""
echo "📋 Available models:"
ollama list

echo ""
echo "🔧 Models configured for ABM:"
echo "  - llama3.2:3b - Primary model for AI fallback classification"
echo "  - phi3:mini - Lightweight alternative for fast inference"
echo "  - dialogue-classifier - Specialized model for dialogue classification"
echo ""
echo "🎯 Ready for integration with ABM Dialogue Classifier Agent!"
