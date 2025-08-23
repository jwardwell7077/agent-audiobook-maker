from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class Utterance:
    role: str  # "narration" | "dialogue"
    text: str
    chapter_index: int
    chapter_title: str


def simple_segment(text: str) -> List[Dict[str, str]]:
    """Split body text into utterances using a basic quote/line heuristic.

    Rules (deterministic, no ML):
    - Split into lines; keep contiguous lines together until a blank line.
        - Lines with any ASCII double quote (") tagged as dialogue; else
            narration.
    - Trim whitespace and ignore empty chunks.
    """
    utterances: List[Dict[str, str]] = []
    buf: List[str] = []
    buf_has_quote = False

    def flush() -> None:
        nonlocal buf, buf_has_quote
        if not buf:
            return
        chunk = "\n".join(buf).strip()
        if chunk:
            utterances.append({
                "role": "dialogue" if buf_has_quote else "narration",
                "text": chunk,
            })
        buf = []
        buf_has_quote = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            flush()
            continue
        buf.append(line)
        if '"' in line:
            buf_has_quote = True
    flush()
    return utterances


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """LangFlow-compatible entry.

    Input payload: {"book": str, "chapters": [{index,title,body_text}]}
        Output: {"book": str, "utterances":
            [{role,text,chapter_index,chapter_title}]}
    """
    book = payload.get("book", "")
    chapters = payload.get("chapters", [])
    out: List[Dict[str, Any]] = []
    for ch in chapters:
        ch_idx = int(ch.get("index", 0))
        ch_title = str(ch.get("title", ""))
        body = str(ch.get("body_text", ""))
        for u in simple_segment(body):
            out.append({
                "role": u["role"],
                "text": u["text"],
                "chapter_index": ch_idx,
                "chapter_title": ch_title,
            })
    return {"book": book, "utterances": out}
