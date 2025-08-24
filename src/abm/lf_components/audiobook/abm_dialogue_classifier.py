"""
ABM Dialogue Classifier - Agent 1 for Two-Agent Character System

This component analyzes utterances and classifies them as dialogue vs. narration
using multiple detection strategies including heuristics and LLM classification.

Part of the two-agent character tracking system for voice casting profile building.
"""

from langflow.custom import Component
from langflow.io import MessageTextInput, Output, DropdownInput, IntInput, FloatInput
from langflow.schema import Data
import re
from typing import Optional, List, Tuple
import logging

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
            info="Minimum confidence for heuristic classification",
            value=0.8,
            range_spec={"min": 0.0, "max": 1.0, "step": 0.1},
        ),
    ]

    outputs = [
        Output(display_name="Classified Utterance", name="classified_utterance", method="classify_utterance"),
    ]

    def __init__(self):
        super().__init__()
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
                "pattern": r'—[^—\n]*',
                "confidence": 0.6,
            },
        }
        
        self.dialogue_tags = [
            "said", "replied", "answered", "asked", "whispered", "shouted",
            "exclaimed", "muttered", "declared", "announced", "continued",
            "added", "interrupted", "agreed", "disagreed", "protested",
            "insisted", "demanded", "pleaded", "wondered", "thought"
        ]

        self.narration_indicators = [
            "he walked", "she walked", "they walked",
            "he looked", "she looked", "they looked",
            "he turned", "she turned", "they turned",
            "meanwhile", "later", "earlier", "suddenly",
            "the room", "the door", "the window"
        ]

    def extract_dialogue_text(self, text: str) -> Optional[str]:
        """Extract the actual dialogue text from quotes."""
        # Try different quote patterns
        patterns = [
            r'"([^"]*)"',  # Standard double quotes
            r'"([^"]*)"',  # Smart quotes
            r"'([^']*)'",  # Single quotes
            r'—([^—\n]*)',  # Em dash dialogue
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def find_attribution_clues(self, text: str) -> List[str]:
        """Find dialogue attribution clues in the text."""
        clues = []
        text_lower = text.lower()
        
        # Look for dialogue tags with names
        for tag in self.dialogue_tags:
            pattern = rf'\b{tag}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clues.append(f"{tag} {match}")
                
        # Look for name + dialogue tags
        name_tag_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(' + '|'.join(self.dialogue_tags) + r')\b'
        matches = re.findall(name_tag_pattern, text, re.IGNORECASE)
        for name, tag in matches:
            clues.append(f"{name} {tag}")
            
        return clues

    def heuristic_classification(self, text: str) -> Tuple[str, float, str, Optional[str], List[str]]:
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

    def llm_classification(self, text: str, context_before: str, context_after: str) -> Tuple[str, float, str]:
        """
        Use LLM for classification when heuristics are uncertain.
        For now, returns a placeholder - would integrate with actual LLM in production.
        """
        # TODO: Implement actual LLM classification
        # This would use a model like Claude/GPT to classify ambiguous cases
        
        # Placeholder implementation
        if len(text) > 50 and any(char in text for char in ['"', "'", '"']):
            return "dialogue", 0.8, "llm_enhanced"
        else:
            return "narration", 0.8, "llm_enhanced"

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
            classification, confidence, detection_method, dialogue_text, attribution_clues = self.heuristic_classification(text)
            
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
                "version": "1.0.0"
            }
            
            logger.info(f"Classified utterance {utterance_idx} as {classification} (confidence: {confidence:.2f})")
            
            return Data(value=result)
            
        except Exception as e:
            logger.error(f"Error in dialogue classification: {str(e)}")
            # Return error result
            error_result = {
                "book_id": getattr(self, 'book_id', 'UNKNOWN'),
                "chapter_id": getattr(self, 'chapter_id', 'UNKNOWN'), 
                "utterance_idx": getattr(self, 'utterance_idx', -1),
                "text": getattr(self, 'utterance_text', ''),
                "classification": "error",
                "confidence": 0.0,
                "method": "error",
                "dialogue_text": None,
                "attribution_clues": [],
                "error": str(e),
                "timestamp": self._get_timestamp(),
            }
            return Data(value=error_result)

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
