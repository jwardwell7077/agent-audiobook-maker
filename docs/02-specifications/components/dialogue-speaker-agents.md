# Two-Agent System: Dialogue Classification and Speaker Attribution

## Overview

This specification defines a two-agent system for audiobook text processing:

1. **Dialogue Classifier Agent** - Distinguishes narration from dialogue
1. **Speaker Attribution Agent** - Associates dialogue with specific characters

The system builds character profiles by collecting all text segments associated with each character in a database for future analysis and voice casting.

## System Architecture

### Agent Responsibilities

#### Agent 1: Dialogue Classifier

- **Input**: Text segments from the segmentation pipeline
- **Output**: Classified segments with dialogue/narration tags
- **Database**: Updates `utterances` table with classification results

#### Agent 2: Speaker Attribution

- **Input**: Dialogue segments from Agent 1
- **Output**: Speaker-attributed dialogue segments
- **Database**: Creates/updates character records and associates text

### Data Flow

```text
Text Segments → Agent 1 (Classify) → Dialogue Segments → Agent 2 (Attribute) → Character Database
                     ↓
              Narration Segments → Character Context Database
```

## Database Schema

### Characters Table

```sql
CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id),
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255), -- normalized form
    aliases JSONB DEFAULT '[]'::JSONB, -- alternative names/nicknames
    first_appearance_segment_id INTEGER,
    character_type VARCHAR(50) DEFAULT 'person', -- person, narrator, group, etc.
    profile JSONB DEFAULT '{}'::JSONB, -- collected traits, relationships
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Character Text Collection Table

```sql
CREATE TABLE character_text_segments (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    utterance_id INTEGER NOT NULL REFERENCES utterances(id),
    segment_type VARCHAR(20) NOT NULL, -- 'dialogue', 'about_character', 'context'
    relationship VARCHAR(50), -- 'speaker', 'mentioned', 'described_by'
    context_before TEXT, -- surrounding context
    context_after TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Enhanced Utterances Table

```sql
-- Add columns to existing utterances table
ALTER TABLE utterances 
ADD COLUMN dialogue_classification VARCHAR(20), -- 'dialogue', 'narration', 'mixed'
ADD COLUMN dialogue_confidence FLOAT DEFAULT 0.0,
ADD COLUMN speaker_character_id INTEGER REFERENCES characters(id),
ADD COLUMN speaker_confidence FLOAT DEFAULT 0.0,
ADD COLUMN processed_by_agents TIMESTAMP;
```

## Agent Specifications

### Dialogue Classification Agent

#### Functional Requirements

- **FR-DC-1**: Classify text segments as dialogue, narration, or mixed
- **FR-DC-2**: Provide confidence scores for classifications
- **FR-DC-3**: Handle complex cases (interrupted dialogue, mixed segments)
- **FR-DC-4**: Update utterances table with classification results

#### Classification Rules

1. **Dialogue Indicators**:

   - Direct quotations ("Hello," she said)
   - Dialogue tags (said, asked, whispered, etc.)
   - Character speech patterns

1. **Narration Indicators**:

   - Descriptive text
   - Action sequences
   - Setting descriptions
   - Internal thoughts (when not quoted)

1. **Mixed Content**:

   - Segments containing both dialogue and narration
   - Dialogue with embedded action/description

#### Input Schema

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

#### Output Schema

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

### Speaker Attribution Agent

#### Functional Requirements

- **FR-SA-1**: Identify speakers for dialogue segments
- **FR-SA-2**: Create character records for new speakers
- **FR-SA-3**: Handle speaker ambiguity and multiple speakers
- **FR-SA-4**: Collect character-related text for profile building

#### Attribution Strategy

1. **Direct Attribution**:

   - Explicit dialogue tags ("John said")
   - Speaker identification phrases

1. **Contextual Attribution**:

   - Conversation context and turn-taking
   - Character presence in scene
   - Speech patterns and vocabulary

1. **Character Discovery**:

   - New character introduction patterns
   - Name extraction and normalization
   - Alias/nickname detection

#### Input Schema

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

#### Output Schema

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
  ],
  "character_context": [
    {
      "character_id": "integer",
      "context_type": "description|action|reference",
      "text": "string"
    }
  ]
}
```

## Character Profile Building

### Data Collection Strategy

#### For Each Character

1. **Direct Dialogue**: All spoken words attributed to the character
1. **Character Descriptions**: Narrative text describing the character
1. **Character Actions**: Actions performed by the character
1. **References**: When other characters mention them
1. **Context**: Surrounding narrative when character appears

#### Profile Schema

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
    "scenes": ["integer"], // segment_ids where character appears
    "emotional_indicators": ["string"]
  }
}
```

## Processing Pipeline

### Sequential Flow

1. **Input**: Segmented text from existing pipeline
1. **Agent 1**: Classify dialogue vs narration
   - Update `utterances.dialogue_classification`
   - Update `utterances.dialogue_confidence`
1. **Agent 2**: Attribute speakers to dialogue
   - Create/update `characters` records
   - Create `character_text_segments` associations
   - Update `utterances.speaker_character_id`
1. **Profile Update**: Aggregate character data
   - Update `characters.profile` JSONB field
   - Maintain character relationship mappings

### Error Handling

- **Low Confidence Classifications**: Flag for manual review
- **Ambiguous Speaker Attribution**: Store multiple candidates
- **Character Name Conflicts**: Use disambiguation strategies
- **Processing Failures**: Rollback database changes

## Performance Requirements

### Throughput

- Process 1000 text segments per minute
- Handle books up to 500,000 words
- Support concurrent processing of multiple books

### Accuracy Targets

- Dialogue classification: >95% accuracy
- Speaker attribution: >85% accuracy for clear cases
- Character discovery: >90% recall for named characters

### Scalability

- Stateless agent design for horizontal scaling
- Database connection pooling
- Batch processing capabilities

## Integration Points

### LangFlow Components

- Input from existing segmentation pipeline
- Output to voice casting and TTS systems
- Integration with quality gates

### Database Integration

- Connection to existing PostgreSQL instance
- Transaction management for data consistency
- Migration scripts for schema updates

### Monitoring and Logging

- Agent processing metrics
- Classification accuracy tracking
- Performance monitoring
- Error rate tracking

## Testing Strategy

### Unit Tests

- Individual agent logic
- Database operations
- Schema validation

### Integration Tests

- Full pipeline processing
- Database consistency
- Error handling scenarios

### Performance Tests

- Load testing with large texts
- Memory usage profiling
- Database query optimization

## Implementation Phases

### Phase 1: Core Infrastructure

- Database schema implementation
- Basic agent frameworks
- Simple classification rules

### Phase 2: Agent Development

- Dialogue classifier implementation
- Speaker attribution logic
- Character discovery algorithms

### Phase 3: Profile Building

- Character data aggregation
- Profile schema implementation
- Relationship detection

### Phase 4: Optimization

- Performance tuning
- Advanced classification algorithms
- Quality improvements

## Success Criteria

1. **Functional Success**:

   - All dialogue segments classified with >95% accuracy
   - All characters discovered and tracked
   - Complete character profiles generated

1. **Technical Success**:

   - System processes target book sizes within performance requirements
   - Database maintains consistency under concurrent load
   - Integration with existing pipeline is seamless

1. **Business Success**:

   - Character data enables effective voice casting decisions
   - Profile quality supports TTS voice assignment
   - System scales to production book processing volumes
