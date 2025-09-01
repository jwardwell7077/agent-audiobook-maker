"""
ABM Dialogue Classifier - Agent 1 for Two-Agent Character System

This component analyzes utterances and classifies them as dialogue vs. narration
using hybrid detection: heuristics (90%) + Ollama AI fallback (10%).

Part of the two-agent character tracking system for voice casting profile building.
"""

import logging
import os
import re
from typing import Any, cast

import requests
from langflow.custom import Component
from langflow.io import BoolInput, DataInput, DropdownInput, FloatInput, IntInput, MessageTextInput, Output, StrInput
from langflow.schema import Data

logger = logging.getLogger(__name__)


class ABMDialogueClassifier(Component):
    display_name = "ABM Dialogue Classifier"
    description = "Agent 1: Classify utterances as dialogue vs. narration for character tracking"
    icon = "🤖"
    name = "ABMDialogueClassifier"

    inputs = [
        # New: Single-wire data input to avoid manual field mapping
        DataInput(
            name="utterance_data",
            display_name="Utterance Data",
            info=(
                "Full utterance payload (from ABMBlockIterator). If provided, this overrides individual "
                "text/context/id fields. Expected keys: utterance_text, book_id, chapter_id, utterance_idx, "
                "context_before, context_after."
            ),
            required=False,
        ),
        MessageTextInput(
            name="utterance_text",
            display_name="Utterance Text",
            info="The text utterance to classify",
            required=False,  # optional when using utterance_data
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
        BoolInput(
            name="disable_llm",
            display_name="Disable LLM Calls",
            info="Force heuristic-only behavior regardless of method",
            value=True,
        ),
        FloatInput(
            name="confidence_threshold",
            display_name="Confidence Threshold",
            info="Minimum confidence for heuristic classification (0.0-1.0)",
            value=0.8,
        ),
        DropdownInput(
            name="llm_provider",
            display_name="LLM Provider",
            info="Backend for LLM classification",
            options=["none", "ollama", "openai", "generic_http"],
            value="none",
        ),
        StrInput(
            name="openai_api_key",
            display_name="OpenAI API Key",
            info="Used when provider=openai (env OPENAI_API_KEY is also read)",
            value="",
        ),
        StrInput(
            name="openai_model",
            display_name="OpenAI Model",
            info="Model name for OpenAI provider",
            value="gpt-4o-mini",
        ),
        StrInput(
            name="generic_url",
            display_name="Generic HTTP URL",
            info="POST endpoint receiving {prompt} and returning {classification|text}",
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Classified Utterance", name="classified_utterance", method="classify_utterance"),
    ]

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        # Load configuration from environment
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.primary_model = os.getenv("OLLAMA_PRIMARY_MODEL", "llama3.2:3b")
        self.ai_timeout = int(os.getenv("AI_CLASSIFICATION_TIMEOUT", "30"))
        # Online providers
        self._openai_api_key_env = os.getenv("OPENAI_API_KEY", "")

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
        clues: list[str] = []

        for tag, pattern in self.attribution_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Normalize matches: can be str or tuple depending on groups
            normalized = []
            for m in matches:
                if isinstance(m, tuple):
                    normalized.append(f"{tag} {' '.join(m)}")
                else:
                    normalized.append(f"{tag} {m}")
            clues.extend(normalized)

        return clues

    def heuristic_classification(self, text: str) -> tuple[str, float, str, str | None, list[str]]:
        """
        Classify using heuristic rules.
        Returns: (classification, confidence, method, dialogue_text, attribution_clues)
        """
        text_lower = text.lower()

        # Check for dialogue patterns
        best_confidence: float = 0.0
        best_method = "heuristic_unknown"
        dialogue_text = None

        for pattern_name, pattern_info in self.dialogue_patterns.items():
            pinfo = cast(dict[str, Any], pattern_info)
            pattern_str: str = str(pinfo.get("pattern", ""))
            if re.search(pattern_str, text):
                conf_raw: Any = pinfo.get("confidence", 0.0)
                try:
                    conf_val: float = float(conf_raw) if conf_raw is not None else 0.0
                except (TypeError, ValueError):
                    conf_val = 0.0
                if conf_val > best_confidence:
                    best_confidence = conf_val
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
        """LLM-backed classification via provider switch: ollama, openai, or generic_http."""
        prompt = f"""Analyze this text and determine if it's dialogue or narration.

CONTEXT BEFORE: {context_before[:200]}...

TEXT TO ANALYZE: {text}

CONTEXT AFTER: {context_after[:200]}...

INSTRUCTIONS:
- Reply ONLY with "dialogue" or "narration"
- Dialogue includes: spoken words, thoughts, internal monologue
- Narration includes: descriptions, actions, scene-setting

Classification:"""
        provider = getattr(self, "llm_provider", "none")
        method_used = f"llm_{provider}"
        result_text: str | None = None

        try:
            if provider == "ollama":
                response = requests.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.primary_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "top_p": 0.1, "num_predict": 10},
                    },
                    timeout=self.ai_timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    result_text = (data.get("response") or "").strip()

            elif provider == "openai":
                api_key = getattr(self, "openai_api_key", "") or self._openai_api_key_env
                model = getattr(self, "openai_model", "gpt-4o-mini")
                if api_key:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    body = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Reply ONLY with dialogue or narration."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 5,
                    }
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=body,
                        headers=headers,
                        timeout=self.ai_timeout,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        result_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            elif provider == "generic_http":
                url = getattr(self, "generic_url", "")
                if url:
                    response = requests.post(url, json={"prompt": prompt}, timeout=self.ai_timeout)
                    if response.status_code == 200:
                        data = response.json()
                        result_text = (data.get("classification") or data.get("text") or "").strip()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"LLM provider error: {e}")

        if result_text:
            label = result_text.lower()
            label = "dialogue" if "dialogue" in label else ("narration" if "narration" in label else "unknown")
            return label, 0.65, method_used

        return "unknown", 0.5, method_used + "_uncertain"

    def classify_utterance(self) -> Data:
        """Main classification method."""
        try:
            # Prefer single-wire Data input when available
            payload: dict[str, Any] | None = None
            try:
                if hasattr(self, "utterance_data") and self.utterance_data:
                    if isinstance(self.utterance_data, Data):
                        # unwrap Data
                        if isinstance(self.utterance_data.data, dict):
                            payload = self.utterance_data.data
                    elif isinstance(self.utterance_data, dict):
                        payload = self.utterance_data
            except Exception:
                payload = None

            # Helper to pull value from payload with fallbacks
            def _get(key: str, default: Any = None) -> Any:
                if payload and isinstance(payload, dict):
                    # support alternative field names
                    if key in payload:
                        return payload.get(key, default)
                    # common alternates
                    alt_map = {
                        "utterance_text": ["text", "content", "chunk_text"],
                        "chapter_id": ["chapter", "chapterId"],
                        "book_id": ["book", "bookId"],
                        "utterance_idx": ["chunk_id", "index", "id"],
                        "context_before": ["prev", "before"],
                        "context_after": ["next", "after"],
                    }
                    for alt in alt_map.get(key, []):
                        if alt in payload:
                            return payload.get(alt, default)
                return default

            # Resolve inputs, preferring payload values
            text_val = _get("utterance_text", self.utterance_text)
            text = str(text_val) if text_val is not None else ""
            book_id_val = _get("book_id", self.book_id)
            book_id = str(book_id_val) if book_id_val else "UNKNOWN_BOOK"
            chapter_id_val = _get("chapter_id", self.chapter_id)
            chapter_id = str(chapter_id_val) if chapter_id_val else "chapter_00"
            utterance_idx_val = _get("utterance_idx", self.utterance_idx)
            try:
                utterance_idx = int(utterance_idx_val) if utterance_idx_val is not None else 0
            except (TypeError, ValueError):
                utterance_idx = 0
            cb = _get("context_before", self.context_before)
            context_before = str(cb) if cb is not None else ""
            ca = _get("context_after", self.context_after)
            context_after = str(ca) if ca is not None else ""
            method = self.classification_method
            threshold = self.confidence_threshold

            # Perform heuristic classification first
            classification, confidence, detection_method, dialogue_text, attribution_clues = (
                self.heuristic_classification(text)
            )

            # Use LLM enhancement if confidence is low or method requires it
            if (
                not getattr(self, "disable_llm", True)
                and method in ["llm_enhanced", "hybrid"]
                and confidence < threshold
            ):
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
