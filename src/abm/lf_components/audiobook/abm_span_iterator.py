"""ABM Span Iterator (LangFlow Component).

Iterates spans produced by the Mixed-Block Resolver. Supports start/max windowing
and optional loading from a spans.jsonl file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, IntInput, Output, StrInput
from langflow.schema import Data


class ABMSpanIterator(Component):
    display_name = "ABM Span Iterator"
    description = "Iterate spans (dialogue/narration) with simple windowing"
    icon = "repeat"
    name = "ABMSpanIterator"

    inputs = [
        DataInput(
            name="spans_data",
            display_name="Spans Data",
            info="Payload with spans|spans_cls|spans_attr|spans_style",
            required=False,
        ),
        StrInput(
            name="spans_jsonl_path",
            display_name="Spans JSONL Path",
            info="Optional path to spans.jsonl; used if spans_data is not provided",
            value="",
            required=False,
        ),
        IntInput(
            name="start_span",
            display_name="Start index (0-based)",
            value=0,
            required=False,
        ),
        IntInput(
            name="max_spans",
            display_name="Max spans to iterate (0 = all)",
            value=0,
            required=False,
        ),
        BoolInput(
            name="dialogue_only",
            display_name="Dialogue only",
            value=False,
            required=False,
        ),
        IntInput(
            name="min_confidence_pct",
            display_name="Min confidence % (dialogue)",
            info="If set (>0), filter dialogue spans with attribution.confidence below this percentage",
            value=0,
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Current Span", name="current_span", method="get_next_span"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._i = 0
        self._processed: list[str] = []

        try:
            self.start_span = int(getattr(self, "start_span", 0) or 0)
        except Exception:
            self.start_span = 0
        try:
            self.max_spans = int(getattr(self, "max_spans", 0) or 0)
        except Exception:
            self.max_spans = 0

    def _load_spans(self) -> list[dict[str, Any]]:
        # Prefer spans_data
        src = getattr(self, "spans_data", None)
        spans: list[dict[str, Any]] = []
        if src is not None:
            if hasattr(src, "data"):
                data = src.data
                payload = cast(dict[str, Any], data) if isinstance(data, dict) else {}
            elif isinstance(src, dict):
                payload = src
            else:
                raise TypeError("spans_data must be a Data or dict payload")
            # Accept spans from any upstream stage including Style Planner
            spans = (
                payload.get("spans")
                or payload.get("spans_cls")
                or payload.get("spans_attr")
                or payload.get("spans_style")
                or []
            )
        else:
            # Fallback: JSONL path
            p = (getattr(self, "spans_jsonl_path", "") or "").strip()
            if not p:
                raise TypeError("No spans_data or spans_jsonl_path provided")
            path = Path(p)
            if not path.exists():
                raise FileNotFoundError(f"spans_jsonl_path not found: {p}")
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    spans.append(json.loads(line))

        # Filter dialogue only if requested
        dialogue_only = bool(getattr(self, "dialogue_only", False))
        if dialogue_only:
            spans = [s for s in spans if (s.get("role") == "dialogue" or s.get("type") == "dialogue")]

        # Optional confidence threshold for dialogue
        try:
            min_pct = int(getattr(self, "min_confidence_pct", 0) or 0)
        except Exception:
            min_pct = 0
        if min_pct > 0:
            thr = float(min_pct) / 100.0

            def _passes_conf(s: dict[str, Any]) -> bool:
                if s.get("role") == "dialogue" or s.get("type") == "dialogue":
                    attr = s.get("attribution") or {}
                    c = attr.get("confidence")
                    try:
                        return c is not None and float(c) >= thr
                    except Exception:
                        return False  # drop if malformed
                return True  # non-dialogue unaffected

            spans = [s for s in spans if _passes_conf(s)]

        # Apply start and max
        start = max(0, int(getattr(self, "start_span", 0) or 0))
        if start:
            spans = [s for i, s in enumerate(spans) if i >= start]
        maxn = int(getattr(self, "max_spans", 0) or 0)
        if maxn > 0:
            spans = spans[:maxn]
        return spans

    def get_next_span(self) -> Data:
        try:
            spans = self._load_spans()
            if not spans:
                self.status = "No spans to process"
                return Data(data={"error": "No spans available"})

            if self._i >= len(spans):
                return self._summary(spans)

            cur = spans[self._i]
            self._i += 1
            sid = str(cur.get("span_uid") or f"{cur.get('block_id')}:{cur.get('segment_id')}")
            self._processed.append(sid)
            self.status = f"Span {self._i}/{len(spans)} - {cur.get('role') or cur.get('type')}"

            # Pass-through data
            out = {
                "span": cur,
                "ids": {
                    "book_id": cur.get("book_id"),
                    "chapter_index": cur.get("chapter_index"),
                    "block_id": cur.get("block_id"),
                    "segment_id": cur.get("segment_id"),
                    "span_uid": cur.get("span_uid"),
                },
                "meta": {
                    "source_component": "ABMSpanIterator",
                },
            }
            return Data(data=out)
        except Exception as e:  # noqa: BLE001
            self.status = f"Error: {e}"
            return Data(data={"error": str(e)})

    def _summary(self, spans: list[dict[str, Any]]) -> Data:
        data = {
            "processing_status": "completed",
            "total_spans_processed": len(self._processed),
            "processed_span_uids": self._processed,
        }
        # reset for next run
        self._i = 0
        self._processed = []
        self.status = f"Completed {len(spans)} spans"
        return Data(data=data)
