"""LangGraph annotation pipeline skeleton.

Stages (placeholders):
1. segment -> split raw text into segments
2. coref -> dummy coreference resolution
3. speakers -> assign speaker labels heuristically
4. emotion -> add mock emotion scores
5. qa -> produce simple quality / summary note

Each node performs pure functional update on the shared state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph


class Configuration(TypedDict, total=False):
    """Runtime toggle configuration for the annotation graph."""

    enable_coref: bool
    enable_emotion: bool
    enable_qa: bool
    max_segments: int  # cap segments for quick tests


@dataclass
class Segment:
    """Single textual segment (utterance) with optional speaker/emotion."""

    id: str
    text: str
    speaker: str | None = None
    emotion: str | None = None
    emotion_conf: float | None = None


@dataclass
class State:
    """Mutable graph state passed between nodes."""

    text: str = ""  # Raw input text to process
    enable_coref: bool = True
    enable_emotion: bool = True
    enable_qa: bool = True
    max_segments: int = 50
    segments: list[Segment] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --- Node implementations -------------------------------------------------


async def segment(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Split raw text into initial segments (idempotent)."""
    max_segments = state.max_segments
    if state.segments:  # idempotent
        return {}
    chunks: list[Segment] = []
    # naive split by blank line fallback to sentence-ish split
    raw_parts = [p.strip() for p in state.text.split("\n\n") if p.strip()]
    if len(raw_parts) == 0:
        raw_parts = [s.strip() for s in state.text.split(". ") if s.strip()]
    for idx, part in enumerate(raw_parts[:max_segments]):
        seg = Segment(id=f"seg-{idx}", text=part)
        chunks.append(seg)
    return {"segments": chunks}


async def coref(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Add coreference note if simple pronoun heuristic detects usage."""
    if not state.enable_coref:
        return {}
    pronouns = [w for w in ["he", "she", "they"] if f" {w} " in state.text.lower()]
    if pronouns:
        return {"notes": state.notes + [f"coref: pronouns {pronouns} detected"]}
    return {}


async def speakers(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Assign alternating speaker labels (A/B) as placeholder."""
    if not state.segments or state.segments[0].speaker is not None:
        return {}
    updated: list[Segment] = []
    for i, seg in enumerate(state.segments):
        speaker = "A" if i % 2 == 0 else "B"
        updated.append(
            Segment(
                id=seg.id,
                text=seg.text,
                speaker=speaker,
                emotion=seg.emotion,
                emotion_conf=seg.emotion_conf,
            )
        )
    return {"segments": updated}


async def emotion(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Annotate segments with simple alternating emotion labels."""
    if not state.enable_emotion:
        # ensure we clear any prior emotion if segments existed
        if any(seg.emotion for seg in state.segments):
            cleared = [
                Segment(
                    id=s.id,
                    text=s.text,
                    speaker=s.speaker,
                    emotion=None,
                    emotion_conf=None,
                )
                for s in state.segments
            ]
            return {"segments": cleared}
        return {}
    if not state.segments:
        return {}
    # assign neutral / excited alternately
    updated: list[Segment] = []
    for i, seg in enumerate(state.segments):
        emo = "excited" if i % 5 == 0 else "neutral"
        conf = 0.9 if emo == "excited" else 0.6
        updated.append(
            Segment(
                id=seg.id,
                text=seg.text,
                speaker=seg.speaker,
                emotion=emo,
                emotion_conf=conf,
            )
        )
    return {"segments": updated}


async def qa(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Add simple QA summary note about segment and character counts."""
    if not state.enable_qa:
        return {}
    if not state.segments:
        return {}
    total_chars = sum(len(s.text) for s in state.segments)
    note = f"qa: {len(state.segments)} segs, {total_chars} chars"
    if note not in state.notes:
        return {"notes": state.notes + [note]}
    return {}


# --- Graph assembly -------------------------------------------------------

graph = (
    StateGraph(State, context_schema=Configuration)
    .add_node("segment", segment)
    .add_node("coref", coref)
    .add_node("speakers", speakers)
    .add_node("emotion", emotion)
    .add_node("qa", qa)
    .add_edge("__start__", "segment")
    .add_edge("segment", "coref")
    .add_edge("coref", "speakers")
    .add_edge("speakers", "emotion")
    .add_edge("emotion", "qa")
    .add_edge("qa", "__end__")
    .compile(name="AnnotationGraph")
)

__all__ = ["graph", "State", "Segment"]
