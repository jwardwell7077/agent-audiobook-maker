"""ABM Utterance JSONL Writer Component for LangFlow.

Writes utterances as records-only JSONL and a sidecar meta file, aligning with
ABMAggregatedJsonlWriter for consistency.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from langflow.custom import Component
from langflow.io import DataInput, Output, StrInput
from langflow.schema import Data


class ABMUtteranceJsonlWriter(Component):
    display_name = "ABM Utterance JSONL Writer"
    description = "Write segmented utterances to JSONL with sidecar metadata"
    icon = "file-text"
    name = "ABMUtteranceJsonlWriter"

    inputs = [
        DataInput(
            name="segmented_data",
            display_name="Segmented Data",
            info="Data containing segmented chapters",
            required=True,
        ),
        StrInput(
            name="output_file",
            display_name="Output File Path",
            info="Path where JSONL file will be written",
            value="output/utterances.jsonl",
            required=True,
        ),
    ]

    outputs = [Output(name="written_data", display_name="Written Data", method="write_utterances")]

    def write_utterances(self) -> Data:
        """Write segmented utterances to JSONL file with sidecar meta."""
        try:
            input_data = self.segmented_data.data

            segmented_chapters = input_data.get("segmented_chapters", [])

            # Ensure output directory exists
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Flatten utterances from segmented chapters
            utterances: list[dict] = [
                {
                    "role": segment.get("type", "unknown"),
                    "text": segment.get("text", ""),
                    "chapter_index": chapter.get("chapter_index"),
                    "chapter_title": chapter.get("chapter_title", ""),
                    "book": input_data.get("book"),
                    "volume": input_data.get("volume"),
                }
                for chapter in segmented_chapters
                for segment in chapter.get("segments", [])
            ]

            # Write JSONL records (no header)
            with output_path.open("w", encoding="utf-8") as f:
                for u in utterances:
                    f.write(json.dumps(u, ensure_ascii=False) + "\n")

            # Sidecar meta file
            meta = {
                "version": "0.2",
                "created_at": datetime.now(UTC).isoformat(),
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
                "chapters_processed": len(segmented_chapters),
                "count": len(utterances),
            }
            meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            result_data = {
                "output_file": str(output_path),
                "meta_file": str(meta_path),
                "utterances_written": len(utterances),
                "chapters_processed": len(segmented_chapters),
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
            }

            self.status = f"Wrote {len(utterances)} utterances → {output_path} (meta: {meta_path.name})"
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to write utterances: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})


def run(segmented_data: dict, base_dir: str | None = None, stem: str | None = None) -> dict:
    """Convenience wrapper to write utterances as JSONL and return path.

    - base_dir: when provided, file will be written under base_dir/output.
    - stem: file name stem; defaults to segments_<timestamp> inside component.
    """
    # Compute default path if not provided
    base = Path(base_dir) if base_dir else Path.cwd()
    out_dir = base / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = (stem or "segments") + ".jsonl"
    comp = ABMUtteranceJsonlWriter()
    comp.segmented_data = Data(data=segmented_data)
    comp.output_file = str(out_dir / filename)
    result = comp.write_utterances().data
    # Provide a legacy-friendly alias used by abm.langflow_runner
    if "path" not in result and "output_file" in result:
        result["path"] = result["output_file"]
    return result
