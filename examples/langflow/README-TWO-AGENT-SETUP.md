# LangFlow Two-Agent System Setup Guide

## 🎯 Overview

This guide walks you through setting up and running the complete two-agent dialogue processing system in LangFlow.

**System Components:**

- **Agent 1**: ABM Dialogue Classifier (dialogue vs. narration)
- **Agent 2**: ABM Speaker Attribution (speaker identification + voice profiles)

## 🚀 Quick Start

### 1. Start LangFlow

```bash
cd /home/jon/repos/audio-book-maker-lg
./scripts/run_langflow.sh
```

### 2. Import Workflow

1. Open LangFlow at <http://127.0.0.1:7860>
2. Click "Import" or "New Flow"
3. Upload one of these workflow files:
   - `examples/langflow/two-agent-complete-workflow.json` (recommended)
   - `examples/langflow/two-agent-dialogue-speaker-system.json` (basic)

### 3. Test the System

Use these sample inputs to test:

**Sample 1 - Direct Attribution:**

```
"We need to make a fire," Ralph said firmly. "The smoke will help rescuers find us."
```

**Sample 2 - Contextual Attribution:**

```
Jack stepped forward angrily. "I should be the leader!" The other boys looked uncomfortable.
```

**Sample 3 - Conversation Flow:**

```
"What do you think we should do?" "I think we need to focus on rescue."
```

## 🔧 Detailed Setup

### Agent 1 Configuration (Dialogue Classifier)

| Parameter | Recommended Value | Purpose |
|-----------|------------------|---------|
| `min_confidence` | 0.7 | AI fallback threshold |
| `ai_classification_enabled` | true | Enable AI for uncertain cases |
| `ollama_model` | "llama3.2:1b" | Fast, lightweight model |
| `debug_mode` | false | Enable for troubleshooting |

### Agent 2 Configuration (Speaker Attribution)

| Parameter | Recommended Value | Purpose |
|-----------|------------------|---------|
| `attribution_method` | "all" | Use all attribution methods |
| `min_confidence` | 0.3 | Minimum attribution confidence |
| `create_new_characters` | true | Allow new character creation |
| `update_profiles` | true | Enable profile building |

## 📊 Expected Output Format

### Agent 1 Output (Dialogue Classifier)

```json
{
  "classification": "dialogue",
  "confidence": 0.95,
  "method": "heuristic",
  "text": "We need to make a fire",
  "dialogue_indicators": ["quoted_speech", "speech_verb"],
  "processing_metadata": {
    "agent": "abm_dialogue_classifier",
    "version": "1.0.0"
  }
}
```

### Agent 2 Output (Speaker Attribution)

```json
{
  "character_id": "char_a4b3c2d1",
  "character_name": "Ralph",
  "attribution_method": "direct",
  "confidence": 0.95,
  "dialogue_text": "We need to make a fire",
  "speech_patterns": {
    "formality_level": "neutral",
    "sentence_length": 6,
    "common_words": ["need", "make", "fire"]
  },
  "voice_characteristics": {
    "estimated_age": "young",
    "personality_traits": ["confident"],
    "social_class_indicators": ["middle_class"]
  },
  "processing_metadata": {
    "agent": "abm_speaker_attribution",
    "version": "2.0.0"
  }
}
```

## 🎭 Attribution Methods Explained

### 1. Direct Attribution (90-95% confidence)

**Patterns:**

- `"Hello," John said.`
- `Mary replied, "How are you?"`
- `Dr. Smith announced, "The results are in."`

### 2. Contextual Attribution (70-85% confidence)

**Analysis:**

- Character mentioned in surrounding text
- Actions attributed to characters before/after dialogue
- Scene character presence

### 3. Conversation Flow (40-60% confidence)

**Logic:**

- Turn-taking patterns (A → B → A)
- Response indicators ("Yes", "No", questions)
- Conversation continuity

### 4. Unknown Speaker (30% confidence)

**Fallback:**

- No clear attribution clues
- Multiple possible speakers
- New character introductions

## 🧪 Testing Scenarios

### Test 1: Direct Attribution

**Input:** `"I'll lead the expedition," Captain Smith declared confidently.`
**Expected:** Direct attribution to "Captain Smith" with 95% confidence

### Test 2: Contextual Attribution  

**Input:**

```
Context Before: Sarah walked to the window and looked outside.
Dialogue: "It's getting dark."
Context After: She turned back to the group with concern.
```

**Expected:** Contextual attribution to "Sarah" with 75-80% confidence

### Test 3: Conversation Flow

**Input:** (after previous dialogue from Character A)

```
"That's a good point."
```

**Expected:** Flow inference to different speaker with 50% confidence

### Test 4: Character Profile Building

**Multiple inputs from same character:**

```
"Indeed, I believe we should proceed with utmost care."
"Certainly, that would be the proper course of action."
"I must insist on following protocol."
```

**Expected:** Profile showing formal speech patterns, mature age estimation

## 🔍 Troubleshooting

### Common Issues

**1. Agent 1 not classifying correctly:**

- Check `min_confidence` threshold
- Verify Ollama is running for AI fallback
- Enable `debug_mode` for detailed logging

**2. Agent 2 not finding speakers:**

- Lower `min_confidence` to 0.2 for testing
- Check `attribution_method` is set to "all"
- Verify context fields have relevant text

**3. Character profiles not updating:**

- Ensure `update_profiles` is true
- Check `create_new_characters` is enabled
- Verify same `book_id` and `chapter_id`

### Debug Mode

Enable debug logging in both agents to see:

- Heuristic pattern matches
- AI classification decisions  
- Attribution method scoring
- Character profile updates

### Performance Optimization

**For speed:**

- Set `attribution_method` to "direct_only"
- Disable `update_profiles` for batch processing
- Use smaller Ollama model (llama3.2:1b)

**For accuracy:**

- Keep `attribution_method` as "all"
- Enable `update_profiles` for learning
- Use larger context windows

## 📈 Integration Examples

### 1. Batch Processing Pipeline

```
Text Input → Agent 1 → Agent 2 → Database Writer
```

### 2. Real-time Processing

```
Stream Input → Agent 1 Filter → Agent 2 → Live Dashboard
```

### 3. Voice Casting Workflow  

```
Agent 2 → Character Profiles → TTS Speaker Assignment
```

## 🎯 Next Steps

1. **Test the basic workflow** with provided samples
2. **Experiment with parameters** to optimize for your content
3. **Connect to database** for persistent character storage
4. **Build voice casting profiles** using character data
5. **Scale up processing** for full book chapters

## 📚 Related Documentation

- [Agent 1 Flow Diagram](../docs/04-diagrams/flows/agent-1-dialogue-classifier-flow.md)
- [Agent 2 Flow Diagram](../docs/04-diagrams/flows/agent-2-speaker-attribution-flow.md)  
- [Two-Agent System Specification](../docs/02-specifications/components/two-agent-dialogue-speaker-system.md)
- [Database Schema](../database/init/01-init-schema.sql)

---

**Ready to get started?** Import the workflow and start testing with the sample inputs! 🚀
