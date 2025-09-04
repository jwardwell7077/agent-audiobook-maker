This document has moved. The legacy two-agent plan is out of scope for this branch.

See: `docs/_deprecated/two-agent-dialogue-speaker-system.md`.

- **Output**: Classified segments with confidence scores
- **Database Impact**: Updates utterances table with classification data

#### Speaker Attribution Agent

- **Purpose**: Associate dialogue with specific characters
- **Input**: Dialogue segments from Classifier Agent
- **Output**: Speaker-attributed dialogue segments
- **Database Impact**: Creates character records and associations

### 2.2 Data Flow Architecture

```text
Text Segments → Dialogue Classifier → Dialogue Segments → Speaker Attribution → Character Database
                        ↓
                 Narration Segments → Character Context Collection
```

## 3. Database Schema Design

### 3.1 Core Tables

#### Characters Table

```sql
CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id),
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255),
    aliases JSONB DEFAULT '[]'::JSONB,
    first_appearance_segment_id INTEGER,
    character_type VARCHAR(50) DEFAULT 'person',
    profile JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Character Text Segments Table

```sql
CREATE TABLE character_text_segments (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    utterance_id INTEGER NOT NULL REFERENCES utterances(id),
    segment_type VARCHAR(20) NOT NULL,
    relationship VARCHAR(50),
    context_before TEXT,
    context_after TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Utterances Table Extensions

```sql
ALTER TABLE utterances
ADD COLUMN dialogue_classification VARCHAR(20),
ADD COLUMN dialogue_confidence FLOAT DEFAULT 0.0,
ADD COLUMN speaker_character_id INTEGER REFERENCES characters(id),
ADD COLUMN speaker_confidence FLOAT DEFAULT 0.0,
ADD COLUMN processed_by_agents TIMESTAMP;
```

## 4. Agent Specifications

### 4.1 Dialogue Classifier Agent

#### Functional Requirements

- **DC-FR-001**: Classify text segments as dialogue, narration, or mixed content
- **DC-FR-002**: Assign confidence scores to all classifications
- **DC-FR-003**: Handle complex cases including interrupted dialogue
- **DC-FR-004**: Update database with classification results

#### Classification Logic

**Dialogue Indicators:**

- Direct quotations with dialogue tags
- Conversational patterns and speech markers
- Character interaction patterns

**Narration Indicators:**

- Descriptive and expository text
- Action sequences and scene setting
- Internal thoughts (non-quoted)

#### Input/Output Specifications

**Input Schema:**

```json
{
  "segment_id": "integer",
  "text": "string",
  "chapter_id": "integer",
  "position_in_chapter": "integer",
  "metadata": {
    "length": "integer",
    "paragraph_type": "string"
  }
}
```

**Output Schema:**

```json
{
  "segment_id": "integer",
  "classification": "dialogue|narration|mixed",
  "confidence": "float",
  "dialogue_portions": [
    {
      "text": "string",
      "start_pos": "integer",
      "end_pos": "integer"
    }
  ],
  "reasoning": "string"
}
```

### 4.2 Speaker Attribution Agent

#### Functional Requirements

- **SA-FR-001**: Identify speakers for dialogue segments
- **SA-FR-002**: Create new character records for unknown speakers
- **SA-FR-003**: Handle speaker ambiguity and multiple speakers
- **SA-FR-004**: Collect character-related text for profile building

#### Attribution Strategy

**Direct Attribution Methods:**

- Explicit dialogue tags ("John said")
- Speaker identification phrases
- Direct address patterns

**Contextual Attribution Methods:**

- Conversation flow and turn-taking analysis
- Character presence tracking in scenes
- Speech pattern recognition

#### Input/Output Specifications

**Input Schema:**

```json
{
  "segment_id": "integer",
  "text": "string",
  "dialogue_portions": [
    {
      "text": "string",
      "start_pos": "integer",
      "end_pos": "integer"
    }
  ],
  "context": {
    "previous_segments": ["string"],
    "chapter_characters": ["string"]
  }
}
```

**Output Schema:**

```json
{
  "segment_id": "integer",
  "attributions": [
    {
      "dialogue_text": "string",
      "character_id": "integer",
      "character_name": "string",
      "confidence": "float",
      "attribution_method": "direct|contextual|inferred"
    }
  ],
  "new_characters": [
    {
      "name": "string",
      "canonical_name": "string",
      "first_mention": "string",
      "character_type": "string"
    }
  ]
}
```

## 5. Character Profile Building

### 5.1 Data Collection Strategy

**Character Data Types:**

- **Direct Dialogue**: All spoken words attributed to character
- **Character Descriptions**: Narrative text describing the character
- **Character Actions**: Actions performed by the character
- **References**: Mentions by other characters
- **Context**: Surrounding narrative when character appears

### 5.2 Profile Data Structure

```json
{
  "character_id": "integer",
  "profile": {
    "dialogue_count": "integer",
    "word_count": "integer",
    "vocabulary_sample": ["string"],
    "speech_patterns": {
      "common_phrases": ["string"],
      "formality_level": "formal|casual|mixed",
      "dialect_markers": ["string"]
    },
    "descriptions": {
      "physical": ["string"],
      "personality": ["string"],
      "role": ["string"]
    },
    "relationships": {
      "character_id": {
        "type": "string",
        "evidence": ["string"]
      }
    },
    "scenes": ["integer"],
    "emotional_indicators": ["string"]
  }
}
```

## 6. Processing Pipeline

### 6.1 Sequential Processing Flow

1. **Input Processing**: Receive segmented text from existing pipeline
1. **Dialogue Classification**: Process segments through Classifier Agent
1. **Speaker Attribution**: Process dialogue segments through Attribution Agent
1. **Database Updates**: Persist classification and attribution results
1. **Profile Building**: Aggregate character data for profile updates

### 6.2 Error Handling Strategy

- **Low Confidence Classifications**: Flag segments for manual review
- **Speaker Ambiguity**: Store multiple attribution candidates
- **Character Name Conflicts**: Apply disambiguation strategies
- **Processing Failures**: Implement database transaction rollbacks

## 7. Performance Requirements

### 7.1 Throughput Targets

- Process minimum 1000 text segments per minute
- Handle books up to 500,000 words
- Support concurrent processing of multiple books

### 7.2 Accuracy Requirements

- Dialogue classification accuracy: >95%
- Speaker attribution accuracy: >85% for clear cases
- Character discovery recall: >90% for named characters

### 7.3 Scalability Design

- Stateless agent architecture for horizontal scaling
- Database connection pooling and optimization
- Batch processing capabilities for large texts

## 8. Integration Specifications

### 8.1 System Integration Points

- **Input**: Integration with existing text segmentation pipeline
- **Output**: Data provision to voice casting and TTS systems
- **Database**: Connection to existing PostgreSQL infrastructure
- **Monitoring**: Integration with system monitoring and logging

### 8.2 LangFlow Component Integration

- Designed as LangFlow components for workflow orchestration
- Compatible with existing component architecture
- Supports quality gate integration patterns

## 9. Testing Strategy

### 9.1 Testing Levels

**Unit Testing:**

- Individual agent logic validation
- Database operation testing
- Schema validation testing

**Integration Testing:**

- Full pipeline processing validation
- Database consistency verification
- Error handling scenario testing

**Performance Testing:**

- Load testing with representative text volumes
- Memory usage profiling and optimization
- Database query performance optimization

## 10. Implementation Roadmap

### 10.1 Development Phases

**Phase 1: Hybrid Classification System (Weeks 1-2)**

- Database schema implementation and migration
- Enhanced heuristics for dialogue/narration classification
- Agent framework for ambiguous cases only
- Integration with existing ABMSegmentDialogueNarration component

**Phase 2: Speaker Attribution Agent (Weeks 3-4)**

- Character database lookup and management
- Speaker attribution logic with context awareness
- Character discovery and alias resolution
- Database integration for character tracking

**Phase 3: Character Profile Building (Weeks 5-6)**

- Character data aggregation across segments
- Profile schema implementation with JSONB storage
- Relationship detection between characters
- Voice casting data preparation

**Phase 4: Full Agent Enhancement (Weeks 7-8)**

- Transition from hybrid to full agent classification
- Performance optimization for RTX 4070 hardware
- Advanced classification algorithms
- Quality assurance and accuracy validation

### 10.2 Success Criteria

**Functional Success Metrics:**

- All dialogue segments classified with target accuracy
- Complete character discovery and tracking
- Comprehensive character profile generation

**Technical Success Metrics:**

- Processing performance meets target requirements
- Database maintains consistency under load
- Seamless integration with existing pipeline

**Business Success Metrics:**

- Character data enables effective voice casting decisions
- Profile quality supports TTS voice assignment
- System scales to production processing volumes

## 11. Risk Assessment and Mitigation

### 11.1 Technical Risks

- **Classification Accuracy**: Implement iterative improvement cycles
- **Performance Bottlenecks**: Design with horizontal scaling capability
- **Data Consistency**: Implement robust transaction management

### 11.2 Integration Risks

- **Pipeline Compatibility**: Maintain backward compatibility with existing systems
- **Database Migration**: Plan phased migration with rollback capabilities
- **Component Dependencies**: Design loose coupling between agents

## 12. Appendices

### 12.1 Glossary

- **Character Profile**: Aggregated data about a character for voice casting
- **Dialogue Classification**: Process of identifying spoken vs narrative text
- **Speaker Attribution**: Assignment of dialogue to specific characters
- **Utterance**: Individual text segment from segmentation pipeline

### 12.2 References

- Existing segmentation pipeline documentation
- Database schema specifications
- LangFlow component architecture guidelines
- Performance testing frameworks and benchmarks
