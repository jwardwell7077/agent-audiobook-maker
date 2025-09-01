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
            name="blocks_data",
            display_name="Blocks Data",
            info="Output from ABM Chapter Loader",
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
            name="start_block",
            display_name="Start Block ID",
            info="Start processing from this block (for debugging)",
            value=0,
            required=False,
        ),
        IntInput(
            name="max_blocks",
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
        self._current_block_index = 0
        self._processed_blocks: list[int] = []
        self._total_processed = 0

    def get_next_utterance(self) -> Data:
        """Get the next block formatted for two-agent processing."""
        try:
            input_data = self.blocks_data.data

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            blocks = input_data.get("blocks", [])
            if not blocks:
                self.status = "No blocks to process"
                return Data(data={"error": "No blocks available"})

            # Filter blocks if needed
            filtered_blocks = self._filter_and_sort_blocks(blocks)

            # Check if we have blocks to process
            if self._current_block_index >= len(filtered_blocks):
                # All blocks processed
                return self._create_completion_summary(input_data)

            # Get current block
            current_block = filtered_blocks[self._current_block_index]

            # Prepare utterance data for Agent 1 (Dialogue Classifier)
            utterance_data = self._prepare_utterance_for_agents(current_block, input_data)

            # Update tracking
            self._current_block_index += 1
            self._processed_blocks.append(current_block["block_id"])
            self._total_processed += 1

            # Update status
            self.status = (
                f"Processing block {current_block['block_id']}/{len(filtered_blocks)} - {current_block['type']}"
            )

            return Data(data=utterance_data)

        except Exception as e:  # noqa: BLE001
            error_msg = f"Failed to get next utterance: {str(e)}"
            self.status = f"Error: {error_msg}"
            logging.error(error_msg)
            return Data(data={"error": error_msg})

    def _filter_and_sort_blocks(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter and sort blocks based on processing preferences."""
        filtered_blocks = blocks.copy()

        # Filter by start block
        if self.start_block > 0:
            filtered_blocks = [c for c in filtered_blocks if c["block_id"] >= self.start_block]

        # Limit max blocks
        if self.max_blocks > 0:
            filtered_blocks = filtered_blocks[: self.max_blocks]

        # Sort by priority if enabled
        if self.dialogue_priority:
            # Sort dialogue first, then by block_id
            filtered_blocks.sort(
                key=lambda x: (
                    0 if x["type"] == "dialogue" else 1 if x["type"] == "mixed" else 2,
                    x["block_id"],
                )
            )
        else:
            # Sort by block_id only
            filtered_blocks.sort(key=lambda x: x["block_id"])

        return filtered_blocks

    def _prepare_utterance_for_agents(self, block: dict[str, Any], chapter_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare block data for two-agent processing pipeline."""

        # Base utterance data for Agent 1 (ABMDialogueClassifier)
        utterance_data = {
            # Core text data
            "utterance_text": block["text"],
            "context_before": block.get("context_before", ""),
            "context_after": block.get("context_after", ""),
            # Identification data
            "book_id": chapter_data["book_name"],
            "chapter_id": f"chapter_{chapter_data['chapter_index']:02d}",
            "utterance_idx": block["block_id"],
            # Processing hints from iterator
            "processing_hints": block.get("processing_hints", {}),
            "expected_type": block["type"],
            "dialogue_text": block.get("dialogue_text", ""),
            "attribution_clues": block.get("attribution_clues", []),
            # Metadata for tracking
            "block_metadata": {
                "chapter_title": block.get("chapter_title", ""),
                "word_count": block["word_count"],
                "sentence_count": block.get("sentence_count", 1),
                "complexity": block.get("processing_hints", {}).get("complexity", "medium"),
                "priority": block.get("processing_hints", {}).get("priority", "medium"),
            },
            # Processing pipeline info
            "pipeline_info": {
                "source_component": "ABMBlockIterator",
                "processing_batch": self._current_block_index // self.batch_size + 1,
                "total_blocks_in_chapter": len(chapter_data.get("blocks", [])),
                "current_block_index": self._current_block_index + 1,
            },
        }

        return utterance_data

    def _create_completion_summary(self, chapter_data: dict[str, Any]) -> Data:
        """Create summary when all blocks are processed."""
        summary_data = {
            "processing_status": "completed",
            "summary": {
                "total_blocks_processed": self._total_processed,
                "blocks_processed": self._processed_blocks,
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
        self._current_block_index = 0
        self._processed_blocks = []
        self._total_processed = 0

        return Data(data=summary_data)
