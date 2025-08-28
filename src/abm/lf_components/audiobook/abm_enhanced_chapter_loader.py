"""ABM Enhanced Chapter Loader for End-to-End LangFlow Processing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import IntInput, Output, StrInput
from langflow.schema import Data


class ABMEnhancedChapterLoader(Component):
    display_name = "ABM Enhanced Chapter Loader"
    description = "Load chapter and emit one chunk per paragraph (block) with sentence context"
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
            name="context_sentences",
            display_name="Context Sentences",
            info="Number of sentences for context before/after",
            value=2,
            required=False,
        ),
        StrInput(
            name="base_data_dir",
            display_name="Data Directory Path",
            info="Path to data directory (relative or absolute)",
            value="data/clean",
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
                candidates = [chapters_path]
            else:
                base = Path(self.base_data_dir) / self.book_name
                candidates = [
                    base / "chapters.json",
                    base / "classified" / "chapters.json",
                    base / "classified" / "ex_chapters.json",
                ]

            chapters_path = next((p for p in candidates if p.exists()), None)
            if not chapters_path:
                tried = ", ".join(str(p) for p in candidates)
                error_msg = f"Chapters file not found. Tried: {tried}"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})

            with open(chapters_path, encoding="utf-8") as f:
                chapters_data = json.load(f)

            # Find target chapter, supporting both 1-based 'index' and 0-based 'chapter_index'
            target_chapter = None
            for chapter in chapters_data.get("chapters", []):
                idx = chapter.get("index")
                cidx = chapter.get("chapter_index")
                if idx == self.chapter_index or (isinstance(cidx, int) and cidx == self.chapter_index - 1):
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
            # paragraphs are authoritative; no need to join into chapter_text here

            # Paragraph/block-based chunking (only mode)
            chunks = self._chunks_from_paragraphs(
                paragraphs, target_chapter.get("title", f"Chapter {self.chapter_index}")
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

            self.status = (
                f"Loaded {len(paragraphs)} paragraphs and created {len(chunks)} chunks from {target_chapter['title']}"
            )
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to load and chunk chapter: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def _chunks_from_paragraphs(self, paragraphs: list[str], chapter_title: str) -> list[dict[str, Any]]:
        """Create one chunk per paragraph, with sentence-based context windows.

        - Uses the chapter's flattened sentence list to compute context_before/after
          around each paragraph boundary.
        - Preserves paragraph boundaries as chunk boundaries.
        """
        # Build sentence lists per paragraph and a flattened chapter sentence list
        sentences_by_par: list[list[str]] = [self._split_into_sentences(p or "") for p in paragraphs]
        all_sentences: list[str] = [s for plist in sentences_by_par for s in plist]

        chunks: list[dict[str, Any]] = []
        chunk_id = 1

        # Track running sentence offset to locate paragraph position in chapter
        offset = 0
        for plist, paragraph_text in zip(sentences_by_par, paragraphs, strict=True):
            # Current index is end of paragraph in flattened sentence list
            current_index = offset + len(plist)

            # Reuse existing chunk builder to compute metadata and context
            # Provide the paragraph's sentences as the current_chunk parameter
            chunk = self._create_chunk(
                (paragraph_text or "").strip(),
                chunk_id,
                all_sentences,
                current_index,
                plist,
                chapter_title,
            )
            chunks.append(chunk)
            chunk_id += 1
            offset = current_index

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
