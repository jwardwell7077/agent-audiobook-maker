"""Minimal attribution engine used by the annotation CLI.

This placeholder provides the interfaces expected by :class:`AnnotateRunner`.
It does not perform real NLP or speaker attribution; instead it returns a
consistent default result. The real implementation can replace this stub
without affecting the CLI signature.
"""

from __future__ import annotations


class AttributeEngine:
    """Trivial speaker attribution engine."""

    def __init__(self, mode: str = "high", llm_tag: str | None = None) -> None:
        """Initialize the engine.

        Args:
            mode: Quality mode flag (unused).
            llm_tag: Optional backend identifier (unused).
        """
        self.mode = mode
        self.llm_tag = llm_tag
        # Placeholder NER pipeline; the real engine would expose a spaCy model.
        self.ner_nlp = None

    def attribute_span(
        self,
        full_text: str,
        span: tuple[int, int],
        span_type: str,
        roster: dict[str, list[str]],
    ) -> tuple[str, str, float]:
        """Return a dummy attribution for a span.

        Args:
            full_text: Complete chapter text.
            span: Tuple of absolute offsets ``(start, end)``.
            span_type: Span label (e.g., ``"Dialogue"``).
            roster: Mapping of canonical speaker names to aliases.

        Returns:
            A tuple of ``(speaker, method, confidence)``. This stub always
            returns ``("Narrator", "rule:placeholder", 0.0)``.
        """
        return "Narrator", "rule:placeholder", 0.0
