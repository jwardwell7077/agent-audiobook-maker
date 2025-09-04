# Database Migration: Two-Agent Character Tracking System

## Migration Overview

This migration adds the necessary database schema changes to support the two-agent dialogue classification and speaker attribution system.

## Schema Changes

### 1. Create Characters Table

```sql
-- Create characters table for tracking book characters
CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255), -- normalized name for matching
    aliases JSONB DEFAULT '[]'::JSONB, -- array of alternative names/nicknames
    first_appearance_segment_id INTEGER, -- will reference utterances(id)
    character_type VARCHAR(50) DEFAULT 'person', -- person, narrator, group, etc.
    profile JSONB DEFAULT '{}'::JSONB, -- collected character traits and data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT characters_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT characters_book_name_unique UNIQUE (book_id, canonical_name)
);

-- Add indexes for performance
CREATE INDEX idx_characters_book_id ON characters(book_id);
CREATE INDEX idx_characters_canonical_name ON characters(canonical_name);
CREATE INDEX idx_characters_aliases ON characters USING GIN(aliases);
```

### 2. Create Character Text Segments Table

```sql
-- Create table to track all text segments associated with characters
CREATE TABLE IF NOT EXISTS character_text_segments (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    utterance_id INTEGER NOT NULL REFERENCES utterances(id) ON DELETE CASCADE,
    segment_type VARCHAR(20) NOT NULL, -- 'dialogue', 'about_character', 'context'
    relationship VARCHAR(50), -- 'speaker', 'mentioned', 'described_by', 'action_by'
    context_before TEXT, -- text context before the segment
    context_after TEXT, -- text context after the segment
    confidence_score FLOAT DEFAULT 0.0, -- agent confidence in association
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT cts_segment_type_valid CHECK (segment_type IN ('dialogue', 'about_character', 'context')),
    CONSTRAINT cts_confidence_valid CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT cts_character_utterance_unique UNIQUE (character_id, utterance_id, relationship)
);

-- Add indexes for performance
CREATE INDEX idx_cts_character_id ON character_text_segments(character_id);
CREATE INDEX idx_cts_utterance_id ON character_text_segments(utterance_id);
CREATE INDEX idx_cts_segment_type ON character_text_segments(segment_type);
CREATE INDEX idx_cts_relationship ON character_text_segments(relationship);
```

### 3. Extend Utterances Table

```sql
-- Add columns to existing utterances table for agent processing results
ALTER TABLE utterances
ADD COLUMN IF NOT EXISTS dialogue_classification VARCHAR(20), -- 'dialogue', 'narration', 'mixed'
ADD COLUMN IF NOT EXISTS dialogue_confidence FLOAT DEFAULT 0.0, -- classifier confidence
ADD COLUMN IF NOT EXISTS speaker_character_id INTEGER, -- resolved speaker character
ADD COLUMN IF NOT EXISTS speaker_confidence FLOAT DEFAULT 0.0, -- attribution confidence
ADD COLUMN IF NOT EXISTS processed_by_agents TIMESTAMP; -- when agents last processed

-- Add foreign key constraint for speaker_character_id
ALTER TABLE utterances
ADD CONSTRAINT fk_utterances_speaker_character
FOREIGN KEY (speaker_character_id) REFERENCES characters(id) ON DELETE SET NULL;

-- Add check constraints for new columns
ALTER TABLE utterances
ADD CONSTRAINT utterances_dialogue_class_valid
CHECK (dialogue_classification IN ('dialogue', 'narration', 'mixed') OR dialogue_classification IS NULL),
ADD CONSTRAINT utterances_dialogue_conf_valid
CHECK (dialogue_confidence >= 0.0 AND dialogue_confidence <= 1.0),
ADD CONSTRAINT utterances_speaker_conf_valid
CHECK (speaker_confidence >= 0.0 AND speaker_confidence <= 1.0);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_utterances_dialogue_classification ON utterances(dialogue_classification);
CREATE INDEX IF NOT EXISTS idx_utterances_speaker_character_id ON utterances(speaker_character_id);
CREATE INDEX IF NOT EXISTS idx_utterances_processed_by_agents ON utterances(processed_by_agents);
```

### 4. Add Foreign Key for First Appearance

```sql
-- Add foreign key constraint for first_appearance_segment_id
ALTER TABLE characters
ADD CONSTRAINT fk_characters_first_appearance
FOREIGN KEY (first_appearance_segment_id) REFERENCES utterances(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_characters_first_appearance ON characters(first_appearance_segment_id);
```

## Data Migration Considerations

### Profile JSONB Structure

The `characters.profile` JSONB field will store structured character data:

```json
{
  "dialogue_count": 0,
  "word_count": 0,
  "vocabulary_sample": [],
  "speech_patterns": {
    "common_phrases": [],
    "formality_level": "unknown",
    "dialect_markers": []
  },
  "descriptions": {
    "physical": [],
    "personality": [],
    "role": []
  },
  "relationships": {},
  "scenes": [],
  "emotional_indicators": []
}
```

### Aliases JSONB Structure

The `characters.aliases` JSONB field will store alternative names:

```json
[
  {"name": "Johnny", "type": "nickname", "confidence": 0.9},
  {"name": "Mr. Smith", "type": "formal", "confidence": 0.8},
  {"name": "Dad", "type": "relationship", "confidence": 0.7}
]
```

## Performance Considerations

### Indexes

All critical indexes are created as part of the migration:

- Characters table: book_id, canonical_name, aliases (GIN)
- Character text segments: character_id, utterance_id, segment_type
- Utterances extensions: dialogue_classification, speaker_character_id

### Query Optimization

Common query patterns to optimize for:

1. **Character lookup by book**: `SELECT * FROM characters WHERE book_id = ?`
1. **Character dialogue**: `SELECT * FROM character_text_segments WHERE character_id = ? AND segment_type = 'dialogue'`
1. **Unprocessed utterances**: `SELECT * FROM utterances WHERE processed_by_agents IS NULL`

## Rollback Plan

```sql
-- Rollback script (run in reverse order)

-- Remove foreign key constraints
ALTER TABLE characters DROP CONSTRAINT IF EXISTS fk_characters_first_appearance;
ALTER TABLE utterances DROP CONSTRAINT IF EXISTS fk_utterances_speaker_character;

-- Remove added columns from utterances
ALTER TABLE utterances
DROP COLUMN IF EXISTS dialogue_classification,
DROP COLUMN IF EXISTS dialogue_confidence,
DROP COLUMN IF EXISTS speaker_character_id,
DROP COLUMN IF EXISTS speaker_confidence,
DROP COLUMN IF EXISTS processed_by_agents;

-- Drop tables (in dependency order)
DROP TABLE IF EXISTS character_text_segments;
DROP TABLE IF EXISTS characters;

-- Drop indexes (will be dropped with tables, but listed for completeness)
DROP INDEX IF EXISTS idx_characters_book_id;
DROP INDEX IF EXISTS idx_characters_canonical_name;
DROP INDEX IF EXISTS idx_characters_aliases;
DROP INDEX IF EXISTS idx_cts_character_id;
DROP INDEX IF EXISTS idx_cts_utterance_id;
DROP INDEX IF EXISTS idx_cts_segment_type;
DROP INDEX IF EXISTS idx_utterances_dialogue_classification;
DROP INDEX IF EXISTS idx_utterances_speaker_character_id;
```

## Validation Queries

After migration, run these queries to validate the schema:

```sql
-- Verify tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('characters', 'character_text_segments');

-- Verify utterances columns added
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'utterances'
AND column_name IN ('dialogue_classification', 'speaker_character_id');

-- Verify constraints
SELECT constraint_name, constraint_type FROM information_schema.table_constraints
WHERE table_schema = 'public'
AND table_name IN ('characters', 'character_text_segments', 'utterances');

-- Verify indexes
SELECT indexname FROM pg_indexes
WHERE tablename IN ('characters', 'character_text_segments', 'utterances')
AND schemaname = 'public';
```

## Migration Execution

1. **Backup Database**: Create full backup before running migration
1. **Run in Transaction**: Execute all DDL in a single transaction for atomicity
1. **Validate Schema**: Run validation queries to confirm changes
1. **Test Queries**: Execute sample queries to verify performance
1. **Monitor Performance**: Check query execution plans after deployment
