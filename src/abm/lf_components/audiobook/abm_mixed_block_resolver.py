"""ABM Mixed-Block Resolver (LangFlow Component).

Splits normalized blocks into ordered spans (dialogue/narration) by quote boundaries.
Assigns 0-based segment_id within each block and computes deterministic span_uid.
Optionally writes spans.jsonl + spans.meta.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data

_QUOTE_RE = re.compile(r'"[^"\n]*"')  # match double-quoted segments without newlines
_WS_RE = re.compile(r"\s+")


def _norm_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    s = s.strip()
    s = _WS_RE.sub(" ", s)
    return s


def _sha1(parts: Iterable[str]) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


@dataclass
class _SpanResult:
    spans: list[dict[str, Any]]
    meta: dict[str, Any]


class ABMMixedBlockResolver(Component):
    display_name = "ABM Mixed-Block Resolver"
    description = "Split blocks into dialogue/narration spans and compute deterministic span_uids"
    icon = "split"
    name = "ABMMixedBlockResolver"

    inputs = [
        DataInput(
            name="validated_blocks",
            display_name="Validated Blocks",
            info="Data payload from ABMBlockSchemaValidator.validated_blocks (contains blocks)",
            required=True,
        ),
        BoolInput(
            name="write_to_disk",
            display_name="Write JSONL + meta to disk",
            value=False,
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            info="If empty, defaults to output/{book_id}/ch{chapter_number:02d}",
            value="",
            required=False,
        ),
        StrInput(
            name="version",
            display_name="Resolver Version",
            value="1.0",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Spans", name="spans", method="resolve_spans"),
        Output(display_name="Spans Meta", name="spans_meta", method="get_meta"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last: _SpanResult | None = None

    def resolve_spans(self) -> Data:
        res = self._ensure_resolved()
        if bool(getattr(self, "write_to_disk", False)):
            self._write_artifacts(res)
        return Data(data={"spans": res.spans})

    def get_meta(self) -> Data:
        res = self._ensure_resolved()
        return Data(data=res.meta)

    # Internal
    def _ensure_resolved(self) -> _SpanResult:
        if self._last is not None:
            return self._last
        src = getattr(self, "validated_blocks", None)
        if src is None:
            raise TypeError("validated_blocks input is required")
        if hasattr(src, "data"):
            payload = src.data  # type: ignore[attr-defined]
        elif isinstance(src, dict):
            payload = src
        else:
            raise TypeError("validated_blocks must be a Data or dict payload")

        blocks = payload.get("blocks") or []
        if not isinstance(blocks, list):
            raise TypeError("validated_blocks.data['blocks'] must be a list")

        spans: list[dict[str, Any]] = []
        errors: list[str] = []
        count_dialogue = 0
        count_narration = 0

        for blk in blocks:
            try:
                book_id = blk.get("book_id")
                chapter_index = int(blk.get("chapter_index") or 0)
                chapter_number = int(blk.get("chapter_number") or (chapter_index + 1))
                block_id = int(blk.get("block_id") or 0)
                block_uid = blk.get("block_uid") or ""
                text_norm = _norm_text(blk.get("text_norm") or blk.get("text_raw") or "")
                role_hint = blk.get("role")

                # If no quotes, keep whole block as one span, using role_hint if available
                if not _QUOTE_RE.search(text_norm):
                    role = role_hint or (
                        "dialogue" if text_norm.startswith('"') and text_norm.endswith('"') else "narration"
                    )
                    span_uid = _sha1([str(block_uid), str(0), text_norm.lower()])
                    spans.append(
                        {
                            "book_id": book_id,
                            "chapter_index": chapter_index,
                            "chapter_number": chapter_number,
                            "block_id": block_id,
                            "segment_id": 0,
                            "role": role,
                            "text_norm": text_norm,
                            "span_uid": span_uid,
                            "block_uid": block_uid,
                        }
                    )
                    if role == "dialogue":
                        count_dialogue += 1
                    else:
                        count_narration += 1
                    continue

                # Split by quotes into narration/dialogue spans
                seg_id = 0
                pos = 0
                for m in _QUOTE_RE.finditer(text_norm):
                    start, end = m.span()
                    if start > pos:
                        narr = _norm_text(text_norm[pos:start])
                        if narr:
                            span_uid = _sha1([str(block_uid), str(seg_id), narr.lower()])
                            spans.append(
                                {
                                    "book_id": book_id,
                                    "chapter_index": chapter_index,
                                    "chapter_number": chapter_number,
                                    "block_id": block_id,
                                    "segment_id": seg_id,
                                    "role": "narration",
                                    "text_norm": narr,
                                    "span_uid": span_uid,
                                    "block_uid": block_uid,
                                }
                            )
                            seg_id += 1
                            count_narration += 1
                    quoted = _norm_text(text_norm[start:end])
                    if quoted:
                        span_uid = _sha1([str(block_uid), str(seg_id), quoted.lower()])
                        spans.append(
                            {
                                "book_id": book_id,
                                "chapter_index": chapter_index,
                                "chapter_number": chapter_number,
                                "block_id": block_id,
                                "segment_id": seg_id,
                                "role": "dialogue",
                                "text_norm": quoted,
                                "span_uid": span_uid,
                                "block_uid": block_uid,
                            }
                        )
                        seg_id += 1
                        count_dialogue += 1
                    pos = end
                if pos < len(text_norm):
                    tail = _norm_text(text_norm[pos:])
                    if tail:
                        span_uid = _sha1([str(block_uid), str(seg_id), tail.lower()])
                        spans.append(
                            {
                                "book_id": book_id,
                                "chapter_index": chapter_index,
                                "chapter_number": chapter_number,
                                "block_id": block_id,
                                "segment_id": seg_id,
                                "role": "narration",
                                "text_norm": tail,
                                "span_uid": span_uid,
                                "block_uid": block_uid,
                            }
                        )
                        seg_id += 1
                        count_narration += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"block {blk.get('block_id')}: {e}")

        meta = {
            "component": self.name,
            "version": getattr(self, "version", "1.0"),
            "total_spans": len(spans),
            "dialogue_spans": count_dialogue,
            "narration_spans": count_narration,
            "errors": errors,
            "valid": len(errors) == 0,
        }
        self._last = _SpanResult(spans=spans, meta=meta)
        return self._last

    def _write_artifacts(self, res: _SpanResult) -> None:
        # Determine output dir from first span or fallback
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir:
            # Try to infer book/chapter from first span
            if res.spans:
                s0 = res.spans[0]
                book_id = s0.get("book_id", "UNKNOWN_BOOK")
                chnum = int(s0.get("chapter_number", 0))
            else:
                book_id = "UNKNOWN_BOOK"
                chnum = 0
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")
        Path(outdir).mkdir(parents=True, exist_ok=True)
        spans_path = Path(outdir) / "spans.jsonl"
        meta_path = Path(outdir) / "spans.meta.json"
        with spans_path.open("w", encoding="utf-8") as f:
            for rec in res.spans:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(res.meta, f, ensure_ascii=False, indent=2)
