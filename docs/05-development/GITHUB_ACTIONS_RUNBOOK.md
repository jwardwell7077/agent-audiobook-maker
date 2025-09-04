# GitHub Actions Runbook

This runbook covers common Actions maintenance: canceling backlogged runs, avoiding duplicates, and keeping CI fast and cheap.

## Cancel queued or in‑progress runs

UI

- Repo → Actions → click a run → Cancel workflow (top-right).

CLI

- List recent runs:
  - gh run list -L 50
- Cancel queued:
  - gh run list -L 200 --json databaseId,status -q 'map(select(.status=="queued")) | .[].databaseId' | xargs -r -n1 gh run cancel
- Cancel in-progress (optional):
  - gh run list -L 200 --json databaseId,status -q 'map(select(.status=="in_progress")) | .[].databaseId' | xargs -r -n1 gh run cancel
- Cancel everything except completed (one-liner):
  - gh run list -L 200 --json databaseId,status -q 'map(select(.status != "completed")) | .[].databaseId' | xargs -r -n1 gh run cancel
- Auth check:
  - gh auth status

References

- Cancel runs: <https://docs.github.com/actions/managing-workflow-runs/canceling-a-workflow>
- gh run list: <https://cli.github.com/manual/gh_run_list>
- gh run cancel: <https://cli.github.com/manual/gh_run_cancel>
- gh formatting: <https://cli.github.com/manual/gh_help_formatting>

## Prevent backlogs (already applied)

- Concurrency (cancels previous run on same ref):
  
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
- Path filters to skip docs‑only changes (see `.github/workflows/ci.yml`, `quality-gate.yml`, `codeql.yml`).
- Prefer pull_request trigger; allow push on `main` only.
- Single Python (3.11) and uv for faster installs.

## Cost visibility

- Repo usage: Settings → Actions → Usage
- Personal/org billing: check your account/organization billing pages for Actions usage.

## Local-first workflow

- Fast setup:
  - make dev_setup_uv
- Quick local checks:
  - make pre_push
- Optional pre-push hook:
  - make install_git_hooks
