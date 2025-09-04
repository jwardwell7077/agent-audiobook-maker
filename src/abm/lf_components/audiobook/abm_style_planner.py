"""ABM Style Planner (Text-only, vendor-neutral).

Takes spans (spans, spans_cls, or spans_attr) and emits spans_style with a
 simple, deterministic StylePlan per span: rate/pitch/volume deltas, basic
 emotion labels, and pause hints derived from punctuation. No SSML, no audio.
 Optionally writes JSONL + meta.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, cast

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, FloatInput, Output, StrInput
from langflow.schema import Data

_PUNCT_PAUSES_MS = {
    ".": 280,
    "?": 280,
    "!": 300,
    ",": 120,
    ";": 180,
    ":": 200,
    "—": 160,
    "-": 140,
}


class ABMStylePlanner(Component):
    display_name = "ABM Style Planner"
    description = "Generate vendor-neutral StylePlan for spans (rate, emotion, pauses)"
    icon = "tuning"
    name = "ABMStylePlanner"

    inputs = [
        DataInput(
            name="spans_in",
            display_name="Spans (any stage)",
            info="Payload with spans_attr, spans_cls, or spans",
            required=True,
        ),
        FloatInput(
            name="base_rate",
            display_name="Base Rate",
            value=1.0,
            required=False,
        ),
        FloatInput(
            name="dialogue_rate_delta",
            display_name="Dialogue Rate Delta",
            value=0.05,
            required=False,
        ),
        FloatInput(
            name="narration_rate_delta",
            display_name="Narration Rate Delta",
            value=-0.03,
            required=False,
        ),
        BoolInput(
            name="emotion_from_punct",
            display_name="Derive Emotion from Punctuation",
            value=True,
            required=False,
        ),
        BoolInput(
            name="write_to_disk",
            display_name="Write JSONL + meta",
            value=False,
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Dir",
            value="",
            required=False,
        ),
        StrInput(
            name="version",
            display_name="Planner Version",
            value="1.0",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Styled Spans", name="spans_style", method="plan_styles"),
    ]

    def plan_styles(self) -> Data:
        payload = self._extract_payload()
        spans = payload.get("spans_attr") or payload.get("spans_cls") or payload.get("spans") or []
        if not isinstance(spans, list):
            return Data(data={"error": "Invalid spans payload"})

        out: list[dict[str, Any]] = []
        counts = {"dialogue": 0, "narration": 0}
        for s in spans:
            role = (s.get("type") or s.get("role") or "").lower()
            text = str(s.get("text_norm") or s.get("text") or "")

            base_rate = float(getattr(self, "base_rate", 1.0))
            if role == "dialogue":
                rate = base_rate + float(getattr(self, "dialogue_rate_delta", 0.05))
                counts["dialogue"] += 1
            else:
                rate = base_rate + float(getattr(self, "narration_rate_delta", -0.03))
                counts["narration"] += 1

            emotion = self._infer_emotion(text) if bool(getattr(self, "emotion_from_punct", True)) else "neutral"
            pauses = self._pauses_from_punct(text)

            style = {
                "rate": round(rate, 3),
                "pitch": 0.0,
                "volume": 0.0,
                "emotion": emotion,
                "pauses": pauses,
                "provenance": {"component": self.name, "version": getattr(self, "version", "1.0")},
            }

            out.append({**s, "style_plan": style})

        result = {"spans_style": out, "counts": counts}

        if bool(getattr(self, "write_to_disk", False)):
            self._write(out)

        self.status = f"Planned styles for {len(out)} spans"
        return Data(data=result)

    # --- helpers ---
    def _extract_payload(self) -> dict[str, Any]:
        src = getattr(self, "spans_in", None)
        if src is None:
            return {"error": "spans_in is required"}
        if hasattr(src, "data"):
            data = src.data
            return cast(dict[str, Any], data) if isinstance(data, dict) else {"error": "Invalid spans_in data"}
        if isinstance(src, dict):
            return src
        return {"error": "Invalid spans_in"}

    def _infer_emotion(self, text: str) -> str:
        t = text
        if "!" in t and "?" in t:
            return "surprised"
        if "!" in t:
            return "excited"
        if "?" in t:
            return "questioning"
        # mild heuristic for ellipsis/thoughtful
        if "…" in t or "..." in t:
            return "thoughtful"
        return "neutral"

    def _pauses_from_punct(self, text: str) -> list[dict[str, Any]]:
        pauses: list[dict[str, Any]] = []
        for m in re.finditer(r"[\.!?,;:\-—]", text):
            ch = m.group(0)
            ms = _PUNCT_PAUSES_MS.get(ch, 0)
            if ms <= 0:
                continue
            pauses.append({"pos": m.start(), "ms": ms, "type": "punct", "char": ch})
        return pauses

    def _write(self, spans_style: list[dict[str, Any]]) -> None:
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir and spans_style:
            s0 = spans_style[0]
            book_id = s0.get("book_id", "UNKNOWN_BOOK")
            chnum = int(s0.get("chapter_number", (s0.get("chapter_index") or 0) + 1))
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")
        if not outdir:
            return
        Path(outdir).mkdir(parents=True, exist_ok=True)
        p = Path(outdir) / "spans_style.jsonl"
        meta_p = Path(outdir) / "spans_style.meta.json"
        with p.open("w", encoding="utf-8") as f:
            for rec in spans_style:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        meta = {"component": self.name, "version": getattr(self, "version", "1.0"), "count": len(spans_style)}
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
