from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from langflow.custom import Component
from langflow.io import DataInput, StrInput, Output
from langflow.schema import Data


class ABMUtteranceJSONLWriter(Component):
    """Write utterances to JSONL following annotation schema."""

    display_name = "Utterance JSONL Writer"
    description = "Write utterances to JSONL with proper annotation schema."
    icon = "MaterialSymbolsOutput"
    name = "abm_utterance_jsonl_writer"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Payload containing 'utterances' list from segmentation.",
            required=True,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            value="data/annotations",
            info="Directory to write JSONL files.",
        ),
        StrInput(
            name="filename",
            display_name="Filename",
            value="utterances_v1.jsonl",
            info="JSONL filename (e.g., utterances_v1.jsonl).",
        ),
    ]

    outputs = [
        Output(
            display_name="Output Payload",
            name="output_payload",
            method="write"
        )
    ]

    def write(
        self,
        payload: Data,
        output_dir: str = "data/annotations",
        filename: str = "utterances_v1.jsonl",
    ) -> Data:
        """Write utterances to JSONL with annotation schema structure."""
        data = payload.data if isinstance(payload, Data) else payload
        
        if not isinstance(data, dict):
            raise ValueError("Payload must be a dict-like Data object")
        
        utterances = data.get("utterances", [])
        if not utterances:
            self.status = "ERROR: No utterances found in payload"
            return Data(data={**data, "error": "No utterances found"})
        
        book_id = data.get("book_id", "unknown")
        
        # Create output directory
        output_path = Path(output_dir)
        if book_id != "unknown":
            output_path = output_path / book_id
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        jsonl_file = output_path / filename
        
        # Write JSONL with annotation schema format
        try:
            with open(jsonl_file, 'w', encoding='utf-8') as f:
                for utterance in utterances:
                    # Convert to annotation schema format
                    annotation_record = {
                        "book_id": book_id,
                        "chapter_id": utterance.get("chapter_idx", 0),
                        "utterance_idx": utterance.get("utterance_idx", 0),
                        "text": utterance.get("text", ""),
                        "start_char": 0,  # TODO: calculate actual positions
                        "end_char": len(utterance.get("text", "")),
                        "speaker": "UNKNOWN",  # To be filled by attribution
                        "speaker_confidence": 0.0,
                        "role": utterance.get("role", "narration"),
                        "emotion": "neutral",
                        "prosody": {
                            "pitch": "mid",
                            "rate": "medium",
                            "intensity": "normal"
                        },
                        "qa_flags": [],
                        "created_at": datetime.now().isoformat(),
                        "version": "v1.0"
                    }
                    
                    f.write(json.dumps(annotation_record) + '\n')
            
            # Create output payload
            output_data = dict(data)
            output_data["output_file"] = str(jsonl_file)
            output_data["records_written"] = len(utterances)
            output_data["annotation_version"] = "v1.0"
            
            msg = f"Wrote {len(utterances)} records to {jsonl_file}"
            self.status = msg
            return Data(data=output_data)
            
        except Exception as e:
            self.status = f"ERROR: Failed to write JSONL: {str(e)}"
            return Data(data={**data, "error": str(e)})
