# Getting Started on Linux (Developer Setup)

This guide lets you spin up the repo on a fresh Linux machine and continue development without WSL2.

## Prerequisites

- OS: Ubuntu/Debian (or similar)
- RAM: 8–16GB recommended for tests
- Tools: git, Python 3.10+ (3.11 tested), venv, pip, ffmpeg

Install base packages (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip make ffmpeg
```

Optional: for DB or containerized workflows

```bash
# Install Docker & Compose plugin if you plan to run docker-compose services
# Refer to your distro’s instructions for Docker Engine and docker-compose-plugin
```

## Clone and set up Python environment

```bash
git clone https://github.com/jwardwell7077/agent-audiobook-maker.git
cd agent-audiobook-maker
git fetch origin
git checkout snapshot-2025-08-31-wip
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
```

Sanity check imports:

```bash
python - << 'PY'
import sys, importlib
sys.path.insert(0, 'src')
sc = importlib.import_module('abm.helpers.deterministic_confidence').DeterministicConfidenceScorer()
print('deterministic scorer ok:', sc is not None)
PY
```

## Run tests (fast path)

Run the scoped tests used during active development:

```bash
pytest -q -k "not ingest and not classifier"
```

Targeted tests:

```bash
pytest -q tests/unit_tests/test_span_attribution_continuity.py
pytest -q tests/unit_tests/test_artifact_orchestrator_style_toggle.py
```

## Run demo scripts

```bash
python scripts/demo_confidence_orchestrator.py
```

## Optional: Docker services

If you need DB or isolated services:

```bash
docker compose up -d
# later
docker compose down
```

DB init scripts live under `database/init/`.

## Key data locations

- Inputs: `data/books/`, `data/characters/`, `data/casting/voice_bank.json`
- Outputs: `output/{book_id}/chNN/` (e.g., `spans_attr.jsonl`, meta)
- Logs: `logs/`

## Current contracts you can build against

- spans_attr schema: `docs/02-specifications/data-schemas/spans_attr.schema.json`
- Contract overview: `docs/02-specifications/data-schemas/SPANS_ATTR_CONTRACT.md`
- Deterministic attribution behavior and knobs:
  - See specs in `docs/02-specifications/components/`

## Troubleshooting

- Exit code 137: Usually OOM. Close other apps or increase RAM/swap.
- Port conflicts: Ensure required ports are free.
- Python build deps: If wheels fail, install `build-essential libffi-dev libssl-dev`.
- ffmpeg missing: Install via `apt` as shown above.

## Next steps

- Explore the CLI demos under `scripts/` and `src/abm/*`.
- Validate `spans_attr.jsonl` against the schema (optional if you install `jsonschema`).
- Start downstream work against the spans_attr contract (fields/methods documented in the contract doc).
