# KISS Policy for Agent Audiobook Maker

Last updated: 2025-08-21

This repository explicitly adopts KISS — Keep It Simple, Simple.

## Project tenets (short list)

- KISS: ship the smallest working slice.
- TDD + spec-first: write a Full Design Spec and pytest tests (mapped to requirements) before code.
- Local-first artifacts: files on disk are the source of truth; offline by default.
- Reproducible outputs: content-addressed hashes.
- Contract-first: schemas define interfaces and invariants.
- Minimal complexity: simple control flow, small modules, low cognitive load; decompose early.

Lean workflow (today)

1. Python 3.11, local `.venv` only (activate with `source .venv/bin/activate`)
1. Minimal dev tools: ruff, mypy, pytest, pre-commit
1. No app installs until code lands (no -e ., no heavy ML deps)

Upgrade path (when needed)

- Add runtime deps behind a single manifest (`pyproject.toml` or `requirements.txt`)
- Introduce Postgres and LangGraph only when a runnable API/graph exists
- TTS engines (XTTS/Piper) added after annotation JSONL is stable

Definition of done (KISS slice)

- One command to set up, one to run, one to test
- No external services required
- Deterministic outputs for the covered slice

Components path

- Export `LANGFLOW_COMPONENTS_PATH` to include our custom components directory
- Typical value: `export LANGFLOW_COMPONENTS_PATH="$(pwd)/src/abm/lf_components"`

Available components (this branch)

- ABMChapterLoader – book/chapters
- ABMBlockSchemaValidator – normalize + JSONL
- ABMMixedBlockResolver – spans
- ABMSpanClassifier – dialogue/narration
- ABMSpanIterator – simple windowing
- ABMArtifactOrchestrator – blocks → spans → spans_cls → spans_attr

Import sample flow

- Use `examples/langflow/abm_spans_first_pipeline.v15.json`
- Adjust inputs (paths, chapter selection) in the UI

Out of scope (this branch)

- Multi-agent systems
- Databases
- Orchestration frameworks
