"""
ABM Dialogue Classifier - Agent 1 for Two-Agent Character System

This component analyzes utterances and classifies them as dialogue vs. narration
using hybrid detection: heuristics (90%) + Ollama AI fallback (10%).

Part of the two-agent character tracking system for voice casting profile building.
"""

import logging
import os
import re
import requests
from langflow.custom import Component
from langflow.io import DropdownInput, FloatInput, IntInput, MessageTextInput, Output
from langflow.schema import Data

logger = logging.getLogger(__name__)


class ABMDialogueClassifier(Component):
    display_name = "ABM Dialogue Classifier"
    description = "Agent 1: Classify utterances as dialogue vs. narration for character tracking"
    icon = "🤖"
    name = "ABMDialogueClassifier"

    inputs = [
        MessageTextInput(
            name="utterance_text",
            display_name="Utterance Text",
            info="The text utterance to classify",
            required=True,
        ),
        MessageTextInput(
            name="book_id",
            display_name="Book ID",
            info="Book identifier",
            value="",
        ),
        MessageTextInput(
            name="chapter_id",
            display_name="Chapter ID",
            info="Chapter identifier",
            value="",
        ),
        IntInput(
            name="utterance_idx",
            display_name="Utterance Index",
            info="0-based index of utterance in chapter",
            value=0,
        ),
        MessageTextInput(
            name="context_before",
            display_name="Context Before",
            info="Text preceding this utterance",
            value="",
        ),
        MessageTextInput(
            name="context_after",
            display_name="Context After",
            info="Text following this utterance",
            value="",
        ),
        DropdownInput(
            name="classification_method",
            display_name="Classification Method",
            info="Primary classification approach",
            options=["heuristic_only", "llm_enhanced", "hybrid"],
            value="hybrid",
        ),
        FloatInput(
            name="confidence_threshold",
            display_name="Confidence Threshold",
            info="Minimum confidence for heuristic classification (0.0-1.0)",
            value=0.8,
        ),
    ]

    outputs = [
        Output(display_name="Classified Utterance", name="classified_utterance", method="classify_utterance"),
    ]

    def __init__(self) -> None:
        super().__init__()
        # Load configuration from environment
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.primary_model = os.getenv("OLLAMA_PRIMARY_MODEL", "llama3.2:3b")
        self.ai_timeout = int(os.getenv("AI_CLASSIFICATION_TIMEOUT", "30"))

        self.dialogue_patterns = {
            # Quote patterns with varying confidence
            "standard_quotes": {
                "pattern": r'"[^"]*"',
                "confidence": 0.9,
            },
            "single_quotes": {
                "pattern": r"'[^']*'",
                "confidence": 0.7,
            },
            "smart_quotes": {
                "pattern": r'"[^"]*"',
                "confidence": 0.9,
            },
            "em_dash_dialogue": {
                "pattern": r"—[^—\n]*",
                "confidence": 0.6,
            },
        }

        self.dialogue_tags = [
            "said",
            "replied",
            "answered",
            "asked",
            "whispered",
            "shouted",
            "exclaimed",
            "muttered",
            "declared",
            "announced",
            "continued",
            "added",
            "interrupted",
            "agreed",
            "disagreed",
            "protested",
            "insisted",
            "demanded",
            "pleaded",
            "wondered",
            "thought",
        ]

        self.narration_indicators = [
            "he walked",
            "she walked",
            "they walked",
            "he looked",
            "she looked",
            "they looked",
            "he turned",
            "she turned",
            "they turned",
            "meanwhile",
            "later",
            "earlier",
            "suddenly",
            "the room",
            "the door",
            "the window",
        ]

        self.attribution_patterns = {
            "speaker_name": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # Full names
            "pronoun_said": r"\b(he|she|they|it)\s+(said|asked|replied|answered)\b",
            "said_pronoun": r"\bsaid\s+(he|she|they|it)\b",
            "character_titles": r"\b(Mr|Mrs|Ms|Dr|Professor|Captain|Sir|Lady)\s+[A-Z][a-z]+\b",
        }

    def extract_dialogue_text(self, text: str) -> str | None:
        """Extract the actual dialogue text from quotes."""
        # Try different quote patterns
        patterns = [
            r'"([^"]*)"',  # Standard double quotes
            r'"([^"]*)"',  # Smart quotes
            r"'([^']*)'",  # Single quotes
            r"—([^—\n]*)",  # Em dash dialogue
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def find_attribution_clues(self, text: str) -> list[str]:
        """Find speaker attribution clues using pattern matching."""
        clues = []

        for tag, pattern in self.attribution_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clues.append(f"{tag} {match}")

        return clues

    def heuristic_classification(self, text: str) -> tuple[str, float, str, str | None, list[str]]:
        """
        Classify using heuristic rules.
        Returns: (classification, confidence, method, dialogue_text, attribution_clues)
        """
        text_lower = text.lower()

        # Check for dialogue patterns
        best_confidence = 0.0
        best_method = "heuristic_unknown"
        dialogue_text = None

        for pattern_name, pattern_info in self.dialogue_patterns.items():
            if re.search(pattern_info["pattern"], text):
                if pattern_info["confidence"] > best_confidence:
                    best_confidence = pattern_info["confidence"]
                    best_method = f"heuristic_{pattern_name}"
                    dialogue_text = self.extract_dialogue_text(text)

        # Look for dialogue tags to boost confidence
        attribution_clues = self.find_attribution_clues(text)
        if attribution_clues and best_confidence > 0:
            best_confidence = min(0.95, best_confidence + 0.1)

        # Check for strong narration indicators
        narration_score = 0
        for indicator in self.narration_indicators:
            if indicator in text_lower:
                narration_score += 1

        # Make final classification
        if best_confidence > 0.5:
            if narration_score > 2:
                # Mixed content, lower confidence
                return "dialogue", best_confidence * 0.7, best_method, dialogue_text, attribution_clues
            else:
                return "dialogue", best_confidence, best_method, dialogue_text, attribution_clues
        elif narration_score > 0:
            return "narration", 0.7, "heuristic_narration_indicators", None, []
        else:
            return "unknown", 0.3, "heuristic_uncertain", None, []

    def llm_classification(self, text: str, context_before: str, context_after: str) -> tuple[str, float, str]:
        """
        Use Ollama AI for classification when heuristics are insufficient.
        Returns: (classification, confidence, method)
        """
        try:
            # Construct the AI prompt with context
            prompt = f"""Analyze this text and determine if it's dialogue or narration.

CONTEXT BEFORE: {context_before[:200]}...

TEXT TO ANALYZE: {text}

CONTEXT AFTER: {context_after[:200]}...

INSTRUCTIONS:
- Reply ONLY with "dialogue" or "narration"
- Dialogue includes: spoken words, thoughts, internal monologue
- Narration includes: descriptions, actions, scene-setting

Classification:"""

            # Make request to Ollama
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.primary_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent results
                        "top_p": 0.1,
                        "num_predict": 10,  # Short response expected
                    },
                },
                timeout=self.ai_timeout,
            )

            if response.status_code == 200:
                result = response.json()
                classification = result.get("response", "").strip().lower()

                # Validate and normalize the response
                if "dialogue" in classification:
                    return ("dialogue", 0.85, "ai_classification")
                elif "narration" in classification:
                    return ("narration", 0.85, "ai_classification")
                else:
                    # Fallback if AI response is unclear
                    return ("narration", 0.6, "ai_fallback_default")
            else:
                logging.warning(f"Ollama request failed: {response.status_code}")
                return ("narration", 0.5, "ai_error_default")

        except requests.exceptions.Timeout:
            logging.warning("Ollama request timed out")
            return ("narration", 0.5, "ai_timeout_default")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Ollama request error: {e}")
            return ("narration", 0.5, "ai_error_default")
        except Exception as e:
            logging.error(f"Unexpected error in AI classification: {e}")
            return ("narration", 0.5, "ai_error_default")

    def classify_utterance(self) -> Data:
        """Main classification method."""
        try:
            # Get inputs
            text = self.utterance_text
            book_id = self.book_id or "UNKNOWN_BOOK"
            chapter_id = self.chapter_id or "UNKNOWN_CHAPTER"
            utterance_idx = self.utterance_idx
            context_before = self.context_before or ""
            context_after = self.context_after or ""
            method = self.classification_method
            threshold = self.confidence_threshold

            # Perform heuristic classification first
            classification, confidence, detection_method, dialogue_text, attribution_clues = (
                self.heuristic_classification(text)
            )

            # Use LLM enhancement if confidence is low or method requires it
            if method in ["llm_enhanced", "hybrid"] and confidence < threshold:
                llm_class, llm_conf, llm_method = self.llm_classification(text, context_before, context_after)

                if method == "llm_enhanced":
                    classification = llm_class
                    confidence = llm_conf
                    detection_method = llm_method
                elif method == "hybrid":
                    # Combine heuristic and LLM results
                    if llm_conf > confidence:
                        classification = llm_class
                        confidence = (confidence + llm_conf) / 2
                        detection_method = f"{detection_method}+{llm_method}"

            # Build output data
            result = {
                "book_id": book_id,
                "chapter_id": chapter_id,
                "utterance_idx": utterance_idx,
                "text": text,
                "classification": classification,
                "confidence": confidence,
                "method": detection_method,
                "dialogue_text": dialogue_text,
                "attribution_clues": attribution_clues,
                "context_before": context_before,
                "context_after": context_after,
                "timestamp": self._get_timestamp(),
            }

            # Add metadata
            result["metadata"] = {
                "classification_method": method,
                "confidence_threshold": threshold,
                "agent": "dialogue_classifier",
                "version": "1.0.0",
            }

            logger.info(f"Classified utterance {utterance_idx} as {classification} (confidence: {confidence:.2f})")

            return Data(data=result)

        except Exception as e:
            logger.error(f"Error in dialogue classification: {str(e)}")
            # Return error result
            error_result: dict[str, object] = {
                "book_id": getattr(self, "book_id", "UNKNOWN"),
                "chapter_id": getattr(self, "chapter_id", "UNKNOWN"),
                "utterance_idx": getattr(self, "utterance_idx", -1),
                "text": getattr(self, "utterance_text", ""),
                "classification": "error",
                "confidence": 0.0,
                "method": "error",
                "dialogue_text": None,
                "attribution_clues": [],
                "error": str(e),
                "timestamp": self._get_timestamp(),
            }
            return Data(data=error_result)

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()
