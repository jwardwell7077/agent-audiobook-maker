from __future__ import annotations

from typing import Any, Dict, List, Optional


def run(
    payload: Dict[str, Any],
    index: Optional[int] = None,
    title_contains: Optional[str] = None,
) -> Dict[str, Any]:
    """Select a single chapter from a chapters payload.

    Input: {"book": str, "chapters": [{index,title,body_text}]}
    Params:
      - index: exact chapter index to select
      - title_contains: match if substring (case-insensitive) is in title
    Returns: {"book": str, "chapters": [one_chapter]}
    """
    book = payload.get("book", "")
    chapters: List[Dict[str, Any]] = list(payload.get("chapters", []))
    if not chapters:
        raise ValueError("No chapters provided in payload")

    selected: Optional[Dict[str, Any]] = None
    if index is not None:
        for ch in chapters:
            if int(ch.get("index", -1)) == int(index):
                selected = ch
                break
    elif title_contains:
        needle = title_contains.lower()
        for ch in chapters:
            title = str(ch.get("title", ""))
            if needle in title.lower():
                selected = ch
                break
    else:
        # default to first chapter deterministically
        selected = chapters[0]

    if selected is None:
        raise ValueError("Chapter not found with given selector")

    return {"book": book, "chapters": [selected]}
