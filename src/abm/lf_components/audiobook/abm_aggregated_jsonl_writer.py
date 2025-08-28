"""ABM Aggregated JSONL Writer for LangFlow.

Writes normalized utterances (from Results→Utterances) to a JSONL file.
Separately writes a .meta.json next to the JSONL to avoid header-in-JSONL.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from langflow.custom import Component
from langflow.io import DataInput, Output, StrInput
from langflow.schema import Data


class ABMAggregatedJsonlWriter(Component):
    display_name = "ABM Aggregated JSONL Writer"
    description = "Write normalized utterances to JSONL with sidecar metadata"
    icon = "file-output"
    name = "ABMAggregatedJsonlWriter"

    inputs = [
        DataInput(
            name="utterances_data",
            display_name="Utterances Data",
            info="Normalized utterances from ABM Results → Utterances",
            required=True,
        ),
        StrInput(
            name="output_path",
            display_name="Output Path",
            info="Destination JSONL file, e.g., data/annotations/<book>/chapter_01.jsonl",
            value="output/utterances.jsonl",
            required=True,
        ),
    ]

    outputs = [Output(display_name="Write Result", name="write_result", method="write")]

    def write(self) -> Data:
        payload = self.utterances_data.data
        if "error" in payload:
            self.status = "Input contains error, passing through"
            return Data(data=payload)

        utterances = payload.get("utterances") or []
        chapter_info = payload.get("chapter_info") or {}

        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Sidecar metadata
        meta = {
            "version": "0.2",
            "created_at": datetime.now(UTC).isoformat(),
            "chapter_info": chapter_info,
            "count": len(utterances),
        }
        meta_path = out_path.with_suffix(out_path.suffix + ".meta.json")

        # Write JSONL (records only)
        with out_path.open("w", encoding="utf-8") as f:
            for u in utterances:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")

        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        self.status = f"Wrote {len(utterances)} utterances → {out_path} (meta: {meta_path.name})"
        return Data(
            data={
                "output_file": str(out_path),
                "meta_file": str(meta_path),
                "utterances_written": len(utterances),
            }
        )
