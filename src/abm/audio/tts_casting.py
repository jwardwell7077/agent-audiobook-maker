"""Simple speaker-to-profile casting helpers."""

from __future__ import annotations

from typing import Any

from abm.profiles.character_profiles import CharacterProfilesDB, Profile

__all__ = ["cast_speaker", "spans_to_tasks"]


def cast_speaker(
    speaker: str,
    db: CharacterProfilesDB,
    *,
    preferred_engine: str | None = None,
) -> dict[str, Any]:
    """Return casting info for ``speaker``.

    Args:
        speaker: Speaker name from the roster.
        db: Loaded :class:`CharacterProfilesDB`.
        preferred_engine: Engine to prefer when choosing fallbacks.

    Returns:
        Dictionary with keys ``engine``, ``voice``, ``profile_id``, ``refs`` and
        ``style``.
    """

    profile: Profile | None = db.by_speaker(speaker)
    lower = speaker.lower()
    if profile is None:
        for candidate in db.profiles.values():
            if any(tag.lower() in lower for tag in candidate.tags):
                profile = candidate
                break
    if profile is None and any(x in lower for x in {"narrator", "system", "ui"}):
        profile = db.fallback(preferred_engine or "piper")
    if profile is None and preferred_engine:
        profile = db.fallback(preferred_engine)
    if profile is None:
        # final fallback: any profile
        profile = next(iter(db.profiles.values()))
    return {
        "engine": profile.engine,
        "voice": profile.voice,
        "profile_id": profile.id,
        "refs": profile.refs,
        "style": profile.style,
    }


def _infer_pause(text: str, default_pause_ms: int) -> int:
    pause = default_pause_ms
    if text.endswith("\n\n"):
        pause += 100
    elif text.endswith(","):
        pause = max(40, default_pause_ms - 40)
    return pause


def spans_to_tasks(
    spans: list[dict[str, Any]],
    db: CharacterProfilesDB,
    *,
    default_engine: str = "piper",
    default_pause_ms: int = 120,
) -> list[dict[str, Any]]:
    """Convert annotated spans into synthesis tasks."""

    tasks: list[dict[str, Any]] = []
    for span in spans:
        if span.get("type") not in {"Dialogue", "Thought", "Narration"}:
            continue
        text = span.get("text", "")
        pause_ms = int(span.get("pause_ms") or _infer_pause(text, default_pause_ms))
        info = cast_speaker(
            span.get("speaker", ""), db, preferred_engine=default_engine
        )
        tasks.append(
            {
                "type": "span",
                "speaker": span.get("speaker"),
                "text": text,
                "pause_ms": pause_ms,
                "engine": info["engine"],
                "voice": info["voice"],
                "profile_id": info["profile_id"],
                "refs": info["refs"],
                "style": info["style"],
            }
        )
    return tasks
