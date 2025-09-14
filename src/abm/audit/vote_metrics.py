"""Parse metrics JSONL produced during refinement voting."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import TypedDict

from .schemas import VoteStats


def parse_metrics_jsonl(path: Path) -> VoteStats:
    """Parse a metrics JSONL file into aggregate statistics."""

    cache_hits = 0
    cache_misses = 0
    margins: list[float] = []
    weak_cases: list[dict] = []

    if not path.exists():
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_rate": 0.0,
            "vote_margins": [],
            "median_margin": None,
            "weak_cases": [],
        }

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("cache_hit"):
                cache_hits += 1
            else:
                cache_misses += 1
            votes: dict[str, int] = obj.get("votes", {}) or {}
            total = sum(votes.values())
            if total:
                top = max(votes.values())
                margin = top / total if total else 0.0
                margins.append(margin)
                if margin < 0.67:
                    winner = max(votes, key=votes.get)
                    weak_cases.append(
                        {
                            "chapter": obj.get("chapter"),
                            "title": obj.get("title"),
                            "span_index": obj.get("span_index"),
                            "margin": margin,
                            "winner": winner,
                            "candidates": votes,
                        }
                    )
    total_events = cache_hits + cache_misses
    stats: VoteStats = {
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_rate": cache_hits / total_events if total_events else 0.0,
        "vote_margins": margins,
        "median_margin": median(margins) if margins else None,
        "weak_cases": weak_cases,
    }
    return stats
