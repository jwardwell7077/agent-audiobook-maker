"""ABM Artifact Orchestrator (LangFlow Component).

Materialize pre-SSML artifacts stepwise:
 blocks.jsonl → spans.jsonl → spans_cls.jsonl → spans_attr.jsonl

Uses the existing components in-process and returns a summary with optional
 output paths. Intended for convenience in flows or scripts.
"""

from __future__ import annotations

import os

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data

from abm.lf_components.audiobook.abm_block_schema_validator import ABMBlockSchemaValidator
from abm.lf_components.audiobook.abm_mixed_block_resolver import ABMMixedBlockResolver
from abm.lf_components.audiobook.abm_span_attribution import ABMSpanAttribution
from abm.lf_components.audiobook.abm_span_classifier import ABMSpanClassifier
from abm.lf_components.audiobook.abm_style_planner import ABMStylePlanner


class ABMArtifactOrchestrator(Component):
    display_name = "ABM Artifact Orchestrator"
    description = "Run validator → resolver → classifier → attribution and write JSONL/meta"
    icon = "layers"
    name = "ABMArtifactOrchestrator"

    inputs = [
        DataInput(
            name="blocks_data",
            display_name="Blocks Data",
            info="From ABMChapterLoader.blocks_data",
            required=True,
        ),
        BoolInput(
            name="write_to_disk",
            display_name="Write Artifacts to Disk",
            value=True,
            required=False,
        ),
        BoolInput(
            name="enable_style_planner",
            display_name="Emit spans_style (Style Planner)",
            value=False,
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory (optional)",
            info="If empty, inferred as output/{book_id}/ch{NN}",
            value="",
            required=False,
        ),
        StrInput(
            name="min_confidence_pct",
            display_name="Min confidence % (dialogue)",
            info="If set (>0), filter dialogue spans_attr whose attribution.confidence is below this percentage",
            value="0",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Artifact Summary", name="artifact_summary", method="generate_artifacts"),
    ]

    def generate_artifacts(self) -> Data:
        src = getattr(self, "blocks_data", None)
        payload = None
        if src is None:
            return Data(data={"error": "blocks_data input is required"})
        if hasattr(src, "data"):
            payload = src.data  # type: ignore[attr-defined]
        elif isinstance(src, dict):
            payload = src
        if not isinstance(payload, dict):
            return Data(data={"error": "Invalid blocks_data input"})

        write = bool(getattr(self, "write_to_disk", True))
        outdir = (getattr(self, "output_dir", "") or "").strip()

        # 1) Validate blocks
        v = ABMBlockSchemaValidator(
            blocks_data=payload,
            write_to_disk=write,
            output_dir=outdir,
        )
        blocks = v.validate_blocks().data
        vmeta = v.get_meta().data

        # Infer outdir if still empty
        if not outdir:
            book_id = vmeta.get("book_id", "UNKNOWN_BOOK")
            chnum = int(vmeta.get("chapter_number", 0))
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")

        # 2) Resolve spans
        r = ABMMixedBlockResolver(validated_blocks=blocks, write_to_disk=write, output_dir=outdir)
        spans = r.resolve_spans().data
        rmeta = r.get_meta().data

        # 3) Classify spans
        c = ABMSpanClassifier(spans=spans, write_to_disk=write, output_dir=outdir)
        spans_cls = c.classify_spans().data
        cmeta = c.get_meta().data

        # 4) Attribute speakers
        a = ABMSpanAttribution(spans_cls=spans_cls, write_to_disk=write, output_dir=outdir)
        spans_attr = a.attribute_spans().data
        ameta = a.get_meta().data

        # Optional confidence threshold filtering for dialogue
        try:
            min_pct_str = (getattr(self, "min_confidence_pct", "0") or "0").strip()
            min_pct = int(min_pct_str)
        except Exception:
            min_pct = 0
        if min_pct > 0 and isinstance(spans_attr, dict):
            thr = float(min_pct) / 100.0
            items = spans_attr.get("spans_attr") or []
            if isinstance(items, list):
                filtered: list[dict] = []
                for s in items:
                    role = (s.get("role") or s.get("type") or "").lower()
                    if role == "dialogue":
                        c = ((s.get("attribution") or {}).get("confidence"))
                        try:
                            if c is not None and float(c) >= thr:
                                filtered.append(s)
                        except Exception:
                            pass
                    else:
                        filtered.append(s)
                spans_attr = {"spans_attr": filtered}

        # 5) (Optional) Style Planner
        spans_style = None
        spans_style_counts = None
        if bool(getattr(self, "enable_style_planner", False)):
            sp = ABMStylePlanner(spans_in=spans_attr, write_to_disk=write, output_dir=outdir)
            sp_data = sp.plan_styles().data
            spans_style = sp_data.get("spans_style") if isinstance(sp_data, dict) else None
            spans_style_counts = sp_data.get("counts") if isinstance(sp_data, dict) else None

        self.status = "Artifacts generated"
        return Data(
            data={
                "blocks": blocks,
                "blocks_meta": vmeta,
                "spans": spans,
                "spans_meta": rmeta,
                "spans_cls": spans_cls,
                "spans_cls_meta": cmeta,
                "spans_attr": spans_attr,
                "spans_attr_meta": ameta,
                "spans_style": spans_style,
                "spans_style_counts": spans_style_counts,
                "output_dir": outdir,
            }
        )
