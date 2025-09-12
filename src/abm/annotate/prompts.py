"""Prompt helpers for LLM speaker attribution."""

from __future__ import annotations

SYSTEM_SPEAKER = (
    "You are a careful literary annotator. "
    "Given a dialogue or thought span and its local context, "
    "identify the most likely SPEAKER strictly from the provided ROSTER. "
    "If it cannot be determined, respond 'Unknown'. "
    "Return strict JSON with keys: speaker (string), confidence (0..1)."
)


def speaker_user_prompt(
    roster: dict[str, list[str]],
    left: str,
    mid: str,
    right: str,
    span_type: str,
) -> str:
    """Build a user prompt constraining speaker choices to a roster.

    Args:
        roster: Mapping of speaker names to aliases.
        left: Context text immediately preceding the span.
        mid: The span text to attribute.
        right: Context text following the span.
        span_type: Either ``"Dialogue"`` or ``"Thought"``.

    Returns:
        str: A formatted prompt ready to send to the LLM.

    Raises:
        None
    """

    roster_flat = sorted(roster.keys()) if roster else []
    roster_str = ", ".join(roster_flat) if roster_flat else "[]"
    return (
        f"ROSTER: {roster_str}\n"
        f"SPAN_TYPE: {span_type}\n"
        f"LEFT: {left}\n"
        f"SPAN: {mid}\n"
        f"RIGHT: {right}\n\n"
        "Choose the SPEAKER from ROSTER or 'Unknown'. "
        'Return JSON: {"speaker": <string>, "confidence": <0..1>}.'
    )
