"""Compute speaker confusion between base and refined documents."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Tuple

from .schemas import ConfusionPair, ConfusionSummary


def _chapter_key(ch: dict) -> str:
    return str(ch.get("title") or ch.get("id") or "")


def compute_confusion(base_doc: dict, refined_doc: dict) -> ConfusionSummary:
    base_map = { _chapter_key(ch): ch for ch in base_doc.get("chapters", []) }
    ref_map = { _chapter_key(ch): ch for ch in refined_doc.get("chapters", []) }
    counter: Counter[Tuple[str, str]] = Counter()
    total = 0
    changes = 0

    for key, bch in base_map.items():
        rch = ref_map.get(key)
        if not rch:
            continue
        for bs, rs in zip(bch.get("spans", []) or [], rch.get("spans", []) or []):
            if bs.get("type") not in ("Dialogue", "Thought"):
                continue
            total += 1
            bsp = str(bs.get("speaker") or "Unknown")
            rsp = str(rs.get("speaker") or "Unknown")
            if bsp != rsp:
                changes += 1
                counter[(bsp, rsp)] += 1
    summary: ConfusionSummary = {
        "total_compared": total,
        "changes": changes,
        "top_pairs": [
            {"from_speaker": a, "to_speaker": b, "count": c}
            for (a, b), c in counter.most_common()
        ],
    }
    return summary
