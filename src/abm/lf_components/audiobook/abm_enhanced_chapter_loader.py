"""ABM Enhanced Chapter Loader for End-to-End LangFlow Processing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, IntInput, Output, StrInput
from langflow.schema import Data


class ABMEnhancedChapterLoader(Component):
    display_name = "ABM Enhanced Chapter Loader"
    description = "Load and intelligently chunk MVS chapters for two-agent processing"
    icon = "book-open"
    name = "ABMEnhancedChapterLoader"

    inputs = [
        StrInput(
            name="book_name",
            display_name="Book Name",
            info="Name of the book to load (e.g., 'mvs')",
            value="mvs",
            required=True,
        ),
        IntInput(
            name="chapter_index",
            display_name="Chapter Index",
            info="Chapter number to load (1-based)",
            value=1,
            required=True,
        ),
        IntInput(
            name="max_chunk_size",
            display_name="Max Chunk Size (words)",
            info="Maximum words per chunk for LLM processing",
            value=300,
            required=False,
        ),
        IntInput(
            name="context_sentences",
            display_name="Context Sentences",
            info="Number of sentences for context before/after",
            value=2,
            required=False,
        ),
        BoolInput(
            name="preserve_dialogue",
            display_name="Preserve Dialogue Boundaries",
            info="Don't split dialogue quotes across chunks",
            value=True,
            required=False,
        ),
        StrInput(
            name="base_data_dir",
            display_name="Data Directory Path",
            info="Absolute path to data directory",
            value="/home/jon/repos/audio-book-maker-lg/data/clean",
            required=False,
        ),
        StrInput(
            name="chapters_file",
            display_name="Chapters File Override",
            info="Optional explicit path to chapters JSON (e.g., chapters_section.json)",
            value="",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Chunked Chapter Data", name="chunked_data", method="load_and_chunk_chapter"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Dialogue detection patterns
        self.dialogue_patterns = [
            r'"[^"]*"',  # Standard quotes
            r"'[^']*'",  # Single quotes
            r'"[^"]*"',  # Smart quotes
        ]

        # Attribution patterns (speaker indicators)
        self.attribution_patterns = [
            r"\b(\w+)\s+(said|asked|replied|shouted|whispered|exclaimed)\b",
            r"\b(he|she|they)\s+(said|asked|replied)\b",
            r"\bsaid\s+(\w+)\b",
        ]

        # Narration indicators
        self.narration_patterns = [
            r"\b(\w+)\s+(walked|ran|thought|looked|felt|seemed)\b",
            r"\b(The|A|An)\s+\w+",
            r"\b(Meanwhile|However|Then|After|Before)\b",
        ]

    def load_and_chunk_chapter(self) -> Data:
        """Load chapter from MVS data and return intelligently chunked segments."""
        try:
            # Load chapters data
            # Prefer explicit override if provided
            if getattr(self, "chapters_file", ""):
                chapters_path = Path(self.chapters_file)
            else:
                chapters_path = Path(self.base_data_dir) / self.book_name / "chapters.json"

            if not chapters_path.exists():
                error_msg = f"Chapters file not found: {chapters_path}"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})

            with open(chapters_path, encoding="utf-8") as f:
                chapters_data = json.load(f)

            # Find target chapter
            target_chapter = None
            for chapter in chapters_data.get("chapters", []):
                if chapter.get("index") == self.chapter_index:
                    target_chapter = chapter
                    break

            if not target_chapter:
                error_msg = f"Chapter {self.chapter_index} not found in {self.book_name}"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})

            # Resolve chapter text from paragraphs[] (required)
            paragraphs = target_chapter.get("paragraphs")
            if not isinstance(paragraphs, list) or not paragraphs:
                error_msg = f"Chapter {self.chapter_index} is missing required paragraphs[] in {chapters_path}"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})
            chapter_text = "\n\n".join(p for p in paragraphs if isinstance(p, str))

            # Chunk the chapter text
            chunks = self._chunk_chapter_text(
                chapter_text, target_chapter.get("title", f"Chapter {self.chapter_index}")
            )

            # Prepare output data
            result_data = {
                "book_name": self.book_name,
                "chapter_index": self.chapter_index,
                "chapter_title": target_chapter.get("title", ""),
                "total_chunks": len(chunks),
                "chunks": chunks,
                "processing_metadata": {
                    "chunk_sizes": [c["word_count"] for c in chunks],
                    "dialogue_chunks": len([c for c in chunks if c["type"] == "dialogue"]),
                    "narration_chunks": len([c for c in chunks if c["type"] == "narration"]),
                    "mixed_chunks": len([c for c in chunks if c["type"] == "mixed"]),
                    "total_words": sum(c["word_count"] for c in chunks),
                    "avg_chunk_size": sum(c["word_count"] for c in chunks) / len(chunks) if chunks else 0,
                },
            }

            self.status = f"Loaded and chunked {len(chunks)} segments from {target_chapter['title']}"
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to load and chunk chapter: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def _chunk_chapter_text(self, chapter_text: str, chapter_title: str) -> list[dict[str, Any]]:
        """Chunk chapter text into optimal segments for LLM processing."""
        if not chapter_text:
            return []

        # Split into sentences with dialogue awareness
        sentences = self._split_into_sentences(chapter_text)

        chunks: list[dict[str, Any]] = []
        current_chunk: list[str] = []
        current_size = 0
        chunk_id = 1

        for i, sentence in enumerate(sentences):
            sentence_words = len(sentence.split())

            # Check if adding sentence exceeds max size
            if current_size + sentence_words > self.max_chunk_size and current_chunk:
                # Flush current chunk
                chunk_text = " ".join(current_chunk).strip()
                if chunk_text:
                    chunks.append(self._create_chunk(chunk_text, chunk_id, sentences, i, current_chunk, chapter_title))
                    chunk_id += 1

                # Start new chunk
                current_chunk = [sentence]
                current_size = sentence_words
            else:
                current_chunk.append(sentence)
                current_size += sentence_words

        # Don't forget final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append(
                    self._create_chunk(chunk_text, chunk_id, sentences, len(sentences), current_chunk, chapter_title)
                )

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Smart sentence splitting that preserves dialogue boundaries."""
        sentences = []
        current_sentence = ""
        in_quote = False
        quote_char = None

        for char in text:
            current_sentence += char

            # Track quote state
            if char in ['"', "'", '"', '"'] and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None

            # Split on sentence endings, but not within quotes
            if char in [".", "!", "?"] and not in_quote:
                # Look ahead to see if this is really the end
                if self._is_sentence_end(current_sentence):
                    sentences.append(current_sentence.strip())
                    current_sentence = ""

        # Add remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return [s for s in sentences if s.strip()]

    def _is_sentence_end(self, sentence: str) -> bool:
        """Check if this is a real sentence ending."""
        # Avoid splitting on abbreviations, decimals, etc.
        if sentence.endswith((" Mr.", " Mrs.", " Dr.", " Prof.", " Inc.", " Ltd.")):
            return False
        if re.search(r"\d+\.\d*$", sentence):  # Decimal numbers
            return False
        return True

    def _create_chunk(
        self,
        chunk_text: str,
        chunk_id: int,
        all_sentences: list[str],
        current_index: int,
        current_chunk: list[str],
        chapter_title: str,
    ) -> dict[str, Any]:
        """Create a properly structured chunk with metadata."""

        # Determine chunk type (dialogue vs narration)
        chunk_type = self._classify_chunk_type(chunk_text)

        # Generate context windows
        context_before = self._get_context_before(all_sentences, current_index - len(current_chunk))
        context_after = self._get_context_after(all_sentences, current_index)

        # Extract dialogue if present
        dialogue_text = self._extract_dialogue(chunk_text) if chunk_type in ["dialogue", "mixed"] else ""

        # Find attribution clues
        attribution_clues = self._find_attribution_clues(chunk_text + " " + context_after)

        return {
            "chunk_id": chunk_id,
            "text": chunk_text,
            "type": chunk_type,
            "word_count": len(chunk_text.split()),
            "char_count": len(chunk_text),
            "sentence_count": len(current_chunk),
            "dialogue_text": dialogue_text,
            "attribution_clues": attribution_clues,
            "context_before": context_before,
            "context_after": context_after,
            "chapter_title": chapter_title,
            "processing_hints": {
                "has_quotes": any(
                    '"' in chunk_text or "'" in chunk_text
                    for pattern in self.dialogue_patterns
                    if re.search(pattern, chunk_text)
                ),
                "has_attribution": bool(attribution_clues),
                "complexity": self._assess_complexity(chunk_text),
                "priority": "high" if chunk_type == "dialogue" else "medium",
            },
        }

    def _classify_chunk_type(self, text: str) -> str:
        """Classify chunk as dialogue, narration, or mixed."""
        has_quotes = any(re.search(pattern, text) for pattern in self.dialogue_patterns)
        has_attribution = any(re.search(pattern, text, re.IGNORECASE) for pattern in self.attribution_patterns)
        has_narration = any(re.search(pattern, text, re.IGNORECASE) for pattern in self.narration_patterns)

        quote_ratio = len(re.findall(r'"[^"]*"', text)) / max(1, len(text.split()))

        if has_quotes and (has_attribution or quote_ratio > 0.1):
            if has_narration:
                return "mixed"
            return "dialogue"
        elif has_narration and not has_quotes:
            return "narration"
        else:
            return "mixed"

    def _get_context_before(self, sentences: list[str], current_index: int) -> str:
        """Get context sentences before current position."""
        start_idx = max(0, current_index - self.context_sentences)
        return " ".join(sentences[start_idx:current_index])

    def _get_context_after(self, sentences: list[str], current_index: int) -> str:
        """Get context sentences after current position."""
        end_idx = min(len(sentences), current_index + self.context_sentences)
        return " ".join(sentences[current_index:end_idx])

    def _extract_dialogue(self, text: str) -> str:
        """Extract dialogue quotes from text."""
        quotes = []
        for pattern in self.dialogue_patterns:
            quotes.extend(re.findall(pattern, text))
        return " ".join(quotes)

    def _find_attribution_clues(self, text: str) -> list[str]:
        """Find speaker attribution clues in text."""
        clues = []
        for pattern in self.attribution_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            clues.extend([" ".join(match) if isinstance(match, tuple) else match for match in matches])
        return list(set(clues))  # Remove duplicates

    def _assess_complexity(self, text: str) -> str:
        """Assess the complexity of the text for processing priority."""
        word_count = len(text.split())
        sentence_count = text.count(".") + text.count("!") + text.count("?")
        avg_sentence_length = word_count / max(1, sentence_count)

        if avg_sentence_length > 25 or word_count > 400:
            return "high"
        elif avg_sentence_length > 15 or word_count > 200:
            return "medium"
        else:
            return "low"
