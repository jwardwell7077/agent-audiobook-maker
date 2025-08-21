# Contributing Guide

This project enforces a consistent Python code style for clear diffs, fewer bugs, and fast reviews.

## Tooling (authoritative)

* Ruff: formatter + linter + import sorting
* Bugbear: enabled via Ruff (B rules)
* Typing: Pyright in editor (strict), mypy in CI (strict)
* Docstrings: Google style
* Line length: 120

## Hard rules (must pass)

* No print/debuggers: `print()`, `breakpoint()`, `pdb.set_trace()` (Ruff T20x)
* No relative imports: absolute imports only (Ruff TID252)
* No wildcard imports: `from x import *` (Ruff F403/F405)
* Type annotations required for public defs (Ruff ANN + mypy strict)
* Docstrings required for public APIs (Ruff D, Google style)
* Cyclomatic complexity: ≤ 10 (Ruff C901)

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip ruff mypy pre-commit pydantic
pre-commit install
```

## Everyday commands

```bash
ruff check . --fix
ruff format .
ruff check .
ruff format --check .
mypy .
```

## Commit/PR checklist

* [ ] Formatted and linted (Ruff)
* [ ] No prints/debuggers/relative/wildcard imports
* [ ] Public APIs typed + documented (Google)
* [ ] Complexity ≤ 10
* [ ] CI green

## Docstring example

```python
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        Sum of `a` and `b`.
    """
```
