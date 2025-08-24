"""
Test Agent 2 - ABM Speaker Attribution Component

Basic validation tests for the speaker attribution functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch
from src.abm.lf_components.audiobook.abm_speaker_attribution import ABMSpeakerAttribution


class TestABMSpeakerAttribution:
    """Test cases for Agent 2 Speaker Attribution"""

    def setup_method(self):
        """Set up test instance"""
        self.component = ABMSpeakerAttribution()
        # Mock the required attributes
        self.component.classified_utterance = '{"classification": "dialogue", "text": "Hello there!"}'
        self.component.dialogue_text = "Hello there!"
        self.component.book_id = "test_book"
        self.component.chapter_id = "chapter_1"
        self.component.context_before = "John walked up to the door."
        self.component.context_after = "He knocked twice."
        self.component.attribution_method = "all"
        self.component.min_confidence = 0.3
        self.component.create_new_characters = True
        self.component.update_profiles = True

    def test_parse_agent1_input_json(self):
        """Test parsing JSON input from Agent 1"""
        result = self.component._parse_agent1_input()

        assert result["dialogue_text"] == "Hello there!"
        assert result["book_id"] == "test_book"
        assert result["chapter_id"] == "chapter_1"
        assert result["utterance_type"] == "dialogue"

    def test_parse_agent1_input_plain_text(self):
        """Test parsing plain text input from Agent 1"""
        self.component.classified_utterance = "Just plain dialogue text"
        result = self.component._parse_agent1_input()

        assert result["dialogue_text"] == "Just plain dialogue text"
        assert result["utterance_type"] == "dialogue"

    def test_validate_input_valid_dialogue(self):
        """Test validation with valid dialogue input"""
        utterance_data = {"utterance_type": "dialogue", "dialogue_text": "Hello there!"}

        assert self.component._validate_input(utterance_data) is True

    def test_validate_input_non_dialogue(self):
        """Test validation with non-dialogue input"""
        utterance_data = {"utterance_type": "narration", "dialogue_text": "The sun was setting."}

        assert self.component._validate_input(utterance_data) is False

    def test_validate_input_empty_dialogue(self):
        """Test validation with empty dialogue text"""
        utterance_data = {"utterance_type": "dialogue", "dialogue_text": ""}

        assert self.component._validate_input(utterance_data) is False

    def test_direct_attribution_simple(self):
        """Test direct attribution with simple pattern"""
        result = self.component._direct_attribution('"Hello," John said.', "The man approached the door.")

        assert result is not None
        assert result.character_name == "John"
        assert result.attribution_method == "direct"
        assert result.confidence >= 0.9

    def test_direct_attribution_reverse_pattern(self):
        """Test direct attribution with reverse pattern"""
        result = self.component._direct_attribution(
            '"I think we should go," she said quietly.', "Mary had been thinking about this all day."
        )

        assert result is not None
        assert result.attribution_method == "direct"
        assert result.confidence >= 0.9

    def test_direct_attribution_no_match(self):
        """Test direct attribution with no matching patterns"""
        result = self.component._direct_attribution("Hello there!", "Someone was at the door.")

        assert result is None

    def test_contextual_attribution_character_in_context(self):
        """Test contextual attribution when character mentioned in context"""
        result = self.component._contextual_attribution(
            "How are you doing?", "Sarah walked up to the window.", "She looked outside thoughtfully."
        )

        if result:
            print(f"Contextual result: {result.character_name}, confidence: {result.confidence}")
            assert result.character_name == "Sarah"
            assert result.attribution_method == "contextual"
            assert result.confidence >= 0.7
        else:
            # Debug why contextual attribution failed
            print("Contextual attribution returned None - checking scoring")
            score = self.component._score_contextual_name(
                "Sarah", "Sarah walked up to the window.", "She looked outside thoughtfully.", "How are you doing?"
            )
            print(f"Sarah score: {score}")
            assert False, f"Expected contextual attribution but got None (score: {score})"

    def test_contextual_attribution_no_names(self):
        """Test contextual attribution with no character names"""
        result = self.component._contextual_attribution(
            "Hello there!", "The door opened slowly.", "Footsteps could be heard."
        )

        assert result is None

    def test_conversation_flow_attribution(self):
        """Test conversation flow attribution"""
        # Set up conversation history
        self.component.conversation_history = [("char_001", "How are you?")]

        result = self.component._conversation_flow_attribution("I'm doing well, thanks!")

        assert result is not None
        assert result.attribution_method == "inferred"
        assert 0.4 <= result.confidence <= 0.6

    def test_conversation_flow_empty_history(self):
        """Test conversation flow with empty history"""
        self.component.conversation_history = []

        result = self.component._conversation_flow_attribution("Hello there!")

        assert result is None

    def test_extract_speech_patterns(self):
        """Test speech pattern extraction"""
        patterns = self.component._extract_speech_patterns("Well, I think we should definitely go! Don't you agree?")

        assert "formality_level" in patterns
        assert "sentence_length" in patterns
        assert "question_count" in patterns
        assert "exclamation_count" in patterns
        assert patterns["question_count"] == 1
        assert patterns["exclamation_count"] == 1

    def test_analyze_voice_characteristics(self):
        """Test voice characteristics analysis"""
        characteristics = self.component._analyze_voice_characteristics(
            "Indeed, I believe we should proceed with utmost care.", "Professor Smith"
        )

        assert "estimated_age" in characteristics
        assert "estimated_gender" in characteristics
        assert "social_class_indicators" in characteristics
        assert "regional_markers" in characteristics
        assert "personality_traits" in characteristics
        assert "emotional_range" in characteristics

    def test_clean_character_name(self):
        """Test character name cleaning"""
        # Test normal name
        assert self.component._clean_character_name("John Smith") == "John Smith"

        # Test name with stopwords
        assert self.component._clean_character_name("the John and Mary") == "John Mary"

        # Test empty result
        assert self.component._clean_character_name("the and or") == ""

    def test_generate_character_id(self):
        """Test character ID generation"""
        id1 = self.component._generate_character_id("John Smith")
        id2 = self.component._generate_character_id("john smith")  # lowercase
        id3 = self.component._generate_character_id("Jane Doe")

        # Same name should generate same ID
        assert id1 == id2
        # Different names should generate different IDs
        assert id1 != id3
        # IDs should start with char_
        assert id1.startswith("char_")

    def test_score_contextual_name(self):
        """Test contextual name scoring"""
        # Close context should score high
        score1 = self.component._score_contextual_name(
            "Mary", "Mary walked to the door.", "She knocked twice.", "Hello there!"
        )
        assert score1 > 0.5

        # Distant context should score lower
        score2 = self.component._score_contextual_name(
            "John",
            "John had been thinking about this for days and days and days.",
            "Meanwhile, the weather was getting worse outside.",
            "Hello!",
        )
        assert score2 < score1

    def test_is_response_pattern(self):
        """Test response pattern detection"""
        # Response indicators
        assert self.component._is_response_pattern("Yes, I think so.") is True
        assert self.component._is_response_pattern("No, not really.") is True
        assert self.component._is_response_pattern("Well, maybe.") is True
        assert self.component._is_response_pattern("What do you mean?") is True

        # Non-response
        assert self.component._is_response_pattern("The sun was setting.") is False

    def test_detect_formality(self):
        """Test formality detection"""
        # Formal
        assert self.component._detect_formality("Indeed, I certainly agree.") == "formal"

        # Casual
        assert self.component._detect_formality("Yeah, I don't think so.") == "casual"

        # Neutral
        assert self.component._detect_formality("I think we should go.") == "neutral"

    def test_estimate_age_from_speech(self):
        """Test age estimation from speech"""
        # Young indicators
        assert self.component._estimate_age_from_speech("That's totally awesome, dude!") == "young"

        # Mature indicators
        assert self.component._estimate_age_from_speech("Indeed, quite proper.") == "mature"

        # Unknown
        assert self.component._estimate_age_from_speech("Hello there.") == "unknown"

    def test_full_attribution_workflow_direct(self):
        """Test complete attribution workflow with direct attribution"""
        # Set up for direct attribution
        self.component.context_before = "John walked up to the door."
        self.component.dialogue_text = '"Hello there," John said.'

        result = self.component.attribute_speaker()

        assert result.data["success"] is True
        attribution = result.data["speaker_attribution"]
        assert attribution["character_name"] == "John"
        assert attribution["attribution_method"] == "direct"
        assert attribution["confidence"] >= 0.9

    def test_full_attribution_workflow_skip(self):
        """Test complete workflow with non-dialogue input"""
        self.component.classified_utterance = '{"classification": "narration", "text": "The sun was setting."}'
        self.component.dialogue_text = ""

        result = self.component.attribute_speaker()

        assert result.data["success"] is True
        attribution = result.data["speaker_attribution"]
        assert attribution["status"] == "skipped"

    def test_character_creation_and_update(self):
        """Test character creation and profile updates"""
        # First attribution - should create new character
        attribution_result = self.component._direct_attribution('"Hello," Mary said.', "The woman approached.")

        utterance_data = {"dialogue_text": "Hello there!", "book_id": "test_book", "chapter_id": "chapter_1"}

        # Create character
        character_profile = self.component._create_new_character(attribution_result, utterance_data)

        assert character_profile.canonical_name == "Mary"
        assert character_profile.utterance_count == 1
        assert len(character_profile.dialogue_samples) == 1
        assert character_profile.first_appearance == "test_book_chapter_1"

    def test_error_handling(self):
        """Test error handling in attribution workflow"""
        # Set up invalid input
        self.component.classified_utterance = "invalid json {"

        result = self.component.attribute_speaker()

        # Should not crash, should return error output
        assert isinstance(result.data, dict)
        # In case of JSON error, it should still process as plain text
        assert result.data.get("success") is not None


if __name__ == "__main__":
    # Run basic tests
    test_instance = TestABMSpeakerAttribution()
    test_instance.setup_method()

    print("🧪 Testing Agent 2 - ABM Speaker Attribution")

    # Test basic functionality
    try:
        test_instance.test_parse_agent1_input_json()
        print("✅ Parse Agent 1 JSON input")

        test_instance.test_validate_input_valid_dialogue()
        print("✅ Validate dialogue input")

        test_instance.test_direct_attribution_simple()
        print("✅ Direct attribution")

        test_instance.test_contextual_attribution_character_in_context()
        print("✅ Contextual attribution")

        test_instance.test_extract_speech_patterns()
        print("✅ Speech pattern extraction")

        test_instance.test_clean_character_name()
        print("✅ Character name cleaning")

        test_instance.test_full_attribution_workflow_direct()
        print("✅ Full attribution workflow")

        print("\n🎉 All core tests passed! Agent 2 is ready for use.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
