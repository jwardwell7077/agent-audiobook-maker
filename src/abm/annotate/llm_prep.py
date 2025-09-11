from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class LLMCandidateConfig:
    """Config for selecting spans that should go to the LLM."""

    conf_threshold: float = 0.90
    consider_methods: tuple[str, ...] = (
        "rule:unknown",
        "rule:coref",
        "rule:turn_taking",
        "rule:descriptor",
    )
    window_chars_before: int = 360
    window_chars_after: int = 360
    include_roster: bool = True


@dataclass
class LLMCandidate:
    """Serializable record for one span that needs LLM refinement."""

    chapter_index: int
    chapter_title: str
    span_id: int
    span_type: str
    baseline_speaker: str
    baseline_method: str
    baseline_confidence: float
    text: str
    context_before: str
    context_after: str
    roster: list[str]
    notes: str | None = None
    fingerprint: str | None = None


class LLMCandidatePreparer:
    """Extract low-confidence spans into a JSONL for a separate LLM stage."""

    def __init__(self, config: LLMCandidateConfig | None = None) -> None:
        self.cfg = config or LLMCandidateConfig()

    # ------------------------------ Public API ------------------------------

    def prepare(self, chapters_doc: dict[str, Any]) -> list[LLMCandidate]:
        """Return a list of LLM candidates from an annotated chapters document."""
        out: list[LLMCandidate] = []
        chapters: list[dict[str, Any]] = list(chapters_doc.get("chapters") or [])

        for ch in chapters:
            ch_idx = int(ch.get("chapter_index", -1))
            title = str(ch.get("title") or "")
            text = str(ch.get("text") or "")
            roster_map: dict[str, list[str]] = dict(ch.get("roster") or {})
            roster = sorted(roster_map.keys())

            for s in ch.get("spans", []):
                stype = str(s.get("type"))
                if stype not in {"Dialogue", "Thought"}:
                    continue
                speaker = str(s.get("speaker") or "Unknown")
                method = str(s.get("method") or "")
                conf = float(s.get("confidence", 0.0))
                notes = s.get("notes")

                if self._needs_llm(stype, speaker, method, conf, notes):
                    start, end = int(s.get("start", 0)), int(s.get("end", 0))
                    cbeg = max(0, start - self.cfg.window_chars_before)
                    cend = min(len(text), end + self.cfg.window_chars_after)
                    cand = LLMCandidate(
                        chapter_index=ch_idx,
                        chapter_title=title,
                        span_id=int(s.get("id", 0)),
                        span_type=stype,
                        baseline_speaker=speaker,
                        baseline_method=method,
                        baseline_confidence=conf,
                        text=str(s.get("text") or ""),
                        context_before=text[cbeg:start],
                        context_after=text[end:cend],
                        roster=roster if self.cfg.include_roster else [],
                        notes=str(notes) if notes else None,
                    )
                    cand.fingerprint = self._fingerprint(cand)
                    out.append(cand)

        return out

    def write_jsonl(self, path: Path, candidates: list[LLMCandidate]) -> None:
        """Write candidates to a JSONL file."""
        with path.open("w", encoding="utf-8") as f:
            for c in candidates:
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    # ------------------------------ Internals ------------------------------

    def _needs_llm(
        self,
        stype: str,
        speaker: str,
        method: str,
        conf: float,
        notes: Any,
    ) -> bool:
        if speaker == "Unknown":
            return True
        if conf < self.cfg.conf_threshold:
            return True
        if method in self.cfg.consider_methods:
            return True
        if notes == "quote_mismatch":
            return True
        return False

    @staticmethod
    def _fingerprint(c: LLMCandidate) -> str:
        """Create a stable key for caching LLM results."""
        h = hashlib.sha256()
        key = {
            "span_id": c.span_id,
            "text": c.text,
            "before": c.context_before[-280:],
            "after": c.context_after[:280],
            "roster": c.roster,
        }
        h.update(json.dumps(key, sort_keys=True).encode("utf-8"))
        return h.hexdigest()
