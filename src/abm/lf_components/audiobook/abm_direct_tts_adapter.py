"""ABM Direct TTS Adapter (LangFlow Component).

Plans or performs direct TTS synthesis per span without SSML, using voice
 configuration from the voice bank (attached to spans by ABMSpanCasting).

Default is dry-run (no audio calls) to generate a per-span render plan and a
 chapter manifest path. Real synthesis can be wired to local engines by
 implementing vendor-specific hooks (e.g., Parler, Bark, StyleTTS2, XTTS).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data


class ABMDirectTTSAdapter(Component):
    display_name = "ABM Direct TTS Adapter"
    description = "Plan or render per-span audio via local promptable engines (Parler/Bark/etc.)"
    icon = "volume-2"
    name = "ABMDirectTTSAdapter"

    inputs = [
        DataInput(
            name="spans_cast",
            display_name="Casted Spans",
            info="From ABMSpanCasting.spans_cast (voice.vendor/model/prompt fields)",
            required=True,
        ),
        BoolInput(
            name="dry_run",
            display_name="Dry Run (no synthesis)",
            value=True,
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            info="If empty, inferred as output/{book_id}/ch{NN}/audio",
            value="",
            required=False,
        ),
        StrInput(
            name="vendor_override",
            display_name="Vendor Override (optional)",
            value="",
            required=False,
        ),
        StrInput(
            name="parler_server",
            display_name="Parler Server URL (optional)",
            value="http://localhost:8000",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Render Plan", name="render_plan", method="plan_or_render"),
    ]

    def plan_or_render(self) -> Data:
        src = getattr(self, "spans_cast", None)
        payload = src.data if hasattr(src, "data") else src
        spans = (
            (payload.get("spans_cast") or payload.get("spans_attr") or payload.get("spans_cls") or [])
            if payload
            else []
        )
        if not isinstance(spans, list):
            self.status = "Error: invalid spans"
            return Data(data={"error": "invalid spans_cast payload"})

        # Infer output dir
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir and spans:
            s0 = spans[0]
            book_id = s0.get("book_id", "UNKNOWN_BOOK")
            chnum = int(s0.get("chapter_number", (s0.get("chapter_index") or 0) + 1))
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}", "audio")
        Path(outdir).mkdir(parents=True, exist_ok=True)

        vendor_override = (getattr(self, "vendor_override", "") or "").strip()
        dry_run = bool(getattr(self, "dry_run", True))

        plan: list[dict[str, Any]] = []
        for s in spans:
            text = s.get("text_norm") or s.get("text") or ""
            vu = s.get("voice") or {}
            vendor = vendor_override or (vu.get("vendor") or "unknown")
            out_path = str(Path(outdir) / f"{s.get('span_uid', 'unknown')}.wav")
            entry = {
                "span_uid": s.get("span_uid"),
                "vendor": vendor,
                "text": text,
                "voice": vu,
                "out_path": out_path,
            }
            # Dry-run: just collect plan. Future: call engines by vendor.
            plan.append(entry)

        # Write a manifest in the chapter folder
        manifest_path = Path(outdir).parent / "audio_manifest.jsonl"
        with manifest_path.open("w", encoding="utf-8") as f:
            for p in plan:
                f.write(json.dumps({"span_uid": p["span_uid"], "audio": p["out_path"]}, ensure_ascii=False) + "\n")

        self.status = f"Planned {len(plan)} renders (dry_run={dry_run})"
        return Data(data={"dry_run": dry_run, "plan": plan, "manifest": str(manifest_path), "audio_dir": outdir})
