from __future__ import annotations

import re

from langflow.custom import Component
from langflow.io import DataInput, IntInput, Output
from langflow.schema import Data


class ABMSegmentDialogueNarration(Component):
    """Split chapter text into dialogue/narration utterances."""

    display_name = "Segment Dialogue/Narration"
    description = "Enhanced segmentation into dialogue and narration."
    icon = "MaterialSymbolsLyrics"
    name = "abm_segment_dialogue_narration"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Payload with chapters from ChapterVolumeLoader.",
            required=True,
        ),
        IntInput(
            name="chapter_index",
            display_name="Chapter Index",
            value=0,
            info="Which chapter to segment (0-based index).",
        ),
    ]

    outputs = [
        Output(
            display_name="Segmented Payload",
            name="segmented_payload",
            method="segment"
        )
    ]

    def segment(self, payload: Data, chapter_index: int = 0) -> Data:
        """Enhanced dialogue segmentation with better quote detection."""
        data = payload.data if isinstance(payload, Data) else payload
        
        if not isinstance(data, dict):
            raise ValueError("Payload must be a dict-like Data object")
        
        chapters = data.get("chapters", [])
        if not chapters:
            self.status = "ERROR: No chapters found in payload"
            return Data(data={**data, "error": "No chapters found"})
            
        if chapter_index >= len(chapters):
            self.status = f"ERROR: Chapter index {chapter_index} out of range"
            return Data(data={**data, "error": "Chapter index out of range"})
        
        chapter = chapters[chapter_index]
        chapter_text = chapter.get("body_text", "")
        
        if not chapter_text:
            self.status = "ERROR: No body_text found in chapter"
            return Data(data={**data, "error": "No chapter text found"})
        
        # Enhanced segmentation algorithm
        utterances = self._enhanced_segment(
            chapter_text, chapter_index, chapter
        )
        
        # Create output payload
        output_data = dict(data)
        output_data["utterances"] = utterances
        output_data["selected_chapter"] = {
            "index": chapter_index,
            "title": chapter.get("title", f"Chapter {chapter_index}"),
            "utterance_count": len(utterances)
        }
        
        status_msg = (f"Segmented {len(utterances)} utterances "
                      f"from chapter {chapter_index}")
        self.status = status_msg
        return Data(data=output_data)
    
    def _enhanced_segment(
        self, text: str, chapter_idx: int, chapter: dict
    ) -> list:
        """Enhanced segmentation with improved dialogue detection."""
        utterances = []
        utterance_idx = 0
        
        # Split into paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        for para in paragraphs:
            # Check if paragraph contains dialogue
            has_quotes = bool(re.search(r'["""].*?["""]', para))
            
            if has_quotes:
                # Split paragraph into dialogue and narration parts
                parts = self._split_dialogue_paragraph(para)
                for part in parts:
                    if part['text'].strip():
                        utterances.append({
                            "utterance_idx": utterance_idx,
                            "chapter_idx": chapter_idx,
                            "chapter_title": chapter.get(
                                "title", f"Chapter {chapter_idx}"
                            ),
                            "text": part['text'].strip(),
                            "role": part['role'],
                            "paragraph_idx": len(utterances) // 10,
                        })
                        utterance_idx += 1
            else:
                # Pure narration paragraph
                if para.strip():
                    utterances.append({
                        "utterance_idx": utterance_idx,
                        "chapter_idx": chapter_idx,
                        "chapter_title": chapter.get(
                            "title", f"Chapter {chapter_idx}"
                        ),
                        "text": para.strip(),
                        "role": "narration",
                        "paragraph_idx": len(utterances) // 10,
                    })
                    utterance_idx += 1
        
        return utterances
    
    def _split_dialogue_paragraph(self, paragraph: str) -> list:
        """Split a paragraph containing dialogue into parts."""
        parts = []
        
        # Simple approach: find quoted sections
        quote_pattern = r'(["""])([^"""]*?)\1'
        last_end = 0
        
        for match in re.finditer(quote_pattern, paragraph):
            start, end = match.span()
            
            # Add narration before quote
            if start > last_end:
                before_text = paragraph[last_end:start].strip()
                if before_text:
                    parts.append({"text": before_text, "role": "narration"})
            
            # Add the dialogue
            quote_text = match.group(2)
            if quote_text.strip():
                parts.append({"text": quote_text.strip(), "role": "dialogue"})
            
            last_end = end
        
        # Add remaining narration after last quote
        if last_end < len(paragraph):
            after_text = paragraph[last_end:].strip()
            if after_text:
                parts.append({"text": after_text, "role": "narration"})
        
        # If no quotes found, treat as narration
        if not parts:
            parts.append({"text": paragraph, "role": "narration"})
        
        return parts
