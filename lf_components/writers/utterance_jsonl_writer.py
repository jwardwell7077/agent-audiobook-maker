"""LangFlow component to persist utterance records and chapter.

Header artifacts to JSONL/JSON.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import DictInput, Output, StrInput


class UtteranceJSONLWriter(Component):
    """Persist utterances JSONL plus summary header JSON for a chapter."""

    display_name = "Write Utterances JSONL"
    description = "Save utterances to structured/<book_id>/chapter-<id>.jsonl + header"
    icon = "save"
    name = "UtteranceJSONLWriter"

    inputs = [
        DictInput(
            name="utterances_payload",
            display_name="Utterances Payload",
        ),
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

    # Runtime-injected by LangFlow
    utterances_payload: dict[str, Any]
    data_root: str
    annotation_version: str

    def _ensure_dir(self, path: Path) -> None:
        """Create directory if absent."""
        path.mkdir(parents=True, exist_ok=True)

    def build(self) -> dict[str, str]:  # returns plain dict
        """Write utterances + header; return mapping of output file paths."""
        payload: dict[str, Any] = self.utterances_payload
        if not payload or "utterances" not in payload or "chapter_meta" not in payload:
            raise ValueError("Expected keys: utterances, chapter_meta")

        utterances: list[dict[str, Any]] = payload["utterances"]
        meta: dict[str, Any] = payload["chapter_meta"]

        book_id = meta["book_id"]
        chapter_id = meta["chapter_id"]  # e.g., "00001"
        out_dir = Path(self.data_root).expanduser() / "data" / "structured" / book_id
        self._ensure_dir(out_dir)
        jsonl_path = out_dir / f"chapter-{chapter_id}.jsonl"
        header_path = out_dir / f"chapter-{chapter_id}.header.json"

        # Use timezone-aware UTC then strip tz info while retaining 'Z'
        created_at = datetime.now().astimezone().replace(microsecond=0).isoformat()
        if not created_at.endswith("Z"):
            created_at = created_at + "Z"
        models = {
            "segmentation": "rule_v0",
            "coref": "",
            "emotion": "",
            "prosody": "",
            "llm_judge": "",
        }

        with jsonl_path.open("w", encoding="utf-8") as f:
            for u in utterances:
                emphasis_spans: list[str] = []
                style_tags: list[str] = []
                characters_present: list[str] = ["char:narrator"]
                rec: dict[str, Any] = {
                    "uid": u["uid"],
                    "chapter_id": int(meta["index"]) + 1,
                    "span": u["span"],
                    "text": u["text"],
                    "type": u["type"],
                    "speaker": {
                        "id": ("char:narrator" if u["type"] == "narration" else "char:unknown"),
                        "name": ("Narrator" if u["type"] == "narration" else "Unknown"),
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
                        "emphasis_spans": emphasis_spans,
                        "style_tags": style_tags,
                    },
                    "context": {
                        "scene": "",
                        "location": "",
                        "time": "",
                        "characters_present": characters_present,
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
                "dialogue_pct": (sum(1 for u in utterances if u["type"] == "dialogue") / max(1, len(utterances))),
                "narration_pct": (sum(1 for u in utterances if u["type"] == "narration") / max(1, len(utterances))),
                "avg_utterance_len": (sum(len(u["text"]) for u in utterances) / max(1, len(utterances))),
            },
            "created_at": created_at,
            "annotation_version": self.annotation_version,
            "models": models,
            "source": {
                "chapter_json": (f"data/clean/{book_id}/{meta['chapter_id']}.json"),
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
