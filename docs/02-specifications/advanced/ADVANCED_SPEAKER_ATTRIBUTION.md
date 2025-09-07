# Advanced Speaker Attribution Strategy for 95% F1 Score

**Document Purpose:** Technical approach to achieve 95% F1 score for speaker attribution in dialogue\
**Current Baseline:** Simple heuristic-based segmentation (~60-70% estimated accuracy)\
**Target Performance:** 95% F1 score on test dataset\
**Timeline:** 3 weeks (Phase 2 of MVP)

## Current State Analysis

### **Existing Implementation Limitations**

- **Simple Quote Detection**: Current `simple_segment()` only looks for `"` characters
- **No Speaker Identification**: Only classifies dialogue vs narration, not WHO is speaking
- **Context Ignorance**: No consideration of surrounding narrative context
- **Character Tracking**: No persistent character state across utterances
- **Quote Attribution**: No linking of dialogue to preceding/following attribution text

### **Performance Gap Assessment**

````text
Current: ~60-70% (estimated, heuristic-based)
Target:   95% F1 score
Gap:      25-35 percentage points improvement needed
```text

## Technical Strategy Overview

To achieve 95% F1 score, we need a **multi-layered approach** combining:

1. **Enhanced Segmentation** - Better dialogue boundary detection
2. **Context-Aware Attribution** - Use surrounding text to identify speakers
3. **Character State Tracking** - Maintain speaker context across conversation
4. **Multi-Model Ensemble** - Combine multiple attribution techniques
5. **Active Learning Pipeline** - Iterative improvement with feedback

## Detailed Technical Approach

### **Layer 1: Enhanced Dialogue Segmentation**

#### **Improved Quote Detection**

```python
def enhanced_segment(text: str) -> List[Dict[str, str]]:
    """Advanced segmentation with better quote boundary detection."""
    patterns = [
        r'"[^"]*"',           # Standard double quotes
        r"'[^']*'",           # Single quotes (for inner dialogue)
        r'"[^"]*$',           # Unclosed quotes (paragraph continuation)
        r'^[^"]*"',           # Quote completion from previous paragraph
        r'["""][^"""]*["""]', # Smart quotes / Unicode quotes
    ]
    # Implementation with regex + context validation
```text

#### **Narrative Context Parsing**

- **Attribution Phrases**: "said John", "Mary whispered", "he replied"
- **Action Beats**: "John slammed the door. 'I'm leaving!'"
- **Thought Indicators**: "John thought to himself", "she wondered"

### **Layer 2: Multi-Model Speaker Attribution Pipeline**

#### **Model 1: Rule-Based Attribution (Baseline - 75% F1)**

```python
class RuleBasedAttributor:
    def __init__(self):
        self.patterns = {
            'direct_attribution': r'(\w+)\s+(said|asked|replied|whispered|shouted)',
            # note: split strings to avoid "](" adjacency in docs
            'reverse_attribution': r"[\"\"]" + r"(.*?)" + r"[\"\"]\s*,?\s*(\\w+)\s+(said|asked)",
            'action_attribution': r"(\\w+)\s+[a-z]+ed[^.]*\\.\s*" + r"[\"\"]" + r"(.*?)" + r"[\"\"]",
        }

    def attribute_speaker(self, utterance: str, context: str) -> Dict:
        # Rule-based matching with confidence scoring
        pass
```text

#### **Model 2: NER + Coreference Resolution (Target: 85% F1)**

```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

class CorefAttributor:
    def __init__(self):
        # Use specialized coreference model (e.g., SpanBERT-coref)
        self.coref_model = pipeline("coreference-resolution",
                                   model="SpanBERT-coref")
        self.ner_model = pipeline("ner",
                                 model="dbmdz/bert-large-cased-finetuned-conll03-english")

    def resolve_speakers(self, chapter_text: str) -> Dict:
        # Full chapter coreference resolution
        # Link pronouns to character entities
        pass
```text

#### **Model 3: LLM-Based Attribution (Target: 90% F1)**

```python
class LLMAttributor:
    def __init__(self):
        # Use local LLM (Llama 3.1 8B) for complex attribution
        self.model = "llama3.1:8b-instruct-q4_k_m"

    def attribute_with_llm(self, utterance: str, context: str,
                          characters: List[str]) -> Dict:
        prompt = f"""
        Given this dialogue and context, identify the speaker:

        Characters: {', '.join(characters)}
        Context: {context}
        Dialogue: "{utterance}"

        Return the most likely speaker with confidence (0-1).
        Format: {{"speaker": "NAME", "confidence": 0.95, "reasoning": "..."}}
        """
        # LLM inference with structured output
        pass
```text

#### **Model 4: Character Embedding Similarity (Target: 88% F1)**

```python
from sentence_transformers import SentenceTransformer

class EmbeddingAttributor:
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.character_profiles = {}  # Character → embedding vectors

    def build_character_profiles(self, attributed_utterances: List[Dict]):
        """Build character speech pattern embeddings from known attributions."""
        pass

    def similarity_attribution(self, utterance: str, characters: List[str]) -> Dict:
        """Find most similar character based on speech patterns."""
        pass
```text

### **Layer 3: Ensemble Attribution System**

#### **Weighted Voting Mechanism**

```python
class EnsembleAttributor:
    def __init__(self):
        self.models = [
            RuleBasedAttributor(weight=0.2),
            CorefAttributor(weight=0.3),  
            LLMAttributor(weight=0.3),
            EmbeddingAttributor(weight=0.2)
        ]

    def predict_speaker(self, utterance: str, context: str,
                       characters: List[str]) -> Dict:
        predictions = []
        for model in self.models:
            pred = model.predict(utterance, context, characters)
            predictions.append({
                'speaker': pred['speaker'],
                'confidence': pred['confidence'] * model.weight,
                'model': model.__class__.__name__
            })

        # Weighted voting with confidence thresholding
        final_prediction = self._ensemble_vote(predictions)
        return final_prediction
```text

### **Layer 4: Character State Management**

#### **Conversation Context Tracking**

```python
class ConversationState:
    def __init__(self):
        self.active_speakers = []  # Currently present characters
        self.last_speaker = None   # Last identified speaker
        self.conversation_turns = []  # Turn-taking history

    def update_context(self, utterance: Dict, attribution: Dict):
        """Update conversation state with new attribution."""
        if attribution['confidence'] > 0.8:
            self.last_speaker = attribution['speaker']
            self.conversation_turns.append({
                'speaker': attribution['speaker'],
                'turn_index': len(self.conversation_turns),
                'utterance_id': utterance['id']
            })

    def get_likely_speaker(self) -> Dict:
        """Use conversation flow to predict likely next speaker."""
        # Implement turn-taking heuristics
        pass
```text

#### **Character Bible Integration**

```python
class CharacterBible:
    def __init__(self):
        self.characters = {}  # name → character profile

    def add_character(self, name: str, aliases: List[str],
                     speech_patterns: Dict, personality: Dict):
        """Add character with speech characteristics."""
        self.characters[name] = {
            'aliases': aliases,  # ["John", "Johnny", "Mr. Smith"]
            'speech_patterns': speech_patterns,  # vocabulary, tone, etc.
            'personality': personality,  # affects dialogue style
            'dialogue_history': [],  # previous utterances
        }

    def resolve_alias(self, speaker_candidate: str) -> str:
        """Resolve speaker alias to canonical character name."""
        pass
```text

### **Layer 5: Training Data & Evaluation Pipeline**

#### **Gold Standard Dataset Creation**

```python
# Create annotated test set for evaluation
GOLD_STANDARD_ANNOTATIONS = [
    {
        "text": "\"I can't believe you did that,\" Mary said angrily.",
        "utterance": "I can't believe you did that,",
        "speaker": "Mary",
        "attribution_type": "direct_said",
        "confidence": 1.0
    },
    # ... 500+ manually verified examples
]
```text

#### **Automated Evaluation Pipeline**

```python
def evaluate_speaker_attribution(predictions: List[Dict],
                                gold_standard: List[Dict]) -> Dict:
    """Calculate precision, recall, F1 for speaker attribution."""
    tp = sum(1 for p, g in zip(predictions, gold_standard)
             if p['speaker'] == g['speaker'])
    fp = sum(1 for p, g in zip(predictions, gold_standard)
             if p['speaker'] != g['speaker'] and p['speaker'] != 'UNKNOWN')
    fn = sum(1 for p, g in zip(predictions, gold_standard)
             if p['speaker'] != g['speaker'] and g['speaker'] != 'UNKNOWN')

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {'precision': precision, 'recall': recall, 'f1': f1}
```text

## Implementation Roadmap

### **Week 1: Foundation & Rule-Based System**

- [ ] Enhanced segmentation with better quote detection
- [ ] Rule-based attribution patterns (said/asked/replied)
- [ ] Character name extraction and alias resolution
- [ ] Basic conversation state tracking
- [ ] **Target: 75% F1 score**

### **Week 2: ML Models & Coreference**

- [ ] Integrate Hugging Face coreference model
- [ ] NER-based character identification
- [ ] Character embedding similarity system
- [ ] LLM-based attribution for complex cases
- [ ] **Target: 85% F1 score**

### **Week 3: Ensemble & Optimization**

- [ ] Ensemble voting mechanism
- [ ] Advanced conversation flow modeling
- [ ] Character bible integration
- [ ] Performance tuning and optimization
- [ ] **Target: 95% F1 score**

## Performance Optimization Strategies

### **Caching & Efficiency**

- Cache LLM responses with input hash keys
- Precompute character embeddings for known speakers
- Batch NER and coreference processing per chapter
- Use quantized models for faster inference

### **Error Analysis & Improvement**

- Track common failure modes (pronouns, nested quotes, etc.)
- Build failure-specific sub-models
- Active learning: identify low-confidence predictions for manual review
- Iterative model refinement based on error patterns

### **Quality Assurance**

- Confidence thresholding: compute span-level scores (e.g., speaker_id_conf, style_match_conf, type_conf) and aggregate C_span = min(...). If below threshold, select the best guess and tag `MANDATORY_REVIEW_LLM`; never emit `UNKNOWN` in outputs.
- Local-first retry: attempt local LLM reprocessing before any cloud call; cache results by hash.
- Cloud-gated review: Only send flagged samples for external review after explicit user approval and cost estimate.
- Cross-validation across different book genres/styles  
- A/B testing of individual model components
- Human-in-the-loop verification for edge cases

## Resource Requirements

### **Computational Resources**

- **CPU**: 8 cores for parallel NLP processing
- **Memory**: 16GB for large language models in memory
- **Storage**: 5GB for model weights and embeddings
- **GPU**: Optional, for faster transformer inference

### **External Dependencies**

```yaml
dependencies:
  - transformers>=4.21.0
  - sentence-transformers>=2.2.0  
  - spacy>=3.4.0
  - torch>=1.12.0
  - ollama  # For local LLM inference
  - datasets>=2.0.0  # For evaluation datasets
```text

## Risk Mitigation

### **High-Risk Areas**

1. **Coreference Model Accuracy**: May struggle with complex pronoun resolution
   - **Mitigation**: Fallback to rule-based pronoun→speaker mapping
2. **LLM Hallucination**: May invent non-existent characters
   - **Mitigation**: Constrain LLM to choose from known character list
3. **Processing Speed**: Ensemble approach may be too slow
   - **Mitigation**: Model cascading - use fast models first, complex ones only for uncertainty

### **Fallback Strategies**

- **High Confidence Threshold**: Only commit to predictions >90% confidence
- **Best-guess + QA**: Never emit "UNKNOWN"; choose the best candidate and tag `MANDATORY_REVIEW_LLM` when confidence < 0.90
- **Human Review Pipeline**: Flag edge cases for manual annotation

## Success Metrics & Validation

### **Primary Metrics**

- **Speaker Attribution F1**: >95% on test dataset
- **Character Consistency**: Same character maintains consistent attribution
- **Processing Speed**: <500ms per utterance on standard hardware

### **Secondary Metrics**  

- **Precision by Attribution Type**: Direct speech, reported speech, thought
- **Recall by Character**: Ensure all major characters properly attributed
- **Confidence Calibration**: High confidence predictions should be highly accurate

### **Validation Methodology**

1. **Stratified Test Set**: Multiple book genres, dialogue complexity levels
2. **Cross-Book Validation**: Train on Book A, test on Book B
3. **Ablation Studies**: Measure contribution of each model component
4. **Error Analysis**: Deep dive on failure cases for targeted improvements

---

This comprehensive approach combines multiple proven NLP techniques in an ensemble system designed specifically to achieve the ambitious 95% F1 target for speaker attribution. The phased implementation allows for iterative improvement and risk mitigation while maintaining the deterministic, local-first principles of the project.
````
