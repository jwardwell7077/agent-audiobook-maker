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
            required=False,
        ),
        # Back-compat alias for callers/tests using 'blocks_data'
        DataInput(
            name="blocks_data",
            display_name="Blocks Data (alias)",
            info="Alias input; equivalent to Chunked Chapter Data",
            required=False,
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
            display_name="Start index (0-based)",
            info="Start processing at this 0-based block index",
            value=0,
            required=False,
        ),
        # Back-compat alias
        IntInput(
            name="start_block",
            display_name="Start block (alias)",
            info="Alias of start index for older flows/tests",
            value=0,
            required=False,
        ),
        IntInput(
            name="max_chunks",
            display_name="Max Blocks to Process",
            info="Limit processing to this many blocks (0 = all)",
            value=0,
            required=False,
        ),
        # Back-compat alias
        IntInput(
            name="max_blocks",
            display_name="Max Blocks (alias)",
            info="Alias of max chunks for older flows/tests",
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
        # Back-compat argument aliases
        if hasattr(self, "blocks_data") and not hasattr(self, "chunked_data"):
            self.chunked_data = self.blocks_data  # type: ignore[attr-defined]
        if hasattr(self, "start_block") and not hasattr(self, "start_chunk"):
            try:
                self.start_chunk = int(self.start_block)  # type: ignore[attr-defined]
            except Exception:
                self.start_chunk = 0
        if hasattr(self, "max_blocks") and not hasattr(self, "max_chunks"):
            try:
                self.max_chunks = int(self.max_blocks)  # type: ignore[attr-defined]
            except Exception:
                self.max_chunks = 0

        # Defaults
        if not hasattr(self, "batch_size"):
            self.batch_size = 10
        if not hasattr(self, "dialogue_priority"):
            self.dialogue_priority = True

        self._current_chunk_index = 0
        self._processed_chunks: list[int] = []
        self._total_processed = 0

    def get_next_utterance(self) -> Data:
        """Get the next block formatted for two-agent processing."""
        try:
            # Prefer chunked_data; fall back to blocks_data
            src = getattr(self, "chunked_data", None) or getattr(self, "blocks_data", None)
            if src is None:
                raise TypeError("chunked_data/blocks_data input is missing")
            if hasattr(src, "data"):
                input_data = src.data  # type: ignore[attr-defined]
            elif isinstance(src, dict):
                input_data = src
            else:
                raise TypeError("chunked_data/blocks_data must be a Data or dict payload")

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            chunks = input_data.get("chunks") or input_data.get("blocks", [])
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
            cid = int(current_chunk.get("chunk_id") or current_chunk.get("block_id") or 0)
            self._processed_chunks.append(cid)
            self._total_processed += 1

            # Update status
            cur_id = current_chunk.get("chunk_id") or current_chunk.get("block_id")
            cur_type = current_chunk.get("type", "unknown")
            self.status = f"Processing block {cur_id}/{len(filtered_chunks)} - {cur_type}"

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
        start_at = int(getattr(self, "start_chunk", 0) or 0)
        if start_at > 0:
            def _cid(c: dict[str, Any]) -> int:
                return int(c.get("chunk_id") or c.get("block_id") or 0)
            filtered_chunks = [c for c in filtered_chunks if _cid(c) >= start_at]

        # Limit max blocks
        maxn = int(getattr(self, "max_chunks", 0) or 0)
        if maxn > 0:
            filtered_chunks = filtered_chunks[:maxn]

        # Sort by priority if enabled
        if bool(getattr(self, "dialogue_priority", True)):
            # Sort dialogue first, then by chunk_id
            def _cid(c: dict[str, Any]) -> int:
                return int(c.get("chunk_id") or c.get("block_id") or 0)

            filtered_chunks.sort(
                key=lambda x: (
                    0
                    if x.get("type") == "dialogue"
                    else 1 if x.get("type") == "mixed" else 2,
                    _cid(x),
                )
            )
        else:
            # Sort by chunk_id only
            def _cid(c: dict[str, Any]) -> int:
                return int(c.get("chunk_id") or c.get("block_id") or 0)
            filtered_chunks.sort(key=_cid)

        return filtered_chunks

    def _prepare_utterance_for_agents(self, chunk: dict[str, Any], chapter_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare block data for two-agent processing pipeline."""

        # Normalize identifiers and totals
        chunk_id = int(chunk.get("chunk_id") or chunk.get("block_id") or 0)
        total = len(chapter_data.get("chunks", [])) or len(chapter_data.get("blocks", []))

        # Base utterance data for Agent 1 (ABMDialogueClassifier)
        utterance_data = {
            # Core text data
            "utterance_text": chunk["text"],
            "context_before": chunk.get("context_before", ""),
            "context_after": chunk.get("context_after", ""),
            # Identification data
            "book_id": chapter_data.get("book_name", chapter_data.get("book", "")),
            "chapter_id": f"chapter_{int(chapter_data.get('chapter_index', 0)):02d}",
            "utterance_idx": chunk_id,
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
                "total_chunks_in_chapter": total,
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
