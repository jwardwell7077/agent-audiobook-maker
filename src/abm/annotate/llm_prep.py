"""Candidate extractor for Stage B LLM refinement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMCandidateConfig:
    """Configuration for selecting spans that require LLM refinement.

    Attributes:
        conf_threshold: Confidence above which spans are skipped.
        types: Span types eligible for refinement.
    """

    conf_threshold: float = 0.90
    types: frozenset[str] = frozenset({"Dialogue", "Thought"})


class LLMCandidatePreparer:
    """Collect spans that need LLM help (Unknown or low-confidence).

    Attributes:
        cfg: Selection policy for candidate spans.
    """

    def __init__(self, cfg: LLMCandidateConfig) -> None:
        """Initialize the preparer with a configuration.

        Args:
            cfg: Selection policy for candidate spans.
        Returns:
            None

        Raises:
            None
        """

        self.cfg = cfg

    def prepare(self, combined_doc: dict[str, Any]) -> list[dict[str, Any]]:
        """Return spans requiring refinement.

        Args:
            combined_doc: Parsed ``combined.json`` document from Stage A.

        Returns:
            list[dict[str, Any]]: Candidate span descriptors.

        Raises:
            None
        """

        out: list[dict[str, Any]] = []
        for ch in combined_doc.get("chapters", []):
            roster = ch.get("roster", {}) or {}
            for s in ch.get("spans", []):
                if s.get("type") not in self.cfg.types:
                    continue
                conf = float(s.get("confidence", 0.0))
                if s.get("speaker") != "Unknown" and conf >= self.cfg.conf_threshold:
                    continue
                out.append(
                    {
                        "chapter_index": ch.get("chapter_index"),
                        "title": ch.get("title"),
                        "start": s["start"],
                        "end": s["end"],
                        "type": s["type"],
                        "speaker": s.get("speaker"),
                        "confidence": conf,
                        "roster": roster,
                    }
                )
        return out
