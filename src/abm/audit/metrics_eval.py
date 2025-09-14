"""Basic statistics for annotation refinement results."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable
import json

from .schemas import Chapter, EvalSummary, Span, ChapterStat


def load_doc(path: Path) -> dict:
    """Load a JSON document from ``path``."""
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_spans(doc: dict) -> Iterable[tuple[str, Span]]:
    for ch in doc.get("chapters", []):
        title = str(ch.get("title", ""))
        for sp in ch.get("spans", []) or []:
            yield title, sp  # type: ignore[misc]


def compute_basic_metrics(refined: dict, base: dict | None, worst_n: int) -> EvalSummary:
    """Compute headline statistics for a refined annotation document."""

    counter: Counter[str] = Counter()
    chapter_rows: list[ChapterStat] = []
    total_spans = 0
    total_dt = 0
    unknown_count = 0

    # Per-chapter counts
    for ch in refined.get("chapters", []):
        spans = ch.get("spans", []) or []
        total_spans += len(spans)
        dt_spans = [s for s in spans if s.get("type") in ("Dialogue", "Thought")]
        dt_total = len(dt_spans)
        total_dt += dt_total
        unk = sum(1 for s in dt_spans if (s.get("speaker") in (None, "Unknown")))
        unknown_count += unk
        for s in dt_spans:
            spk = s.get("speaker") or "Unknown"
            if spk != "Unknown":
                counter[str(spk)] += 1
        rate = unk / dt_total if dt_total else 0.0
        chapter_rows.append(
            {
                "title": str(ch.get("title", "")),
                "total": dt_total,
                "unknown": unk,
                "unknown_rate": rate,
            }
        )

    chapter_rows.sort(key=lambda r: r["unknown_rate"], reverse=True)
    worst_chapters = chapter_rows[:worst_n]

    speaker_changes = 0
    speaker_changes_rate = 0.0
    if base:
        base_dt_total = 0
        for bch, rch in zip(base.get("chapters", []), refined.get("chapters", [])):
            b_spans = bch.get("spans", []) or []
            r_spans = rch.get("spans", []) or []
            for bs, rs in zip(b_spans, r_spans):
                if bs.get("type") not in ("Dialogue", "Thought"):
                    continue
                base_dt_total += 1
                if (bs.get("speaker") or "Unknown") != (rs.get("speaker") or "Unknown"):
                    speaker_changes += 1
        speaker_changes_rate = speaker_changes / base_dt_total if base_dt_total else 0.0

    summary: EvalSummary = {
        "total_spans": total_spans,
        "total_dialog_thought": total_dt,
        "unknown_count": unknown_count,
        "unknown_rate": unknown_count / total_dt if total_dt else 0.0,
        "top_speakers": counter.most_common(),
        "worst_chapters": worst_chapters,
        "speaker_changes": speaker_changes,
        "speaker_changes_rate": speaker_changes_rate,
        "generated_at": datetime.utcnow().isoformat(),
        "chapters": chapter_rows,
    }
    return summary
