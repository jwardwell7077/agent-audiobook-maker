"""Compatibility shim for deterministic confidence scorer.

This module preserves the legacy import path:
    abm.lf_components.audiobook.deterministic_confidence

It re-exports the scorer and config from the new location:
    abm.helpers.deterministic_confidence

TODO (deprecate and remove this shim):
- Migrate all imports in code, tests, and LangFlow flows to
    `abm.helpers.deterministic_confidence`.
- Ensure LangFlow runtime has PYTHONPATH including `src/` so `abm.*` resolves.
- After migration is complete, delete this file.
- Target removal date: 2025-09-30 (adjust if needed).
"""

from abm.helpers.deterministic_confidence import (  # noqa: F401
    DeterministicConfidenceConfig,
    DeterministicConfidenceScorer,
)

__all__ = [
    "DeterministicConfidenceConfig",
    "DeterministicConfidenceScorer",
]
