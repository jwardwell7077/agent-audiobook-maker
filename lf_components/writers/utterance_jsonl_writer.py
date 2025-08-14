from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from langflow.custom import Component
from langflow.io import StrInput, Output, DictInput


class UtteranceJSONLWriter(Component):
    display_name = "Write Utterances JSONL"
    description = (
        "Save utterances to structured/<book_id>/chapter-<id>.jsonl + header"
    )
    icon = "save"
    name = "UtteranceJSONLWriter"

    inputs = [
        DictInput(name="utterances_payload", display_name="Utterances Payload"),
        StrInput(
            name="data_root",
            display_name="Project Root",
            value="/home/jon/repos/audio-book-maker-lg",
        ),
        StrInput(
            name="annotation_version",
            display_name="Annotation Version",
            value="v0.1.0",
        ),
    ]

    outputs = [
        Output(name="paths", display_name="Output Paths", method="build"),
    ]

    def _ensure_dir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)

    def build(self):  # returns plain dict
    payload: Dict[str, Any] = self.utterances_payload
        if (
            not payload
            or "utterances" not in payload
            or "chapter_meta" not in payload
        ):
            raise ValueError("Expected keys: utterances, chapter_meta")

        utterances: List[Dict[str, Any]] = payload["utterances"]
        meta: Dict[str, Any] = payload["chapter_meta"]

        book_id = meta["book_id"]
        chapter_id = meta["chapter_id"]  # e.g., "00001"
        out_dir = (
            Path(self.data_root).expanduser()
            / "data"
            / "structured"
            / book_id
        )
        self._ensure_dir(out_dir)

        jsonl_path = out_dir / f"chapter-{chapter_id}.jsonl"
        header_path = out_dir / f"chapter-{chapter_id}.header.json"

    # Minimal fields to match utterance schema (speaker/emotion stubbed)
        created_at = datetime.utcnow().isoformat() + "Z"
        models = {
            "segmentation": "rule_v0",
            "coref": "",
            "emotion": "",
            "prosody": "",
            "llm_judge": "",
        }

        with jsonl_path.open("w", encoding="utf-8") as f:
            for u in utterances:
                rec = {
                    "uid": u["uid"],
                    "chapter_id": int(meta["index"]) + 1,
                    "span": u["span"],
                    "text": u["text"],
                    "type": u["type"],
                    "speaker": {
                        "id": (
                            "char:narrator"
                            if u["type"] == "narration"
                            else "char:unknown"
                        ),
                        "name": (
                            "Narrator"
                            if u["type"] == "narration"
                            else "Unknown"
                        ),
                        "confidence": 0.5,
                        "evidence": ["rule_heuristic"],
                    },
                    "emotion": {
                        "primary": "neutral",
                        "secondary": [],
                        "intensity": 0.1,
                        "confidence": 0.5,
                    },
                    "prosody": {
                        "rate": "medium",
                        "pitch": "neutral",
                        "volume": "medium",
                        "pause_before_ms": 0,
                        "pause_after_ms": 150,
                        "emphasis_spans": [],
                        "style_tags": [],
                    },
                    "context": {
                        "scene": "",
                        "location": "",
                        "time": "",
                        "characters_present": ["char:narrator"],
                    },
                    "directives": [],
                    "qa": {"needs_review": False, "notes": None},
                    "audit": {
                        "annotation_version": self.annotation_version,
                        "created_at": created_at,
                        "models": models,
                    },
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        header = {
            "book_id": book_id,
            "chapter_id": meta["chapter_id"],
            "title": meta["title"],
            "sha256": meta["text_sha256"],
            "token_counts": {
                "chars": sum(len(u["text"]) for u in utterances),
                "words": sum(len(u["text"].split()) for u in utterances),
                "sentences": len(utterances),
                "utterances": len(utterances),
            },
            "stats": {
                "dialogue_pct": (
                    sum(1 for u in utterances if u["type"] == "dialogue")
                    / max(1, len(utterances))
                ),
                "narration_pct": (
                    sum(1 for u in utterances if u["type"] == "narration")
                    / max(1, len(utterances))
                ),
                "avg_utterance_len": (
                    sum(len(u["text"]) for u in utterances)
                    / max(1, len(utterances))
                ),
            },
            "created_at": created_at,
            "annotation_version": self.annotation_version,
            "models": models,
            "source": {
                "chapter_json": f"data/clean/{book_id}/{meta['chapter_id']}.json",
                "extraction_tool": "N/A",
            },
            "processing": {
                "status": "annotated",
                "notes": "baseline segmentation only",
            },
        }
        with header_path.open("w", encoding="utf-8") as f:
            json.dump(header, f, ensure_ascii=False, indent=2)

        return {"jsonl_path": str(jsonl_path), "header_path": str(header_path)}
