# Getting Started

Welcome! This guide helps you set up and run Agent Audiobook Maker locally.

## Quick Setup

- Python 3.11+ and a virtual environment
- Dev tools from requirements

```bash
# Clone and setup
git clone https://github.com/jwardwell7077/agent-audiobook-maker.git
cd agent-audiobook-maker

# Create virtual environment
python3.11 -m venv .venv || python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -U pip
pip install -r requirements-dev.txt

# Verify setup
make test
```

## Run a Chapter End-to-End

- Prefer Kokoro as the TTS engine; see Engines → Kokoro for server/env notes.
- Use planning + rendering scripts for a chapter. See Pipeline → planning and tts.

## Learn the System

- Overview → Context: overview/context.md
- Overview → Architecture: overview/architecture.md
- Pipeline overview: pipeline/

## Notes

- Local-first artifacts; large media lives under data/ (gitignored)
- Deterministic processing where possible (stable inputs ⇒ stable outputs)