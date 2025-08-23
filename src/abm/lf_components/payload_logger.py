from __future__ import annotations

import json
from typing import Any, Dict, Optional


def _shorten(value: Any, max_chars: int) -> Any:
    s = str(value)
    return s if len(s) <= max_chars else s[: max_chars - 1] + "\u2026"


def run(
    payload: Dict[str, Any],
    preview_key: Optional[str] = None,
    max_chars: int = 200,
    echo: bool = False,
) -> Dict[str, Any]:
    """Log a compact preview of the payload and pass it through.

    Returns the original payload plus a string field "log" for debugging.
    """
    preview = None
    if preview_key and preview_key in payload:
        preview = _shorten(payload[preview_key], max_chars)
    meta = {
        "book": payload.get("book"),
        "keys": sorted(list(payload.keys())),
        "preview_key": preview_key,
        "preview_value": preview,
    }
    log_str = json.dumps(meta, ensure_ascii=False)
    if echo:
        print(log_str)  # deterministic side-effect allowed for dev use
    out = dict(payload)
    out["log"] = log_str
    return out
