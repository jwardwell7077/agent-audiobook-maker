# KISS Policy for Agent Audiobook Maker

Last updated: 2025-08-21

This repository explicitly adopts KISS — Keep It Simple, Simple.

Guiding rules

- Favor the smallest working slice. Ship a thin vertical slice over a broad incomplete surface.
- Defer infrastructure. Add Docker, DB, orchestrators, and GPUs only when a running slice demands it.
- One obvious way. Prefer one code path and one tool per job; remove fallbacks that add nondeterminism.
- Local-first by default. Design to work offline with files on disk; services are optional add-ons.
- Deterministic over clever. If a “smart” heuristic adds drift, prefer a deterministic simpler approach.
- Write docs for the next person. Every command in README must run on a clean machine.

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
