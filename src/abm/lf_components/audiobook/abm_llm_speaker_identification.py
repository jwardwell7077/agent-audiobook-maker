"""ABM LLM Speaker Identification Component for LangFlow."""

from langflow.custom import Component
from langflow.io import DataInput, IntInput, Output, StrInput
from langflow.schema import Data


class ABMLLMSpeakerIdentification(Component):
    display_name = "ABM LLM Speaker Identification"
    description = "Use LLM to identify speakers and segment dialogue contextually"
    icon = "user-voice"
    name = "ABMLLMSpeakerIdentification"

    inputs = [
        DataInput(
            name="chapters_data",
            display_name="Chapters Data",
            info="Data containing chapters to analyze",
            required=True,
        ),
        StrInput(
            name="llm_model",
            display_name="LLM Model",
            info="LLM model to use for speaker identification",
            value="gpt-4o-mini",
            required=True,
        ),
        IntInput(
            name="context_window",
            display_name="Context Window",
            info="Number of surrounding paragraphs to include for context",
            value=3,
            required=False,
        ),
    ]

    outputs = [Output(name="speaker_identified_data", display_name="Speaker Identified Data", method="identify_speakers")]

    def identify_speakers(self) -> Data:
        """Use LLM to identify speakers and segment dialogue contextually."""
        try:
            input_data = self.chapters_data.data

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            chapters = input_data.get("chapters", [])
            if not chapters:
                self.status = "No chapters to analyze"
                return Data(data=input_data)

            analyzed_chapters = []
            total_utterances = 0

            for chapter in chapters:
                body_text = chapter.get("body_text", "")
                if not body_text:
                    continue

                # Split into paragraphs for analysis
                paragraphs = [p.strip() for p in body_text.split('\n\n') if p.strip()]
                
                chapter_utterances = []
                
                for i, paragraph in enumerate(paragraphs):
                    # Get surrounding context
                    context_start = max(0, i - self.context_window)
                    context_end = min(len(paragraphs), i + self.context_window + 1)
                    context = paragraphs[context_start:context_end]
                    
                    # Analyze paragraph with LLM
                    analysis = self._analyze_paragraph_with_llm(paragraph, context, chapter)
                    
                    utterance = {
                        "text": paragraph,
                        "type": analysis["type"],  # dialogue, narration, thought, etc.
                        "speaker": analysis.get("speaker"),  # character name or null
                        "confidence": analysis.get("confidence", 0.0),
                        "paragraph_index": i,
                        "length": len(paragraph),
                        "context_used": len(context),
                    }
                    
                    chapter_utterances.append(utterance)

                analyzed_chapter = {
                    "chapter_index": chapter.get("index"),
                    "chapter_title": chapter.get("title"),
                    "utterances": chapter_utterances,
                    "total_utterances": len(chapter_utterances),
                    "characters_identified": list(set(u["speaker"] for u in chapter_utterances if u["speaker"])),
                }
                
                analyzed_chapters.append(analyzed_chapter)
                total_utterances += len(chapter_utterances)

            result_data = {
                "analyzed_chapters": analyzed_chapters,
                "total_chapters": len(analyzed_chapters),
                "total_utterances": total_utterances,
                "all_characters": list(set().union(*[ch["characters_identified"] for ch in analyzed_chapters])),
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
            }

            self.status = f"Identified speakers in {len(analyzed_chapters)} chapters, {total_utterances} utterances, {len(result_data['all_characters'])} characters"
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to identify speakers: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def _analyze_paragraph_with_llm(self, paragraph: str, context: list, chapter: dict) -> dict:
        """Analyze a paragraph using LLM to identify speaker and type."""
        
        # This would integrate with your preferred LLM (OpenAI, Anthropic, local model, etc.)
        # For now, showing the structure of what the analysis would return
        
        system_prompt = f"""
        You are analyzing a paragraph from a fantasy novel to identify:
        1. Type: dialogue, narration, thought, action, description
        2. Speaker: character name if dialogue, or null if narration
        3. Confidence: 0.0-1.0 confidence in the identification
        
        Chapter context: {chapter.get('title', 'Unknown')}
        
        Surrounding paragraphs for context:
        {chr(10).join(f"[{i}]: {p[:100]}..." for i, p in enumerate(context))}
        
        Analyze this paragraph:
        {paragraph}
        
        Return JSON: {{"type": "dialogue|narration|thought|action|description", "speaker": "character_name_or_null", "confidence": 0.95}}
        """
        
        # Placeholder for LLM call - would integrate with your chosen LLM
        # Example response structure:
        if '"' in paragraph and any(word in paragraph.lower() for word in ['said', 'shouted', 'asked', 'replied']):
            # Try to extract speaker from dialogue tags
            speaker = self._extract_speaker_from_dialogue_tag(paragraph)
            return {
                "type": "dialogue",
                "speaker": speaker,
                "confidence": 0.8 if speaker else 0.6
            }
        elif '"' in paragraph:
            return {
                "type": "dialogue", 
                "speaker": None,  # Would need LLM to determine from context
                "confidence": 0.7
            }
        else:
            return {
                "type": "narration",
                "speaker": None,
                "confidence": 0.9
            }

    def _extract_speaker_from_dialogue_tag(self, paragraph: str) -> str:
        """Extract speaker name from dialogue tags like 'Quinn said' or 'shouted Vorden'."""
        # Simple regex-based extraction - LLM would be more sophisticated
        import re
        
        # Look for patterns like "said Quinn" or "Quinn said"
        patterns = [
            r'"[^"]*"\s*([A-Z][a-z]+)\s+(?:said|shouted|asked|replied|whispered)',
            r'(?:said|shouted|asked|replied|whispered)\s+([A-Z][a-z]+)',
            r'([A-Z][a-z]+)\s+(?:said|shouted|asked|replied|whispered)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, paragraph)
            if match:
                return match.group(1)
        
        return None
