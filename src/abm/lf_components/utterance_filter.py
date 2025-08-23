from __future__ import annotations

from typing import Any, Dict, List, Optional


def run(
    payload: Dict[str, Any],
    role: Optional[str] = None,
    min_len: Optional[int] = None,
    max_len: Optional[int] = None,
    contains: Optional[str] = None,
) -> Dict[str, Any]:
    """Filter utterances by simple criteria.

    Input: {"book": str, "utterances": [{role,text,...}]}
    Params: role in {"dialogue","narration"}, length bounds, substring match
    Returns: same shape with filtered utterances.
    """
    book = payload.get("book", "")
    utterances: List[Dict[str, Any]] = list(payload.get("utterances", []))
    out: List[Dict[str, Any]] = []
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
