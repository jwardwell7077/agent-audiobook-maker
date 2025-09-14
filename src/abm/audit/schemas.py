"""Typed structures for the :mod:`abm.audit` package."""

from __future__ import annotations

from typing import TypedDict


class Span(TypedDict, total=False):
    type: str  # "Dialogue" | "Thought" | "Narration"
    speaker: str | None
    text: str


class Chapter(TypedDict, total=False):
    title: str
    id: str | int | None
    spans: list[Span]


class ChapterStat(TypedDict):
    title: str
    total: int
    unknown: int
    unknown_rate: float


class EvalSummary(TypedDict, total=False):
    total_spans: int
    total_dialog_thought: int
    unknown_count: int
    unknown_rate: float
    top_speakers: list[tuple[str, int]]
    worst_chapters: list[ChapterStat]
    speaker_changes: int
    speaker_changes_rate: float
    generated_at: str
    chapters: list[ChapterStat]


class VoteStats(TypedDict, total=False):
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    vote_margins: list[float]
    median_margin: float | None
    weak_cases: list[dict]


class ConfusionPair(TypedDict):
    from_speaker: str
    to_speaker: str
    count: int


class ConfusionSummary(TypedDict):
    total_compared: int
    changes: int
    top_pairs: list[ConfusionPair]
