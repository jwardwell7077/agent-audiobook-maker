from __future__ import annotations

from typing import Any, Dict, List


def simple_segment(text: str) -> List[Dict[str, str]]:
    """Split body text into utterances using a quote/line heuristic.

    - Split into lines; accumulate until a blank line.
        - If any line contains a double quote, mark chunk as dialogue,
            else narration.
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
