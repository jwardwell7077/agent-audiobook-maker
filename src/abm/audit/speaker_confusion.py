"""Compute speaker confusion between base and refined documents."""

from __future__ import annotations

import logging
from collections import Counter

from abm.audit.schemas import ConfusionSummary

logger = logging.getLogger(__name__)


def compute_confusion(base_doc: dict, refined_doc: dict) -> ConfusionSummary:
    base_chapters = base_doc.get("chapters", []) or []
    ref_chapters = refined_doc.get("chapters", []) or []
    counter: Counter[tuple[str, str]] = Counter()
    total = 0
    changes = 0

    for idx, rch in enumerate(ref_chapters):
        title = rch.get("title")
        candidates = [bch for bch in base_chapters if bch.get("title") == title]
        bch = None
        if len(candidates) == 1:
            bch = candidates[0]
        elif len(candidates) > 1 and rch.get("id") is not None:
            matches = [b for b in candidates if b.get("id") == rch.get("id")]
            if len(matches) == 1:
                bch = matches[0]
        if bch is None:
            if idx < len(base_chapters):
                bch = base_chapters[idx]
                logger.warning("chapter alignment fallback by index %s", idx)
            else:
                logger.warning("base chapter missing for '%s'", title)
                continue
        for bs, rs in zip(bch.get("spans", []) or [], rch.get("spans", []) or [], strict=False):
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
        "top_pairs": [{"from_speaker": a, "to_speaker": b, "count": c} for (a, b), c in counter.most_common()],
    }
    return summary
