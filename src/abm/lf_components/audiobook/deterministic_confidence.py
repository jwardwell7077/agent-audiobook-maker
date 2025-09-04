"""Compatibility shim for deterministic confidence scorer.

This module preserves the legacy import path:
    abm.lf_components.audiobook.deterministic_confidence

It re-exports the scorer and config from the new location:
    abm.helpers.deterministic_confidence
"""

from abm.helpers.deterministic_confidence import (  # noqa: F401
    DeterministicConfidenceConfig,
    DeterministicConfidenceScorer,
)

__all__ = [
    "DeterministicConfidenceConfig",
    "DeterministicConfidenceScorer",
]
