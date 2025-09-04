# Dependencies

Use `requirements.txt` for runtime and `requirements-dev.txt` for development.

- `requirements.txt`: minimal runtime pins used in production/CI.
- `requirements-dev.txt`: `-r requirements.txt` plus linters, tests, docs tools.

With uv (fast):

```bash
python -m pip install -U pip uv
uv pip install --system -r requirements-dev.txt
```

With venv locally:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
```

Troubleshooting:

- If CI fails on uv complaining about missing venv, use `--system` (already applied in workflows).
- If a new machine fails to resolve packages, ensure Python 3.11 is used and update pip: `pip install -U pip`.
