# Contributing Guide

<!-- markdownlint-disable MD004 -->

KISS first

- Keep diffs small and focused. Aim for a single vertical slice per PR.
- Prefer the minimal tool that does the job. Avoid adding services/dependencies unless essential.
- Ensure every step in README runs on a clean machine with only `requirements-dev.txt` installed.

This project enforces a consistent Python code style for clear diffs, fewer bugs, and fast reviews.

## Spec-first workflow (required)

Before writing code for a non-trivial component, complete a Full Design Spec and the corresponding tests.

Full Design Spec must include:

- Diagrams:
  - Architecture (Mermaid; source under `docs/diagrams/`)
  - UML (class/sequence as appropriate)
  - Data diagram (ERD/class) if applicable
  - Finite State Machine (FSM) if applicable
- Narrative description: purpose, scope, assumptions, constraints
- Interfaces and contracts: inputs, outputs, data shapes, file paths, invariants
- Requirements: numbered, testable statements
- Error modes and edge cases
- Task plan: bullet list of implementation steps

Tests-first (TDD):

- Write pytest tests that map 1:1 to the Requirements in the spec (happy path + at least one edge case).
- Tests must run locally (`make test`) and in pre-commit fast subset when applicable.

Implementation loop:

- Only after the spec and tests are merged (or committed on a feature branch), implement code iteratively with a red→green loop.
- Use the quality gates below; do not merge until all gates pass and all spec tests are green.

Templates:

- Use `docs/templates/FULL_DESIGN_SPEC_TEMPLATE.md` to author specs.
- Optional: `docs/templates/TEST_PLAN_TEMPLATE.md` to outline test mapping.

## Architecture Style Snapshot

- Python 3.11 modular monolith under `src/` (no implicit namespace packages)
- Progressive refactor path: procedural → service classes (encapsulate orchestration/state) → graph orchestration (LangGraph/Dagster)
- Modern typing only: `list[str]`, `| None`, `typing.Annotated` when needed

## Quality Gates (ordered workflow)

1. Design spec (issue / markdown snippet) capturing inputs, outputs, error modes, invariants
1. Characterization tests for any legacy behavior you must preserve
1. OOP / service refactor (introduce class with narrow public surface)
1. Ruff clean (style, imports, docstrings) – zero errors
1. Mypy strict passes (no `# type: ignore` unless justified)
1. (Optional) Docstring coverage gate (interrogate) ≥ target %

Treat each gate as a merge precondition; do not defer earlier gates downstream.

## Tooling (authoritative)

- Ruff: formatting, lint (E,F,I,UP,B,C4,SIM,PL,PT,D,S,T20,ANN,TID,C90)
- Bugbear: via Ruff (B rules)
- Security subset: basic `S` rules (may expand later)
- Typing: Pyright (editor) + mypy strict (CI) – same config assumptions
- Docstrings: Google style enforced via Ruff pydocstyle; optional coverage via `interrogate`
- Line length: 120 (formatter + linter agree)
- Future optional: param/return docstring validator (pydoclint)

## Hard rules (must pass)

- No print/debuggers: `print()`, `breakpoint()`, `pdb.set_trace()` (Ruff T20x)
- No relative imports: absolute imports only (Ruff TID252) – prefer explicit root package path
- No wildcard imports: `from x import *` (Ruff F403/F405)
- Type annotations required for public defs (Ruff ANN + mypy strict)
- Docstrings required for public APIs (Ruff D100–D103 unless intentionally suppressed)
- Cyclomatic complexity: ≤ 10 (Ruff C901) – refactor into helpers early
- Avoid runtime work at import (no heavy I/O or model loads in module top-level)
- Deterministic function signatures (no `**kwargs` for public APIs unless forwarding)
- Group related FastAPI query parameters into a Pydantic model built by a small dependency factory function (avoids B008 and keeps endpoint signatures short)

## Local setup

````bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip ruff mypy pre-commit pydantic
pre-commit install
```text

KISS reminder: Minimal is better. You can also use the Make target which installs only the documented dev tools:

```bash
make dev_setup
source .venv/bin/activate
```text

Single virtual environment policy:

- Use only `.venv` at the project root. Remove any legacy `venv/` or `.venv311/` directories to avoid tooling picking inconsistent interpreters.

- If you previously created extra envs, delete them (after deactivating) with:

  ```bash
  rm -rf venv .venv311
````

- Editors (VS Code / PyCharm) should point to `.venv/bin/python`.

### Pre-commit Hooks

Installed via `pre-commit install`. Current hooks (see `.pre-commit-config.yaml`):

- Ruff (format + lint)
- mdformat (Markdown formatter: GFM + frontmatter; no hard-wrap)
- PyMarkdown (Markdown linter; MD013 disabled to defer line-length to formatter)
- Mypy (strict)
- Interrogate (docstring coverage gate >= fail-under in `pyproject.toml`)
- End-of-file fixer & whitespace cleanup
- Pytest fast subset (`pytest -q -k "not integration"`) on commit
- Pytest full suite on push

Run manually across all files:

````bash
pre-commit run --all-files
```text

If coverage gate fails, add missing docstrings or consciously exclude paths before raising threshold.

### Test Execution Policy

- After each meaningful code change: run fast tests (`pytest -q -k "not integration"`). Use `watchexec` or editor test runner for quick feedback.
- Before every commit: pre-commit automatically runs fast subset (fails fast).
- Before every push: pre-commit (push stage) runs full test suite; push is blocked if any test fails.
- Integration or long-running tests should be marked (e.g., `@pytest.mark.integration`) so they are skipped in the fast subset.
- Keep fast subset < 30s; refactor or further mark slow tests if exceeded.

## Everyday commands

```bash
ruff check . --fix
ruff format .
ruff check .
ruff format --check .
mypy .
```text

## Commit/PR checklist

- [ ] Design spec (for non‑trivial feature) linked in PR description
- [ ] Characterization tests added/updated (when modifying existing behavior)
- [ ] New/refactored code uses service class pattern where appropriate
- [ ] Formatted and linted (Ruff) – zero warnings
- [ ] No prints/debuggers/relative/wildcard imports
- [ ] Public APIs typed + documented (Google docstrings)
- [ ] Complexity ≤ 10 (large functions decomposed)
- [ ] Added/updated tests (happy path + at least one edge case)
- [ ] Mypy strict passes with no new ignores
- [ ] (If enabled) Docstring coverage target met
- [ ] CI green

## Docstring example (Google style)

## Docstring Coverage / Enforcement Options

Baseline: Ruff ensures structural presence but not semantic coverage (e.g., Args names vs. parameters). To tighten:

- `interrogate` – percentage coverage gate. Example snippet in `pyproject.toml`:

```toml
[tool.interrogate]
fail-under = 95
exclude = ["tests", "alembic"]
verbose = 1
style = "google"
```text

- `pydoclint` – validate param/return sections align with signatures.
- Add a pre-commit hook or CI step combining: `ruff check .`, `mypy .`, `pytest -q`, `interrogate -c pyproject.toml`.

Suppress individual docstring rules only with justification: `# noqa: D10x  # Reason...`.

## Refactor Workflow Tip

During migration of a procedural module:

1. Introduce a slim service class (`FooService`) with explicit constructor deps.
1. Port logic into private methods; keep public surface small.
1. Add/expand tests hitting the public methods only.
1. Delete or deprecate legacy free functions (shim if needed temporarily).
1. Once tests + lint + mypy pass, remove shims.

```python
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        Sum of `a` and `b`.
    """
```text

## Recent Refactor Patterns (Ingest & Annotation Endpoints)

The `/ingest` endpoint was decomposed to keep complexity ≤ 10 and improve testability. Key patterns you should emulate when adding or modifying complex endpoints:

- Pure helper functions per ingest variant:
  - `_batch_ingest(book_id, verbose)` – multi‑PDF flow (enumerate, aggregate stats, write chapters)
  - `_ingest_single_stored(book_id, pdf_name, verbose)` – existing stored PDF path
  - `_ingest_uploaded(book_id, file, verbose)` – uploaded file temp handling
- Accumulator object (`_BatchIngestAccumulator`) centralizes metric/state aggregation instead of mutating many locals.
- Shared pre‑work (existing chapter scan) factored into `_gather_existing_chapter_info`.
- Job execution path split into `_job_prepare`, `_job_batch`, `_job_single_pdf`, and `_execute_ingest_job` to isolate orchestration from FastAPI wiring.
- Annotation query parameters are bundled in a lightweight Pydantic model `AnnotationQueryParams` constructed via a dependency function `_annotation_qp_dep` assigned to the constant `ANNOTATION_QP_DEP` used as the endpoint default — avoids calling `Depends(...)` inline in the signature and keeps the function pure for tests.

When facing a large endpoint:

1. Identify side‑effect boundaries (DB writes, file writes, external calls) and isolate them.
1. Create a small accumulator/dataclass if you are returning or computing more than ~4 related metrics.
1. Move query parameter collections into a model + dependency factory.
1. Keep the public endpoint body to orchestration + response shaping only.

This approach eliminated prior `noqa` complexity suppressions; any new endpoint exceeding limits should first attempt this decomposition style.
````
