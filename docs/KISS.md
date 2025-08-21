# KISS Policy for Agent Audiobook Maker

Last updated: 2025-08-21

This repository explicitly adopts KISS — Keep It Simple, Simple.

## Project tenets (short list)

- KISS: ship the smallest working slice.
- TDD + spec-first: write a Full Design Spec and pytest tests (mapped to requirements) before code.
- Local-first artifacts: files on disk are the source of truth; offline by default.
- Deterministic + reproducible: same inputs → same outputs; content-addressed hashes.
- Contract-first: schemas define interfaces and invariants.
- Minimal deps: defer Docker/DB/GPUs/orchestrators until the slice truly needs them.

Lean workflow (today)

1) Python 3.11, local `.venv` only
2) Minimal dev tools: ruff, mypy, pytest, pre-commit
3) No app installs until code lands (no -e ., no heavy ML deps)

Upgrade path (when needed)

- Add runtime deps behind a single manifest (`pyproject.toml` or `requirements.txt`)
- Introduce Postgres and LangGraph only when a runnable API/graph exists
- TTS engines (XTTS/Piper) added after annotation JSONL is stable

Definition of done (KISS slice)

- One command to set up, one to run, one to test
- No external services required
- Deterministic outputs for the covered slice
