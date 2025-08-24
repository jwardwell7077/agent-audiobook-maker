"""
ABM Speaker Attribution - Agent 2 for Two-Agent Character System

This component identifies speakers in dialogue utterances and builds character voice profiles
using multi-method attribution: direct, contextual, and conversation flow analysis.

Part of the two-agent character tracking system for voice casting profile building.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from langflow.custom import Component
from langflow.io import DropdownInput, FloatInput, BoolInput, MessageTextInput, Output
from langflow.schema import Data

logger = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """Result of speaker attribution analysis"""

    character_id: Optional[str]
    character_name: Optional[str]
    attribution_method: str  # direct, contextual, inferred, unknown
    confidence: float
    speech_patterns: Dict[str, Any]
    voice_characteristics: Dict[str, Any]
    processing_metadata: Dict[str, Any]


@dataclass
class CharacterProfile:
    """Character voice profile data"""

    character_id: str
    canonical_name: str
    name_variations: List[str]
    speech_patterns: Dict[str, Any]
    voice_characteristics: Dict[str, Any]
    dialogue_samples: List[str]
    utterance_count: int
    first_appearance: Optional[str]
    last_appearance: Optional[str]


class ABMSpeakerAttribution(Component):
    display_name = "ABM Speaker Attribution"
    description = "Agent 2: Identify speakers in dialogue and build character voice profiles"
    icon = "🎭"
    name = "ABMSpeakerAttribution"

    inputs = [
        MessageTextInput(
            name="classified_utterance",
            display_name="Classified Utterance",
            info="Output from Agent 1 (ABM Dialogue Classifier)",
            required=True,
        ),
        MessageTextInput(
            name="dialogue_text",
            display_name="Dialogue Text",
            info="The actual dialogue text to analyze",
            value="",
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
        MessageTextInput(
            name="context_before",
            display_name="Context Before",
            info="Text context before the utterance",
            value="",
        ),
        MessageTextInput(
            name="context_after",
            display_name="Context After",
            info="Text context after the utterance",
            value="",
        ),
        DropdownInput(
            name="attribution_method",
            display_name="Attribution Method",
            options=["all", "direct_only", "contextual_only", "flow_only"],
            value="all",
            info="Which attribution methods to use",
        ),
        FloatInput(
            name="min_confidence",
            display_name="Minimum Confidence",
            value=0.3,
            info="Minimum confidence threshold for attribution (0.0-1.0)",
        ),
        BoolInput(
            name="create_new_characters",
            display_name="Create New Characters",
            value=True,
            info="Allow creation of new character profiles",
        ),
        BoolInput(
            name="update_profiles",
            display_name="Update Profiles",
            value=True,
            info="Enable character profile updates",
        ),
    ]

    outputs = [
        Output(display_name="Speaker Attribution", name="speaker_attribution", method="attribute_speaker"),
    ]

    def __init__(self):
        super().__init__()
        self.character_cache: Dict[str, CharacterProfile] = {}
        self.conversation_history: List[Tuple[str, str]] = []  # (character_id, dialogue)

        # Attribution patterns
        self.direct_patterns = [
            # "John said" patterns
            r"([A-Z][a-zA-Z\s]+?)\s+(?:said|replied|asked|shouted|whispered|called|announced|declared|exclaimed)",
            # "said John" patterns
            (
                r"(?:said|replied|asked|shouted|whispered|called|announced|declared|exclaimed)\s+"
                r"([A-Z][a-zA-Z\s]+?)[\.,\?!]"
            ),
            # Character titles
            r"((?:Dr|Mr|Mrs|Ms|Professor|Captain|Sir|Lady|Lord)\.\s+[A-Z][a-zA-Z]+)",
        ]

        self.speech_verbs = [
            "said",
            "replied",
            "asked",
            "shouted",
            "whispered",
            "called",
            "announced",
            "declared",
            "exclaimed",
            "muttered",
            "gasped",
            "stammered",
            "yelled",
            "screamed",
            "chuckled",
            "laughed",
        ]

    def attribute_speaker(self) -> Data:
        """Main speaker attribution workflow"""
        try:
            # Parse input from Agent 1
            utterance_data = self._parse_agent1_input()

            # Validation Gate
            if not self._validate_input(utterance_data):
                return self._create_skip_output("Invalid input or non-dialogue")

            # Character Database Lookup
            chapter_characters = self._load_chapter_characters(
                utterance_data.get("book_id", ""), utterance_data.get("chapter_id", "")
            )

            # Attribution Analysis - Multi-Method Speaker Detection
            attribution_result = self._analyze_attribution(utterance_data, chapter_characters)

            # Character Management
            character_profile = self._manage_character(attribution_result, utterance_data)

            # Profile Building
            if self.update_profiles and character_profile:
                self._build_character_profile(character_profile, utterance_data)

            # Generate structured output
            output_data = self._generate_output(attribution_result, character_profile, utterance_data)

            return Data(
                data={
                    "speaker_attribution": output_data,
                    "success": True,
                    "agent": "abm_speaker_attribution",
                    "version": "1.0.0",
                }
            )

        except Exception as e:
            logger.error(f"Speaker attribution error: {e}")
            return self._create_error_output(str(e))

    def _parse_agent1_input(self) -> Dict[str, Any]:
        """Parse input from Agent 1"""
        try:
            # If classified_utterance is JSON, parse it
            if self.classified_utterance.startswith("{"):
                agent1_data = json.loads(self.classified_utterance)
            else:
                # Handle plain text input
                agent1_data = {"text": self.classified_utterance}

            return {
                "agent1_output": agent1_data,
                "dialogue_text": self.dialogue_text or agent1_data.get("text", ""),
                "book_id": self.book_id,
                "chapter_id": self.chapter_id,
                "context_before": self.context_before,
                "context_after": self.context_after,
                "utterance_type": agent1_data.get("classification", "unknown"),
            }
        except json.JSONDecodeError:
            # Fallback for non-JSON input
            return {
                "agent1_output": {"text": self.classified_utterance},
                "dialogue_text": self.dialogue_text or self.classified_utterance,
                "book_id": self.book_id,
                "chapter_id": self.chapter_id,
                "context_before": self.context_before,
                "context_after": self.context_after,
                "utterance_type": "dialogue",
            }

    def _validate_input(self, utterance_data: Dict[str, Any]) -> bool:
        """Validation Gate - check if processing should continue"""
        # Check if it's dialogue
        utterance_type = utterance_data.get("utterance_type", "").lower()
        if utterance_type not in ["dialogue", "dialog", "speech"]:
            logger.info(f"Skipping non-dialogue utterance: {utterance_type}")
            return False

        # Check if we have dialogue text
        dialogue_text = utterance_data.get("dialogue_text", "").strip()
        if not dialogue_text:
            logger.info("No dialogue text provided")
            return False

        return True

    def _load_chapter_characters(self, book_id: str, chapter_id: str) -> Dict[str, CharacterProfile]:
        """Character Database Lookup - load existing characters for this chapter"""
        # TODO: Replace with actual database queries
        # For now, use in-memory cache

        cache_key = f"{book_id}_{chapter_id}"
        if cache_key in self.character_cache:
            return self.character_cache[cache_key]

        # Mock character data - in production this would be database queries
        characters = {}

        # Store in cache
        self.character_cache[cache_key] = characters
        return characters

    def _analyze_attribution(
        self, utterance_data: Dict[str, Any], chapter_characters: Dict[str, CharacterProfile]
    ) -> AttributionResult:
        """Attribution Analysis - Multi-Method Speaker Detection"""

        dialogue_text = utterance_data["dialogue_text"]
        context_before = utterance_data.get("context_before", "")
        context_after = utterance_data.get("context_after", "")

        attribution_methods = []
        if self.attribution_method in ["all", "direct_only"]:
            attribution_methods.append("direct")
        if self.attribution_method in ["all", "contextual_only"]:
            attribution_methods.append("contextual")
        if self.attribution_method in ["all", "flow_only"]:
            attribution_methods.append("flow")

        # Try direct attribution first (highest confidence)
        if "direct" in attribution_methods:
            result = self._direct_attribution(dialogue_text, context_before + context_after)
            if result and result.confidence >= 0.9:
                logger.info(f"Direct attribution found: {result.character_name} (confidence: {result.confidence})")
                return result

        # Try contextual attribution
        if "contextual" in attribution_methods:
            result = self._contextual_attribution(dialogue_text, context_before, context_after)
            if result and result.confidence >= 0.7:
                logger.info(f"Contextual attribution found: {result.character_name} (confidence: {result.confidence})")
                return result

        # Try conversation flow inference
        if "flow" in attribution_methods:
            result = self._conversation_flow_attribution(dialogue_text)
            if result and result.confidence >= 0.4:
                logger.info(f"Flow attribution found: {result.character_name} (confidence: {result.confidence})")
                return result

        # Unknown speaker
        logger.info("No clear speaker attribution found")
        return AttributionResult(
            character_id=None,
            character_name="Unknown Speaker",
            attribution_method="unknown",
            confidence=0.3,
            speech_patterns={},
            voice_characteristics={},
            processing_metadata={"reason": "no_attribution_clues"},
        )

    def _direct_attribution(self, dialogue_text: str, context: str) -> Optional[AttributionResult]:
        """Direct Attribution - look for explicit speaker indicators"""

        # Clean and combine text for analysis
        full_text = context + " " + dialogue_text

        # Try each direct pattern
        for pattern in self.direct_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                character_name = match.group(1).strip()

                # Clean up the character name
                character_name = self._clean_character_name(character_name)
                if not character_name:
                    continue

                # Extract speech patterns from direct attribution
                speech_patterns = self._extract_speech_patterns(dialogue_text)
                voice_characteristics = self._analyze_voice_characteristics(dialogue_text, character_name)

                return AttributionResult(
                    character_id=self._generate_character_id(character_name),
                    character_name=character_name,
                    attribution_method="direct",
                    confidence=0.95,
                    speech_patterns=speech_patterns,
                    voice_characteristics=voice_characteristics,
                    processing_metadata={"pattern_matched": pattern, "match_text": match.group(0)},
                )

        return None

    def _contextual_attribution(
        self, dialogue_text: str, context_before: str, context_after: str
    ) -> Optional[AttributionResult]:
        """Contextual Analysis - look for character mentions in surrounding context"""

        # Look for character names in context
        context_text = context_before + " " + context_after

        # Pattern for character names (capitalized words)
        name_pattern = r"\b([A-Z][a-zA-Z]{2,})\b"
        potential_names = re.findall(name_pattern, context_text)

        if not potential_names:
            return None

        # Score each potential name based on proximity and context
        best_name = None
        best_score = 0.0

        for name in set(potential_names):  # Remove duplicates
            score = self._score_contextual_name(name, context_before, context_after, dialogue_text)
            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score > 0.7:
            speech_patterns = self._extract_speech_patterns(dialogue_text)
            voice_characteristics = self._analyze_voice_characteristics(dialogue_text, best_name)

            return AttributionResult(
                character_id=self._generate_character_id(best_name),
                character_name=best_name,
                attribution_method="contextual",
                confidence=best_score,
                speech_patterns=speech_patterns,
                voice_characteristics=voice_characteristics,
                processing_metadata={"context_analysis": True, "candidates": potential_names},
            )

        return None

    def _conversation_flow_attribution(self, dialogue_text: str) -> Optional[AttributionResult]:
        """Conversation Flow - use turn-taking patterns to infer speaker"""

        if len(self.conversation_history) < 1:
            return None

        # Get the last speaker
        last_speaker_id, _ = self.conversation_history[-1]

        # Look for patterns indicating turn-taking
        if self._is_response_pattern(dialogue_text):
            # This appears to be a response, likely different speaker
            confidence = 0.6
            method_info = {"turn_taking": True, "last_speaker": last_speaker_id}
        else:
            # Might be same speaker continuing
            confidence = 0.4
            method_info = {"continuation": True, "last_speaker": last_speaker_id}

        # For flow attribution, we create a temporary ID
        inferred_character_id = f"flow_inferred_{len(self.conversation_history)}"

        speech_patterns = self._extract_speech_patterns(dialogue_text)

        return AttributionResult(
            character_id=inferred_character_id,
            character_name=f"Speaker {len(self.conversation_history) + 1}",
            attribution_method="inferred",
            confidence=confidence,
            speech_patterns=speech_patterns,
            voice_characteristics={},
            processing_metadata=method_info,
        )

    def _manage_character(
        self, attribution_result: AttributionResult, utterance_data: Dict[str, Any]
    ) -> Optional[CharacterProfile]:
        """Character Management - create new or update existing character"""

        if not attribution_result.character_id:
            return None

        character_id = attribution_result.character_id

        # Check if character exists
        existing_character = self._find_character_by_id(character_id)

        if existing_character:
            # Update existing character
            logger.info(f"Updating existing character: {existing_character.canonical_name}")
            return self._update_character(existing_character, attribution_result, utterance_data)
        elif self.create_new_characters:
            # Create new character
            logger.info(f"Creating new character: {attribution_result.character_name}")
            return self._create_new_character(attribution_result, utterance_data)
        else:
            logger.info(f"New character creation disabled for: {attribution_result.character_name}")
            return None

    def _build_character_profile(self, character_profile: CharacterProfile, utterance_data: Dict[str, Any]) -> None:
        """Profile Building - enhance character voice characteristics"""

        dialogue_text = utterance_data["dialogue_text"]

        # Speech Pattern Analysis
        new_patterns = self._extract_speech_patterns(dialogue_text)
        self._merge_speech_patterns(character_profile.speech_patterns, new_patterns)

        # Voice Characteristics Analysis
        new_characteristics = self._analyze_voice_characteristics(dialogue_text, character_profile.canonical_name)
        self._merge_voice_characteristics(character_profile.voice_characteristics, new_characteristics)

        # Add dialogue sample
        if dialogue_text not in character_profile.dialogue_samples:
            character_profile.dialogue_samples.append(dialogue_text)
            # Keep only recent samples
            if len(character_profile.dialogue_samples) > 20:
                character_profile.dialogue_samples = character_profile.dialogue_samples[-20:]

        # Update counts
        character_profile.utterance_count += 1

    def _extract_speech_patterns(self, dialogue_text: str) -> Dict[str, Any]:
        """Extract speech patterns from dialogue"""

        patterns = {
            "formality_level": self._detect_formality(dialogue_text),
            "sentence_length": len(dialogue_text.split()),
            "question_count": dialogue_text.count("?"),
            "exclamation_count": dialogue_text.count("!"),
            "common_words": self._extract_common_words(dialogue_text),
            "contraction_usage": self._count_contractions(dialogue_text),
        }

        return patterns

    def _analyze_voice_characteristics(self, dialogue_text: str, character_name: str) -> Dict[str, Any]:
        """Analyze voice characteristics for casting"""

        characteristics = {
            "estimated_age": self._estimate_age_from_speech(dialogue_text),
            "estimated_gender": self._estimate_gender(character_name, dialogue_text),
            "social_class_indicators": self._detect_social_class(dialogue_text),
            "regional_markers": self._detect_regional_markers(dialogue_text),
            "personality_traits": self._detect_personality_traits(dialogue_text),
            "emotional_range": self._analyze_emotional_indicators(dialogue_text),
        }

        return characteristics

    def _generate_output(
        self,
        attribution_result: AttributionResult,
        character_profile: Optional[CharacterProfile],
        utterance_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate structured output"""

        output = {
            "character_id": attribution_result.character_id,
            "character_name": attribution_result.character_name,
            "attribution_method": attribution_result.attribution_method,
            "confidence": attribution_result.confidence,
            "dialogue_text": utterance_data["dialogue_text"],
            "speech_patterns": attribution_result.speech_patterns,
            "voice_characteristics": attribution_result.voice_characteristics,
            "processing_metadata": {
                **attribution_result.processing_metadata,
                "book_id": utterance_data.get("book_id", ""),
                "chapter_id": utterance_data.get("chapter_id", ""),
                "processing_timestamp": self._get_timestamp(),
                "agent_version": "2.0.0",
            },
        }

        # Add character profile data if available
        if character_profile:
            output["character_profile"] = {
                "canonical_name": character_profile.canonical_name,
                "name_variations": character_profile.name_variations,
                "utterance_count": character_profile.utterance_count,
                "dialogue_samples_count": len(character_profile.dialogue_samples),
            }

        # Update conversation history
        if attribution_result.character_id:
            self.conversation_history.append((attribution_result.character_id, utterance_data["dialogue_text"]))
            # Keep recent history
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

        return output

    # Helper methods
    def _clean_character_name(self, name: str) -> str:
        """Clean and normalize character name"""
        # Remove common words that aren't names
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "he",
            "she",
            "it",
            "they",
        }
        words = name.split()
        clean_words = [w for w in words if w.lower() not in stopwords and len(w) > 1]
        return " ".join(clean_words).strip()

    def _generate_character_id(self, character_name: str) -> str:
        """Generate a unique character ID"""
        # Use a hash of the name for consistency
        import hashlib

        name_hash = hashlib.md5(character_name.lower().encode()).hexdigest()[:8]
        return f"char_{name_hash}"

    def _score_contextual_name(self, name: str, context_before: str, context_after: str, dialogue_text: str) -> float:
        """Score a potential character name based on context"""
        score = 0.0

        # Check proximity to dialogue
        before_distance = len(context_before.split()) if context_before else 999
        after_distance = len(context_after.split()) if context_after else 999
        min_distance = min(before_distance, after_distance)

        # Closer = higher score
        if min_distance <= 5:
            score += 0.8
        elif min_distance <= 10:
            score += 0.6
        elif min_distance <= 20:
            score += 0.4

        # Check for action words near the name
        action_words = ["walked", "said", "looked", "turned", "stood", "sat", "moved", "came", "went"]
        full_context = context_before + " " + context_after
        for action in action_words:
            if action in full_context.lower() and name in full_context:
                score += 0.2
                break

        return min(score, 1.0)

    def _is_response_pattern(self, dialogue_text: str) -> bool:
        """Check if dialogue appears to be a response"""
        response_indicators = [
            dialogue_text.strip().lower().startswith(("yes", "no", "maybe", "well", "oh", "ah", "hmm")),
            "?" in dialogue_text,  # Questions often get responses
            dialogue_text.strip().endswith("?"),  # This is a question
        ]
        return any(response_indicators)

    def _find_character_by_id(self, character_id: str) -> Optional[CharacterProfile]:
        """Find character in cache by ID"""
        # Search through all cached characters
        for characters in self.character_cache.values():
            if character_id in characters:
                return characters[character_id]
        return None

    def _create_new_character(
        self, attribution_result: AttributionResult, utterance_data: Dict[str, Any]
    ) -> CharacterProfile:
        """Create new character profile"""
        character_profile = CharacterProfile(
            character_id=attribution_result.character_id,
            canonical_name=attribution_result.character_name,
            name_variations=[attribution_result.character_name],
            speech_patterns=attribution_result.speech_patterns,
            voice_characteristics=attribution_result.voice_characteristics,
            dialogue_samples=[utterance_data["dialogue_text"]],
            utterance_count=1,
            first_appearance=f"{utterance_data.get('book_id', '')}_{utterance_data.get('chapter_id', '')}",
            last_appearance=f"{utterance_data.get('book_id', '')}_{utterance_data.get('chapter_id', '')}",
        )

        # Add to cache
        cache_key = f"{utterance_data.get('book_id', '')}_{utterance_data.get('chapter_id', '')}"
        if cache_key not in self.character_cache:
            self.character_cache[cache_key] = {}
        self.character_cache[cache_key][attribution_result.character_id] = character_profile

        return character_profile

    def _update_character(
        self, character_profile: CharacterProfile, attribution_result: AttributionResult, utterance_data: Dict[str, Any]
    ) -> CharacterProfile:
        """Update existing character profile"""

        # Update last appearance
        character_profile.last_appearance = (
            f"{utterance_data.get('book_id', '')}_{utterance_data.get('chapter_id', '')}"
        )

        # Add name variation if new
        if attribution_result.character_name not in character_profile.name_variations:
            character_profile.name_variations.append(attribution_result.character_name)

        return character_profile

    def _merge_speech_patterns(self, existing: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Merge new speech patterns with existing ones"""
        for key, value in new.items():
            if key in existing:
                if isinstance(value, (int, float)) and isinstance(existing[key], (int, float)):
                    # Average numeric values
                    existing[key] = (existing[key] + value) / 2
                elif isinstance(value, list):
                    # Merge lists
                    existing[key] = list(set(existing[key] + value))
            else:
                existing[key] = value

    def _merge_voice_characteristics(self, existing: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Merge new voice characteristics with existing ones"""
        for key, value in new.items():
            if key not in existing or not existing[key]:
                existing[key] = value

    # Speech analysis helper methods
    def _detect_formality(self, text: str) -> str:
        """Detect formality level of speech"""
        formal_indicators = ["indeed", "certainly", "however", "furthermore", "nevertheless"]
        casual_indicators = ["don't", "won't", "can't", "yeah", "ok", "hey"]

        formal_count = sum(1 for word in formal_indicators if word in text.lower())
        casual_count = sum(1 for word in casual_indicators if word in text.lower())

        if formal_count > casual_count:
            return "formal"
        elif casual_count > formal_count:
            return "casual"
        else:
            return "neutral"

    def _extract_common_words(self, text: str) -> List[str]:
        """Extract common words from text"""
        words = re.findall(r"\b\w+\b", text.lower())
        # Filter out very common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        filtered_words = [w for w in words if w not in common_words and len(w) > 2]
        return list(set(filtered_words))[:10]  # Top 10 unique words

    def _count_contractions(self, text: str) -> int:
        """Count contractions in text"""
        contractions = ["n't", "'re", "'ve", "'ll", "'d", "'s", "'m"]
        return sum(text.count(contraction) for contraction in contractions)

    def _estimate_age_from_speech(self, text: str) -> str:
        """Estimate age group from speech patterns"""
        young_indicators = ["awesome", "cool", "dude", "like", "totally", "whatever"]
        old_indicators = ["indeed", "certainly", "proper", "quite", "rather", "dear"]

        young_count = sum(1 for word in young_indicators if word in text.lower())
        old_count = sum(1 for word in old_indicators if word in text.lower())

        if young_count > old_count:
            return "young"
        elif old_count > young_count:
            return "mature"
        else:
            return "unknown"

    def _estimate_gender(self, name: str, text: str) -> str:
        """Estimate gender from name and speech patterns"""
        # Simple name-based estimation (very basic)
        male_names = ["john", "james", "robert", "michael", "william", "david", "richard", "thomas"]
        female_names = ["mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan", "jessica"]

        name_lower = name.lower()
        if any(male_name in name_lower for male_name in male_names):
            return "male"
        elif any(female_name in name_lower for female_name in female_names):
            return "female"
        else:
            return "unknown"

    def _detect_social_class(self, text: str) -> List[str]:
        """Detect social class indicators"""
        upper_class = ["certainly", "indeed", "quite", "rather", "proper", "distinguished"]
        working_class = ["ain't", "gonna", "wanna", "gotta", "dunno"]

        indicators = []
        if any(word in text.lower() for word in upper_class):
            indicators.append("upper_class")
        if any(word in text.lower() for word in working_class):
            indicators.append("working_class")

        return indicators if indicators else ["middle_class"]

    def _detect_regional_markers(self, text: str) -> List[str]:
        """Detect regional speech markers"""
        # Very basic regional detection
        southern = ["y'all", "ain't", "fixin'", "reckon"]
        british = ["bloody", "bloke", "chap", "brilliant", "cheers"]

        markers = []
        if any(word in text.lower() for word in southern):
            markers.append("southern")
        if any(word in text.lower() for word in british):
            markers.append("british")

        return markers

    def _detect_personality_traits(self, text: str) -> List[str]:
        """Detect personality traits from speech"""
        confident = ["absolutely", "definitely", "certainly", "of course"]
        hesitant = ["maybe", "perhaps", "i think", "possibly", "um", "uh"]

        traits = []
        if any(word in text.lower() for word in confident):
            traits.append("confident")
        if any(word in text.lower() for word in hesitant):
            traits.append("hesitant")

        return traits

    def _analyze_emotional_indicators(self, text: str) -> Dict[str, int]:
        """Analyze emotional indicators in text"""
        emotions = {
            "excitement": text.count("!"),
            "questioning": text.count("?"),
            "emphasis": len(re.findall(r"[A-Z]{2,}", text)),  # ALL CAPS words
            "pauses": text.count("...") + text.count(" - "),
        }

        return emotions

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _create_skip_output(self, reason: str) -> Data:
        """Create output for skipped processing"""
        return Data(
            data={
                "speaker_attribution": {
                    "status": "skipped",
                    "reason": reason,
                    "character_id": None,
                    "character_name": None,
                    "attribution_method": "none",
                    "confidence": 0.0,
                },
                "success": True,
                "agent": "abm_speaker_attribution",
            }
        )

    def _create_error_output(self, error_message: str) -> Data:
        """Create output for error cases"""
        return Data(
            data={
                "speaker_attribution": {
                    "status": "error",
                    "error": error_message,
                    "character_id": None,
                    "character_name": None,
                    "attribution_method": "error",
                    "confidence": 0.0,
                },
                "success": False,
                "agent": "abm_speaker_attribution",
            }
        )
