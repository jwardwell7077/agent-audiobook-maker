"""Classifier package exports.

Expose the primary entrypoint ``classify_sections`` and maintain a
backward-compatible alias ``classify_blocks``.
"""

from abm.classifier.section_classifier import classify_sections as classify_sections

# Back-compat alias used by older callers/tests
classify_blocks = classify_sections

__all__ = ["classify_sections", "classify_blocks"]
