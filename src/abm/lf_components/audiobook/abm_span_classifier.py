"""ABM Span-level Classifier (LangFlow Component).

Classifies spans into dialogue/narration/mixed deterministically with simple rules.
Emits spans_cls records and meta; optionally writes JSONL + meta to disk.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data


@dataclass
class _ClsResult:
    spans_cls: list[dict[str, Any]]
    meta: dict[str, Any]


class ABMSpanClassifier(Component):
    display_name = "ABM Span Classifier"
    description = "Classify spans (dialogue/narration/mixed) deterministically; produce spans_cls records"
    icon = "check-square"
    name = "ABMSpanClassifier"

    inputs = [
        DataInput(
            name="spans",
            display_name="Spans",
            info="Data payload from ABMMixedBlockResolver.spans (contains spans)",
            required=True,
        ),
        BoolInput(
            name="use_role_hint",
            display_name="Use role hint if present",
            value=True,
            required=False,
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
            display_name="Classifier Version",
            value="1.0",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Classified Spans", name="spans_cls", method="classify_spans"),
        Output(display_name="Classifier Meta", name="spans_cls_meta", method="get_meta"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last: _ClsResult | None = None

    def classify_spans(self) -> Data:
        res = self._ensure_classified()
        if bool(getattr(self, "write_to_disk", False)):
            self._write_artifacts(res)
        return Data(data={"spans_cls": res.spans_cls})

    def get_meta(self) -> Data:
        res = self._ensure_classified()
        return Data(data=res.meta)

    # Internal
    def _ensure_classified(self) -> _ClsResult:
        if self._last is not None:
            return self._last
        src = getattr(self, "spans", None)
        if src is None:
            raise TypeError("spans input is required")
        if hasattr(src, "data"):
            payload = src.data  # type: ignore[attr-defined]
        elif isinstance(src, dict):
            payload = src
        else:
            raise TypeError("spans must be a Data or dict payload")

        spans = payload.get("spans") or []
        if not isinstance(spans, list):
            raise TypeError("spans.data['spans'] must be a list")

        use_hint = bool(getattr(self, "use_role_hint", True))
        spans_out: list[dict[str, Any]] = []
        errors: list[str] = []
        c_dialogue = 0
        c_narration = 0
        c_mixed = 0

        for i, s in enumerate(spans):
            try:
                text = s.get("text_norm") or s.get("text_raw") or ""
                role_hint = s.get("role")
                # Simple deterministic rules
                if use_hint and role_hint in {"dialogue", "narration"}:
                    label = role_hint
                else:
                    # Fallback: quote-wrapped string -> dialogue; else narration
                    t = str(text)
                    label = "dialogue" if (t.startswith('"') and t.endswith('"')) else "narration"

                features = {
                    "len_chars": len(text),
                    "len_words": len(str(text).split()),
                    "has_quotes": str(text).count('"') >= 2,
                }

                out = {
                    "span_uid": s.get("span_uid"),
                    "role": role_hint or label,
                    "type": label,
                    "text_norm": text,
                    "book_id": s.get("book_id"),
                    "chapter_index": s.get("chapter_index"),
                    "chapter_number": s.get("chapter_number"),
                    "block_id": s.get("block_id"),
                    "segment_id": s.get("segment_id"),
                    "features": features,
                    "provenance": {
                        "rules": "role_hint_if_available_else_quote_wrapped",
                        "version": getattr(self, "version", "1.0"),
                    },
                }
                spans_out.append(out)
                if label == "dialogue":
                    c_dialogue += 1
                elif label == "narration":
                    c_narration += 1
                else:
                    c_mixed += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"span {i}: {e}")

        meta = {
            "component": self.name,
            "version": getattr(self, "version", "1.0"),
            "dialogue": c_dialogue,
            "narration": c_narration,
            "mixed": c_mixed,
            "total": len(spans_out),
            "errors": errors,
            "valid": len(errors) == 0,
        }
        self._last = _ClsResult(spans_cls=spans_out, meta=meta)
        return self._last

    def _write_artifacts(self, res: _ClsResult) -> None:
        # Determine output dir from first span or fallback
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir:
            if res.spans_cls:
                s0 = res.spans_cls[0]
                book_id = s0.get("book_id", "UNKNOWN_BOOK")
                chnum = int(s0.get("chapter_number", 0))
            else:
                book_id = "UNKNOWN_BOOK"
                chnum = 0
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")
        Path(outdir).mkdir(parents=True, exist_ok=True)
        path = Path(outdir) / "spans_cls.jsonl"
        meta_path = Path(outdir) / "spans_cls.meta.json"
        with path.open("w", encoding="utf-8") as f:
            for rec in res.spans_cls:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(res.meta, f, ensure_ascii=False, indent=2)
