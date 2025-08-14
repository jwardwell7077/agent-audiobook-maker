from __future__ import annotations
"""Casting derivation utilities.

Extract distinct speaker labels from annotation segments and create
character records (in-memory + DB persistence helper).
"""

from typing import Iterable, Any, List
from dataclasses import dataclass
from db import get_session, models


@dataclass
class CharacterRecord:
    book_id: str
    name: str
    id: str
    aliases: list[str]


def derive_characters(
    book_id: str,
    segments: Iterable[dict | Any],
) -> list[CharacterRecord]:
    names: set[str] = set()
    for seg in segments:
        speaker = getattr(seg, "speaker", None)
        if isinstance(seg, dict):
            speaker = seg.get("speaker")
        if not speaker:
            continue
        names.add(speaker)
    records: list[CharacterRecord] = []
    for name in sorted(names):
        char_id = f"{book_id}-char-{name.lower()}"
        records.append(
            CharacterRecord(
                book_id=book_id,
                name=name,
                id=char_id,
                aliases=[name],
            )
        )
    return records


def persist_characters(chars: List[CharacterRecord]) -> None:
    if not chars:
        return
    with get_session() as session:
        for c in chars:
            existing = session.get(models.Character, c.id)
            if existing:
                continue
            session.add(
                models.Character(
                    id=c.id,
                    book_id=c.book_id,
                    name=c.name,
                    aliases=c.aliases,
                    profile=None,
                )
            )


__all__ = ["derive_characters", "persist_characters", "CharacterRecord"]
