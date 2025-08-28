"""ABM Block Iterator for LangFlow Two-Agent Processing."""

from __future__ import annotations

import logging
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, IntInput, Output
from langflow.schema import Data


class ABMBlockIterator(Component):
    display_name = "ABM Block Iterator"
    description = "Process blocks through two-agent pipeline with batch management"
    icon = "repeat"
    name = "ABMBlockIterator"

    inputs = [
        DataInput(
            name="chunked_data",
            display_name="Chunked Chapter Data",
            info="Output from Enhanced Chapter Loader",
            required=True,
        ),
        IntInput(
            name="batch_size",
            display_name="Batch Size",
            info="Number of blocks to process per batch",
            value=10,
            required=False,
        ),
        IntInput(
            name="start_chunk",
            display_name="Start Block ID",
            info="Start processing from this block (for debugging)",
            value=1,
            required=False,
        ),
        IntInput(
            name="max_chunks",
            display_name="Max Blocks to Process",
            info="Limit processing to this many blocks (0 = all)",
            value=0,
            required=False,
        ),
        BoolInput(
            name="dialogue_priority",
            display_name="Prioritize Dialogue Blocks",
            info="Process dialogue blocks first",
            value=True,
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Current Utterance", name="current_utterance", method="get_next_utterance"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_chunk_index = 0
        self._processed_chunks: list[int] = []
        self._total_processed = 0

    def get_next_utterance(self) -> Data:
        """Get the next block formatted for two-agent processing."""
        try:
            input_data = self.chunked_data.data

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            chunks = input_data.get("chunks", [])
            if not chunks:
                self.status = "No blocks to process"
                return Data(data={"error": "No blocks available"})

            # Filter chunks if needed
            filtered_chunks = self._filter_and_sort_chunks(chunks)

            # Check if we have chunks to process
            if self._current_chunk_index >= len(filtered_chunks):
                # All chunks processed
                return self._create_completion_summary(input_data)

            # Get current chunk
            current_chunk = filtered_chunks[self._current_chunk_index]

            # Prepare utterance data for Agent 1 (Dialogue Classifier)
            utterance_data = self._prepare_utterance_for_agents(current_chunk, input_data)

            # Update tracking
            self._current_chunk_index += 1
            self._processed_chunks.append(current_chunk["chunk_id"])
            self._total_processed += 1

            # Update status
            self.status = (
                f"Processing block {current_chunk['chunk_id']}/{len(filtered_chunks)} - {current_chunk['type']}"
            )

            return Data(data=utterance_data)

        except Exception as e:  # noqa: BLE001
            error_msg = f"Failed to get next utterance: {str(e)}"
            self.status = f"Error: {error_msg}"
            logging.error(error_msg)
            return Data(data={"error": error_msg})

    def _filter_and_sort_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter and sort blocks based on processing preferences."""
        filtered_chunks = chunks.copy()

        # Filter by start block
        if self.start_chunk > 1:
            filtered_chunks = [c for c in filtered_chunks if c["chunk_id"] >= self.start_chunk]

        # Limit max blocks
        if self.max_chunks > 0:
            filtered_chunks = filtered_chunks[: self.max_chunks]

        # Sort by priority if enabled
        if self.dialogue_priority:
            # Sort dialogue first, then by chunk_id
            filtered_chunks.sort(
                key=lambda x: (0 if x["type"] == "dialogue" else 1 if x["type"] == "mixed" else 2, x["chunk_id"])
            )
        else:
            # Sort by chunk_id only
            filtered_chunks.sort(key=lambda x: x["chunk_id"])

        return filtered_chunks

    def _prepare_utterance_for_agents(self, chunk: dict[str, Any], chapter_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare block data for two-agent processing pipeline."""

        # Base utterance data for Agent 1 (ABMDialogueClassifier)
        utterance_data = {
            # Core text data
            "utterance_text": chunk["text"],
            "context_before": chunk.get("context_before", ""),
            "context_after": chunk.get("context_after", ""),
            # Identification data
            "book_id": chapter_data["book_name"],
            "chapter_id": f"chapter_{chapter_data['chapter_index']:02d}",
            "utterance_idx": chunk["chunk_id"],
            # Processing hints from iterator
            "processing_hints": chunk.get("processing_hints", {}),
            "expected_type": chunk["type"],
            "dialogue_text": chunk.get("dialogue_text", ""),
            "attribution_clues": chunk.get("attribution_clues", []),
            # Metadata for tracking
            "chunk_metadata": {
                "chapter_title": chunk.get("chapter_title", ""),
                "word_count": chunk["word_count"],
                "sentence_count": chunk.get("sentence_count", 1),
                "complexity": chunk.get("processing_hints", {}).get("complexity", "medium"),
                "priority": chunk.get("processing_hints", {}).get("priority", "medium"),
            },
            # Processing pipeline info
            "pipeline_info": {
                "source_component": "ABMBlockIterator",
                "processing_batch": self._current_chunk_index // self.batch_size + 1,
                "total_chunks_in_chapter": len(chapter_data.get("chunks", [])),
                "current_chunk_index": self._current_chunk_index + 1,
            },
        }

        return utterance_data

    def _create_completion_summary(self, chapter_data: dict[str, Any]) -> Data:
        """Create summary when all blocks are processed."""

        summary_data = {
            "processing_status": "completed",
            "summary": {
                "total_chunks_processed": self._total_processed,
                "chunks_processed": self._processed_chunks,
                "chapter_info": {
                    "book_name": chapter_data["book_name"],
                    "chapter_index": chapter_data["chapter_index"],
                    "chapter_title": chapter_data.get("chapter_title", ""),
                },
                "processing_metadata": chapter_data.get("processing_metadata", {}),
            },
            "next_action": "aggregate_results",
        }

        self.status = f"Completed processing {self._total_processed} blocks"

        # Reset for next run
        self._current_chunk_index = 0
        self._processed_chunks = []
        self._total_processed = 0

        return Data(data=summary_data)
