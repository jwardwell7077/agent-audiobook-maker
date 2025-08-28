"""
Character Data Collection Agent - LangFlow Component

Collects character dialogue and narration context for voice casting analysis.
This component focuses on data mining and storage rather than sophisticated analysis.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import DataInput, Output, StrInput
from langflow.schema import Data

logger = logging.getLogger(__name__)


class ABMCharacterDataCollector(Component):
    """Collect character dialogue and narration data for voice casting analysis."""

    display_name = "Character Data Collector"
    description = "Mines character data from speaker-attributed utterances for voice casting preparation"
    icon = "MaterialSymbolsPersonSearch"
    name = "abm_character_data_collector"

    inputs = [
        DataInput(
            name="utterances_data",
            display_name="Utterances Data",
            info="Speaker-attributed utterances from previous agent",
            required=True,
        ),
        StrInput(
            name="book_id",
            display_name="Book ID",
            info="Book identifier for file organization",
            value="",
            required=True,
        ),
        StrInput(
            name="output_directory",
            display_name="Output Directory",
            info="Base directory for character data files",
            value="data/characters",
            required=False,
        ),
    ]

    outputs = [Output(display_name="Collection Stats", name="collection_stats", method="collect_character_data")]

    def collect_character_data(
        self, utterances_data: Data, book_id: str, output_directory: str = "data/characters"
    ) -> Data:
        """Main processing method for character data collection."""

        if not book_id:
            raise ValueError("book_id is required for file organization")

        data = utterances_data.data if isinstance(utterances_data, Data) else utterances_data

        if not isinstance(data, dict) or "utterances" not in data:
            raise ValueError("Input must contain 'utterances' field")

        utterances = data["utterances"]
        if not isinstance(utterances, list):
            raise ValueError("Utterances must be a list")

        # Setup output directory
        output_path = Path(output_directory) / book_id
        output_path.mkdir(parents=True, exist_ok=True)

        # Process utterances and collect character data
        character_registry = self._build_character_registry(utterances, book_id)
        dialogue_records = self._collect_dialogue(utterances, book_id)
        narration_records = self._collect_narration(utterances, book_id)

        # Write data files
        stats = self._write_data_files(output_path, character_registry, dialogue_records, narration_records)

        # Return processing statistics
        self.status = (
            f"Collected data for {stats['characters_found']} characters, {stats['dialogue_count']} dialogue utterances"
        )

        return Data(
            data={
                "collection_stats": stats,
                "output_directory": str(output_path),
                "files_written": ["character_registry.json", "dialogue_collection.jsonl", "narration_context.jsonl"],
            }
        )

    def _build_character_registry(self, utterances: list[dict], book_id: str) -> dict[str, Any]:
        """Build character registry with basic statistics."""
        characters = {}
        chapters_seen = set()

        for utterance in utterances:
            speaker = utterance.get("speaker", "UNKNOWN")
            chapter_id = utterance.get("chapter_id", "unknown")
            # chapter_title available if needed later
            utterance_idx = utterance.get("utterance_idx", 0)
            role = utterance.get("role", "unknown")
            text = utterance.get("text", "")

            chapters_seen.add(chapter_id)

            # Initialize character record if not seen
            if speaker not in characters:
                characters[speaker] = {
                    "character_id": self._normalize_character_id(speaker),
                    "canonical_name": speaker,
                    "aliases": [speaker],  # Start with just the canonical name
                    "first_seen": {"chapter_id": chapter_id, "utterance_idx": utterance_idx},
                    "stats": {"dialogue_count": 0, "narration_count": 0, "chapters_appeared": set(), "total_words": 0},
                }

            # Update character statistics
            char_data = characters[speaker]
            char_data["stats"]["chapters_appeared"].add(chapter_id)
            char_data["stats"]["total_words"] += len(text.split())

            if role == "dialogue":
                char_data["stats"]["dialogue_count"] += 1
            elif role == "narration":
                char_data["stats"]["narration_count"] += 1

        # Convert sets to lists for JSON serialization
        for char_data in characters.values():
            char_data["stats"]["chapters_appeared"] = list(char_data["stats"]["chapters_appeared"])

        # Build final registry structure
        registry = {
            "schema_version": "1.0",
            "book_id": book_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "processing_stats": {
                "chapters_processed": len(chapters_seen),
                "total_utterances": len(utterances),
                "characters_found": len(characters),
            },
            "characters": list(characters.values()),
        }

        return registry

    def _collect_dialogue(self, utterances: list[dict], book_id: str) -> list[dict[str, Any]]:
        """Collect all dialogue utterances by character."""
        dialogue_records = []

        for utterance in utterances:
            if utterance.get("role") != "dialogue":
                continue

            record = {
                "character_id": self._normalize_character_id(utterance.get("speaker", "UNKNOWN")),
                "book_id": book_id,
                "chapter_id": utterance.get("chapter_id", "unknown"),
                "chapter_title": utterance.get("chapter_title", "Unknown Chapter"),
                "utterance_idx": utterance.get("utterance_idx", 0),
                "text": utterance.get("text", ""),
                "word_count": len(utterance.get("text", "").split()),
                "context_before": self._get_context_before(utterances, utterance),
                "context_after": self._get_context_after(utterances, utterance),
                "attribution_confidence": utterance.get("speaker_confidence", 0.0),
                "collected_at": datetime.utcnow().isoformat() + "Z",
            }

            dialogue_records.append(record)

        return dialogue_records

    def _collect_narration(self, utterances: list[dict], book_id: str) -> list[dict[str, Any]]:
        """Collect narration that mentions or describes characters."""
        narration_records = []

        for utterance in utterances:
            if utterance.get("role") != "narration":
                continue

            # For now, collect all narration - later we can filter for character mentions
            record = {
                "character_focus": self._detect_character_focus(utterance.get("text", "")),
                "book_id": book_id,
                "chapter_id": utterance.get("chapter_id", "unknown"),
                "chapter_title": utterance.get("chapter_title", "Unknown Chapter"),
                "utterance_idx": utterance.get("utterance_idx", 0),
                "text": utterance.get("text", ""),
                "word_count": len(utterance.get("text", "").split()),
                "narration_type": "general",  # Placeholder for future classification
                "character_mentioned": self._has_character_mention(utterance.get("text", "")),
                "collected_at": datetime.utcnow().isoformat() + "Z",
            }

            narration_records.append(record)

        return narration_records

    def _write_data_files(
        self,
        output_path: Path,
        character_registry: dict[str, Any],
        dialogue_records: list[dict[str, Any]],
        narration_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Write collected data to files."""

        try:
            # Write character registry
            registry_file = output_path / "character_registry.json"
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(character_registry, f, indent=2, ensure_ascii=False)

            # Write dialogue collection
            dialogue_file = output_path / "dialogue_collection.jsonl"
            with open(dialogue_file, "w", encoding="utf-8") as f:
                for record in dialogue_records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Write narration context
            narration_file = output_path / "narration_context.jsonl"
            with open(narration_file, "w", encoding="utf-8") as f:
                for record in narration_records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Return statistics
            stats = {
                "characters_found": character_registry["processing_stats"]["characters_found"],
                "dialogue_count": len(dialogue_records),
                "narration_count": len(narration_records),
                "total_utterances": character_registry["processing_stats"]["total_utterances"],
                "files_written": 3,
                "output_path": str(output_path),
            }

            logger.info(f"Character data collection complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to write character data files: {e}")
            raise

    def _normalize_character_id(self, speaker: str) -> str:
        """Convert speaker name to normalized character ID."""
        if not speaker or speaker in ["UNKNOWN", "NARRATOR"]:
            return speaker.lower()

        # Simple normalization - remove special chars, lowercase, replace spaces
        normalized = "".join(c.lower() if c.isalnum() else "_" for c in speaker)
        normalized = "_".join(part for part in normalized.split("_") if part)

        return normalized

    def _get_context_before(self, utterances: list[dict], current_utterance: dict) -> str:
        """Get context text before the current utterance."""
        current_idx = current_utterance.get("utterance_idx", 0)

        # Find previous utterance
        for utterance in utterances:
            if utterance.get("utterance_idx") == current_idx - 1:
                text = utterance.get("text", "")
                return text[-50:] if len(text) > 50 else text

        return ""

    def _get_context_after(self, utterances: list[dict], current_utterance: dict) -> str:
        """Get context text after the current utterance."""
        current_idx = current_utterance.get("utterance_idx", 0)

        # Find next utterance
        for utterance in utterances:
            if utterance.get("utterance_idx") == current_idx + 1:
                text = utterance.get("text", "")
                return text[:50] if len(text) > 50 else text

        return ""

    def _detect_character_focus(self, text: str) -> str:
        """Detect which character the narration is focused on (simple heuristic)."""
        # Simple keyword detection - could be enhanced later
        text_lower = text.lower()

        # Common character indicators
        if "quinn" in text_lower:
            return "quinn_talen"
        elif any(word in text_lower for word in ["he", "his", "him"]):
            return "male_character"  # Placeholder
        elif any(word in text_lower for word in ["she", "her", "hers"]):
            return "female_character"  # Placeholder

        return "unknown"

    def _has_character_mention(self, text: str) -> bool:
        """Check if narration mentions any character."""
        text_lower = text.lower()

        # Simple character mention detection
        character_indicators = [
            "quinn",
            "he",
            "she",
            "his",
            "her",
            "him",
            "they",
            "their",
            "boy",
            "girl",
            "man",
            "woman",
            "student",
            "character",
        ]

        return any(indicator in text_lower for indicator in character_indicators)
