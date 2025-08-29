"""ABM Speaker Attribution - Agent 2 for Two-Agent Character System.

Heuristic speaker attribution using local context and dialogue tags. Designed as a
lightweight, dependency-free fallback that works without LLMs. It consumes the
output of ABMDialogueClassifier and enriches it with a best-effort speaker guess
plus a confidence score and reasoning string.
"""

from __future__ import annotations

import re
from typing import Any

from langflow.custom import Component
from langflow.io import DataInput, FloatInput, Output
from langflow.schema import Data


class ABMSpeakerAttribution(Component):
    display_name = "ABM Speaker Attribution"
    description = "Agent 2: Attribute dialogue to likely speaker using heuristics"
    icon = "user"
    name = "ABMSpeakerAttribution"

    inputs = [
        DataInput(
            name="classified_utterance",
            display_name="Classified Utterance",
            info="Output from Agent 1 (Dialogue Classifier)",
            required=True,
        ),
        FloatInput(
            name="base_confidence",
            display_name="Base Confidence",
            info="Baseline confidence when a speaker is found via tags",
            value=0.75,
            required=False,
        ),
        FloatInput(
            name="unknown_confidence",
            display_name="Unknown Confidence",
            info="Confidence to use when no clear speaker found",
            value=0.35,
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Attributed Utterance",
            name="attributed_utterance",
            method="attribute_speaker",
        ),
    ]

    def attribute_speaker(self) -> Data:
        """Attribute speaker for a single classified utterance using heuristics."""
        try:
            payload = self.classified_utterance.data

            # Pass-through errors
            if "error" in payload:
                self.status = "Input contains error, passing through"
                return Data(data=payload)

            classification = (payload.get("classification") or "").lower()

            # If not dialogue, return with unknown speaker
            if classification != "dialogue":
                result = self._build_result(payload, None, self.unknown_confidence, method="heuristic_non_dialogue")
                self.status = "Non-dialogue: attribution skipped"
                return Data(data=result)

            # Try multiple sources for attribution: dialogue_text first, then full text + context
            dialogue_text = payload.get("dialogue_text") or payload.get("text") or ""
            context_before = payload.get("context_before", "")
            context_after = payload.get("context_after", "")

            # 1) Look for explicit tags in the same utterance (e.g., "...", Quinn said)
            speaker = self._extract_speaker_from_tags(dialogue_text)
            method = "heuristic_dialogue_tag"

            # 2) If not found, search in combined context
            if not speaker:
                combined = f"{dialogue_text} {context_after} {context_before}"
                speaker = self._extract_speaker_from_tags(combined)
                method = "heuristic_context_tag" if speaker else method

            # 3) If still not found, try simple proper-noun proximity before/after quotes
            if not speaker:
                speaker = self._extract_near_quotes(payload.get("text", ""))
                method = "heuristic_quote_proximity" if speaker else method

            # Confidence and reasoning
            if speaker:
                confidence = float(self.base_confidence)
                reasoning = "Speaker inferred from dialogue tags / nearby context"
            else:
                confidence = float(self.unknown_confidence)
                reasoning = "No reliable dialogue tags found; defaulting to unknown"

            result = self._build_result(payload, speaker, confidence, method=method, reasoning=reasoning)
            self.status = f"Attributed speaker: {speaker or 'Unknown'} (conf {confidence:.2f})"
            return Data(data=result)

        except Exception as e:  # pragma: no cover - defensive
            self.status = f"Error: {e}"
            return Data(data={"error": str(e)})

    # --- Heuristics -----------------------------------------------------
    _TAG_PATTERNS = [
        # "...", Quinn said / Quinn replied / Quinn asked
        r'"[^\"]*"\s*,?\s*([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|exclaimed)\b',
        # said Quinn / asked Quinn
        r"(?:said|asked|replied|whispered|shouted|exclaimed)\s+([A-Z][a-z]+)\b",
        # Quinn said / Quinn asked (without preceding quotes)
        r"\b([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|exclaimed)\b",
    ]

    def _extract_speaker_from_tags(self, text: str) -> str | None:
        for pat in self._TAG_PATTERNS:
            m = re.search(pat, text)
            if m:
                return m.group(1)
        return None

    def _extract_near_quotes(self, text: str) -> str | None:
        """Look for a Proper Noun near quotes within a small window."""
        # Find quotes spans
        for q in re.finditer(r'"[^\"]*"', text):
            span_start, span_end = q.span()
            window = text[max(0, span_start - 60) : min(len(text), span_end + 60)]
            m = re.search(r"\b([A-Z][a-z]{2,})\b", window)
            if m:
                return m.group(1)
        return None

    # --- Result shaping -------------------------------------------------
    def _build_result(
        self,
        src: dict[str, Any],
        speaker: str | None,
        confidence: float,
        *,
        method: str,
        reasoning: str | None = None,
    ) -> dict[str, Any]:
        """Create standardized attribution result expected by the aggregator."""
        # Provide stable narrator fallback for non-dialogue
        classification = (src.get("classification") or src.get("original_classification") or "").lower()
        if not speaker and classification == "narration":
            character_name = "Narrator"
            character_id = "narrator"
        else:
            character_name = speaker or "Unknown"
            character_id = (speaker or "unknown").lower()

        return {
            # Identification
            "book_id": src.get("book_id", ""),
            "chapter_id": src.get("chapter_id", ""),
            "utterance_idx": src.get("utterance_idx", 0),
            # Content
            "dialogue_text": src.get("dialogue_text") or src.get("utterance_text", ""),
            "full_text": src.get("utterance_text", ""),
            "original_classification": src.get("classification", "unknown"),
            # Speaker
            "character_id": character_id if speaker else None,
            "character_name": character_name,
            "speaker_attribution": {
                "confidence": float(confidence),
                "method": method,
                "reasoning": reasoning or "",
            },
            # Context
            "context_before": src.get("context_before", ""),
            "context_after": src.get("context_after", ""),
            # Optional extras (placeholders for downstream tools)
            "speech_patterns": {},
            "processing_info": {
                "source_component": "ABMSpeakerAttribution",
                "pipeline_agent": 2,
            },
        }
