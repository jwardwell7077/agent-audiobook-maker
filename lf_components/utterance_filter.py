from __future__ import annotations

from typing import Any


def run(
    payload: dict[str, Any],
    role: str | None = None,
    min_len: int | None = None,
    max_len: int | None = None,
    contains: str | None = None,
) -> dict[str, Any]:
    book = payload.get("book", "")
    utterances: list[dict[str, Any]] = list(payload.get("utterances", []))
    out: list[dict[str, Any]] = []
    rnorm = role.lower() if role else None
    needle = contains.lower() if contains else None
    for u in utterances:
        text = str(u.get("text", ""))
        if rnorm and str(u.get("role", "")).lower() != rnorm:
            continue
        if min_len is not None and len(text) < int(min_len):
            continue
        if max_len is not None and len(text) > int(max_len):
            continue
        if needle and needle not in text.lower():
            continue
        out.append(u)
    return {"book": book, "utterances": out}
