"""ABM Dialogue Narration Classifier Component for LangFlow."""

from langflow.custom import Component
from langflow.io import DataInput, FloatInput, Output, StrInput
from langflow.schema import Data


class ABMDialogueNarrationClassifier(Component):
    display_name = "ABM Dialogue Narration Classifier"
    description = "Classify text segments as dialogue or narration using LLM or rule-based methods"
    icon = "message-circle"
    name = "ABMDialogueNarrationClassifier"

    inputs = [
        DataInput(
            name="chapters_data",
            display_name="Chapters Data",
            info="Data containing chapters to classify",
            required=True,
        ),
        StrInput(
            name="classification_method",
            display_name="Classification Method",
            info="Method to use: 'quotes', 'llm', 'hybrid'",
            value="quotes",
            options=["quotes", "llm", "hybrid"],
            required=True,
        ),
        StrInput(
            name="llm_model",
            display_name="LLM Model",
            info="LLM model to use if method is 'llm' or 'hybrid'",
            value="gpt-4o-mini",
            required=False,
        ),
        FloatInput(
            name="confidence_threshold",
            display_name="Confidence Threshold",
            info="Minimum confidence for LLM classification (0.0-1.0)",
            value=0.7,
            required=False,
        ),
    ]

    outputs = [
        Output(
            name="classified_data",
            display_name="Classified Data",
            method="classify_dialogue_narration",
        )
    ]

    def classify_dialogue_narration(self) -> Data:
        """Classify text segments as dialogue or narration."""
        try:
            input_data = self.chapters_data.data

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            chapters = input_data.get("chapters", [])
            if not chapters:
                self.status = "No chapters to classify"
                return Data(data=input_data)

            classified_chapters = []
            total_segments = 0
            dialogue_count = 0
            narration_count = 0

            for chapter in chapters:
                # Require paragraphs[] schema
                if not isinstance(chapter.get("paragraphs"), list):
                    continue
                paragraphs = [p for p in chapter.get("paragraphs") if isinstance(p, str) and p.strip()]

                chapter_segments = []

                for i, paragraph in enumerate(paragraphs):
                    if self.classification_method == "quotes":
                        classification = self._classify_by_quotes(paragraph)
                    elif self.classification_method == "llm":
                        classification = self._classify_by_llm(paragraph, paragraphs, i)
                    elif self.classification_method == "hybrid":
                        classification = self._classify_hybrid(paragraph, paragraphs, i)
                    else:
                        classification = {"type": "unknown", "confidence": 0.0, "method": "none"}

                    segment = {
                        "text": paragraph,
                        "type": classification["type"],
                        "confidence": classification["confidence"],
                        "method_used": classification["method"],
                        "paragraph_index": i,
                        "length": len(paragraph),
                        "has_quotes": '"' in paragraph,
                        "has_dialogue_tags": self._has_dialogue_tags(paragraph),
                    }

                    chapter_segments.append(segment)

                    if classification["type"] == "dialogue":
                        dialogue_count += 1
                    elif classification["type"] == "narration":
                        narration_count += 1

                classified_chapter = {
                    "chapter_index": chapter.get("index"),
                    "chapter_title": chapter.get("title"),
                    "segments": chapter_segments,
                    "total_segments": len(chapter_segments),
                    "dialogue_segments": len([s for s in chapter_segments if s["type"] == "dialogue"]),
                    "narration_segments": len([s for s in chapter_segments if s["type"] == "narration"]),
                }

                classified_chapters.append(classified_chapter)
                total_segments += len(chapter_segments)

            result_data = {
                "classified_chapters": classified_chapters,
                "total_chapters": len(classified_chapters),
                "total_segments": total_segments,
                "dialogue_segments": dialogue_count,
                "narration_segments": narration_count,
                "classification_method": self.classification_method,
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
            }

            status_msg = (
                f"Classified {total_segments} segments: "
                f"{dialogue_count} dialogue, {narration_count} narration "
                f"using {self.classification_method} method"
            )
            self.status = status_msg

            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to classify dialogue/narration: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def _classify_by_quotes(self, paragraph: str) -> dict:
        """Simple rule-based classification using quotation marks."""
        has_quotes = '"' in paragraph
        has_dialogue_tags = self._has_dialogue_tags(paragraph)

        if has_quotes:
            confidence = 0.9 if has_dialogue_tags else 0.7
            return {"type": "dialogue", "confidence": confidence, "method": "quotes"}
        else:
            return {"type": "narration", "confidence": 0.85, "method": "quotes"}

    def _classify_by_llm(self, paragraph: str, context: list, index: int) -> dict:
        """LLM-based classification with context."""
        # Placeholder for LLM integration
        # Would send paragraph + context to LLM for classification

        # Placeholder system prompt (not executed yet)
        # Classify this paragraph as either dialogue or narration and return a JSON structure.

        # For now, fallback to quote-based with lower confidence
        quote_result = self._classify_by_quotes(paragraph)
        return {
            "type": quote_result["type"],
            "confidence": quote_result["confidence"] * 0.8,  # Lower confidence for placeholder
            "method": "llm_placeholder",
        }

    def _classify_hybrid(self, paragraph: str, context: list, index: int) -> dict:
        """Hybrid approach: use quotes first, then LLM for ambiguous cases."""
        quote_result = self._classify_by_quotes(paragraph)

        # If quote-based classification is confident, use it
        if quote_result["confidence"] >= self.confidence_threshold:
            quote_result["method"] = "hybrid_quotes"
            return quote_result

        # Otherwise, use LLM for refinement
        llm_result = self._classify_by_llm(paragraph, context, index)
        llm_result["method"] = "hybrid_llm"
        return llm_result

    def _has_dialogue_tags(self, paragraph: str) -> bool:
        """Check if paragraph has dialogue attribution tags."""
        dialogue_tags = [
            "said",
            "asked",
            "replied",
            "shouted",
            "whispered",
            "exclaimed",
            "muttered",
            "called",
            "yelled",
            "continued",
            "added",
        ]
        return any(tag in paragraph.lower() for tag in dialogue_tags)
