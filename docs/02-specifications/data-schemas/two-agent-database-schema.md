# Two-Agent System Data Model Specifications

## Database Schema Design

### Entity Relationship Overview

The two-agent system uses a relational database model with PostgreSQL and JSONB fields for flexible character profile storage.

### Core Tables

#### 1. Books Table (Existing)

```sql
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(20),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_books_author ON books(author);
CREATE INDEX idx_books_metadata ON books USING GIN(metadata);
```

#### 2. Chapters Table (Existing)

```sql
CREATE TABLE chapters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_index INTEGER NOT NULL,
    title VARCHAR(255),
    body_text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(book_id, chapter_index)
);

-- Indexes
CREATE INDEX idx_chapters_book_id ON chapters(book_id);
CREATE INDEX idx_chapters_index ON chapters(book_id, chapter_index);
```

#### 3. Enhanced Utterances Table

```sql
CREATE TABLE utterances (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    
    -- Core content
    text TEXT NOT NULL,
    position_in_chapter INTEGER NOT NULL,
    word_count INTEGER DEFAULT 0,
    character_count INTEGER DEFAULT 0,
    
    -- Agent 1 results (Dialogue Classification)
    dialogue_classification VARCHAR(20), -- 'dialogue', 'narration', 'mixed'
    dialogue_confidence FLOAT DEFAULT 0.0,
    classification_method VARCHAR(20), -- 'heuristic', 'ai', 'hybrid'
    classification_reasoning TEXT,
    
    -- Agent 2 results (Speaker Attribution)  
    speaker_character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    speaker_confidence FLOAT DEFAULT 0.0,
    attribution_method VARCHAR(20), -- 'direct', 'contextual', 'inferred'
    attribution_reasoning TEXT,
    
    -- Processing metadata
    processed_by_agents TIMESTAMP,
    processing_version VARCHAR(10) DEFAULT '1.0',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT utterances_dialogue_class_valid 
        CHECK (dialogue_classification IN ('dialogue', 'narration', 'mixed') OR dialogue_classification IS NULL),
    CONSTRAINT utterances_dialogue_conf_valid 
        CHECK (dialogue_confidence >= 0.0 AND dialogue_confidence <= 1.0),
    CONSTRAINT utterances_speaker_conf_valid 
        CHECK (speaker_confidence >= 0.0 AND speaker_confidence <= 1.0),
    CONSTRAINT utterances_position_positive
        CHECK (position_in_chapter > 0)
);

-- Indexes for performance
CREATE INDEX idx_utterances_book_id ON utterances(book_id);
CREATE INDEX idx_utterances_chapter_id ON utterances(chapter_id);
CREATE INDEX idx_utterances_position ON utterances(chapter_id, position_in_chapter);
CREATE INDEX idx_utterances_dialogue_class ON utterances(dialogue_classification);
CREATE INDEX idx_utterances_speaker_id ON utterances(speaker_character_id);
CREATE INDEX idx_utterances_unprocessed ON utterances(book_id, processed_by_agents) 
    WHERE processed_by_agents IS NULL;
```

#### 4. Characters Table (New)

```sql
CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    
    -- Character identification
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL, -- normalized form for matching
    display_name VARCHAR(255), -- preferred display form
    
    -- Character classification
    character_type VARCHAR(50) DEFAULT 'person', -- 'person', 'narrator', 'group', 'entity'
    importance_level VARCHAR(20) DEFAULT 'unknown', -- 'major', 'minor', 'background'
    
    -- Aliases and alternative names (JSONB for flexibility)
    aliases JSONB DEFAULT '[]'::JSONB,
    /* Alias structure:
    [
        {"name": "Johnny", "type": "nickname", "confidence": 0.9, "first_used_segment": 123},
        {"name": "Mr. Smith", "type": "formal", "confidence": 0.8, "context": "work"},
        {"name": "Dad", "type": "relationship", "confidence": 0.7, "used_by": ["Mary", "Tom"]}
    ]
    */
    
    -- Character profile (JSONB for flexible schema evolution)
    profile JSONB DEFAULT '{}'::JSONB,
    /* Profile structure documented below */
    
    -- First appearance tracking
    first_appearance_segment_id INTEGER,
    first_mention_chapter_id INTEGER REFERENCES chapters(id),
    
    -- Statistics (updated by triggers or batch processes)
    dialogue_count INTEGER DEFAULT 0,
    mention_count INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT characters_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT characters_canonical_not_empty CHECK (length(trim(canonical_name)) > 0),
    CONSTRAINT characters_book_canonical_unique UNIQUE (book_id, canonical_name),
    CONSTRAINT characters_type_valid 
        CHECK (character_type IN ('person', 'narrator', 'group', 'entity', 'unknown')),
    CONSTRAINT characters_importance_valid 
        CHECK (importance_level IN ('major', 'minor', 'background', 'unknown'))
);

-- Indexes
CREATE INDEX idx_characters_book_id ON characters(book_id);
CREATE INDEX idx_characters_canonical_name ON characters(canonical_name);
CREATE INDEX idx_characters_name ON characters(name);
CREATE INDEX idx_characters_aliases ON characters USING GIN(aliases);
CREATE INDEX idx_characters_profile ON characters USING GIN(profile);
CREATE INDEX idx_characters_type ON characters(character_type);
CREATE INDEX idx_characters_first_appearance ON characters(first_appearance_segment_id);

-- Add foreign key constraint after utterances table exists
ALTER TABLE characters 
ADD CONSTRAINT fk_characters_first_appearance 
FOREIGN KEY (first_appearance_segment_id) REFERENCES utterances(id) ON DELETE SET NULL;
```

#### 5. Character Text Segments Table (New)

```sql
CREATE TABLE character_text_segments (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    utterance_id INTEGER NOT NULL REFERENCES utterances(id) ON DELETE CASCADE,
    
    -- Relationship type
    segment_type VARCHAR(20) NOT NULL, -- 'dialogue', 'about_character', 'context', 'action'
    relationship VARCHAR(50) NOT NULL, -- 'speaker', 'addressee', 'mentioned', 'described_by', 'action_by'
    
    -- Context preservation
    context_before TEXT, -- text immediately before this segment
    context_after TEXT, -- text immediately after this segment
    
    -- Agent confidence and reasoning
    confidence_score FLOAT DEFAULT 0.0,
    detection_method VARCHAR(30), -- 'dialogue_tag', 'contextual', 'pattern_match', 'ai_inference'
    reasoning TEXT, -- explanation of why this association was made
    
    -- Additional context data (JSONB for flexibility)
    context_data JSONB DEFAULT '{}'::JSONB,
    /* Context data structure:
    {
        "dialogue_tag": "said Mary",
        "position_in_text": "after_quote",
        "other_characters_present": ["Quinn", "John"],
        "scene_type": "conversation",
        "emotional_context": "tense",
        "speaking_style": "formal"
    }
    */
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT cts_segment_type_valid 
        CHECK (segment_type IN ('dialogue', 'about_character', 'context', 'action')),
    CONSTRAINT cts_relationship_valid 
        CHECK (relationship IN ('speaker', 'addressee', 'mentioned', 'described_by', 'action_by', 'referenced')),
    CONSTRAINT cts_confidence_valid 
        CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT cts_character_utterance_relationship_unique 
        UNIQUE (character_id, utterance_id, relationship)
);

-- Indexes
CREATE INDEX idx_cts_character_id ON character_text_segments(character_id);
CREATE INDEX idx_cts_utterance_id ON character_text_segments(utterance_id);
CREATE INDEX idx_cts_segment_type ON character_text_segments(segment_type);
CREATE INDEX idx_cts_relationship ON character_text_segments(relationship);
CREATE INDEX idx_cts_confidence ON character_text_segments(confidence_score);
CREATE INDEX idx_cts_context_data ON character_text_segments USING GIN(context_data);
```

### Character Profile JSONB Schema

The `characters.profile` JSONB field stores comprehensive character information:

```json
{
    "basic_info": {
        "age": "unknown",
        "gender": "unknown", 
        "occupation": [],
        "relationships": {
            "family": [],
            "friends": [],
            "enemies": [],
            "romantic": []
        }
    },
    "physical_description": {
        "height": "unknown",
        "build": "unknown",
        "hair": "unknown",
        "eyes": "unknown",
        "distinguishing_features": [],
        "clothing_style": []
    },
    "personality": {
        "traits": [],
        "habits": [],
        "fears": [],
        "goals": [],
        "values": []
    },
    "speech_patterns": {
        "vocabulary_level": "unknown", -- formal, casual, mixed
        "common_phrases": [],
        "dialect_markers": [],
        "speech_style": "unknown", -- verbose, terse, eloquent, etc.
        "emotional_range": []
    },
    "dialogue_statistics": {
        "total_words": 0,
        "average_sentence_length": 0.0,
        "vocabulary_richness": 0.0,
        "most_common_words": [],
        "emotional_tone_distribution": {
            "happy": 0,
            "sad": 0,
            "angry": 0,
            "neutral": 0,
            "excited": 0
        }
    },
    "scene_presence": {
        "chapters_appeared": [],
        "total_segments": 0,
        "dialogue_segments": 0,
        "mentioned_segments": 0,
        "scene_types": [] -- indoor, outdoor, action, conversation, etc.
    },
    "character_interactions": {
        "speaks_to": {}, -- character_id: count
        "mentioned_by": {}, -- character_id: count
        "in_scene_with": {}, -- character_id: count
        "relationship_indicators": [] -- textual evidence of relationships
    },
    "voice_casting_data": {
        "suggested_voice_type": "unknown", -- deep, high, raspy, smooth, etc.
        "age_range": "unknown",
        "accent_hints": [],
        "speaking_pace": "unknown", -- fast, slow, measured
        "volume_tendency": "unknown", -- quiet, loud, variable
        "emotional_range": "unknown" -- expressive, monotone, varied
    },
    "narrative_role": {
        "protagonist": false,
        "antagonist": false,
        "supporting": false,
        "comic_relief": false,
        "mentor": false,
        "love_interest": false,
        "role_confidence": 0.0
    },
    "metadata": {
        "last_profile_update": "timestamp",
        "profile_completeness": 0.0, -- 0.0 to 1.0
        "data_sources": ["dialogue", "descriptions", "actions", "mentions"],
        "confidence_score": 0.0,
        "needs_review": false,
        "review_reasons": []
    }
}
```

### Data Processing Views

#### Character Summary View

```sql
CREATE VIEW character_summary AS
SELECT 
    c.id,
    c.book_id,
    c.name,
    c.canonical_name,
    c.character_type,
    c.dialogue_count,
    c.mention_count,
    c.total_word_count,
    
    -- Profile extracts
    c.profile->>'basic_info'->>'gender' as gender,
    c.profile->>'basic_info'->>'age' as age,
    c.profile->>'personality'->>'traits' as personality_traits,
    c.profile->>'voice_casting_data'->>'suggested_voice_type' as voice_type,
    
    -- Statistics
    COUNT(cts.id) as total_text_associations,
    COUNT(CASE WHEN cts.relationship = 'speaker' THEN 1 END) as speaking_instances,
    COUNT(CASE WHEN cts.relationship = 'mentioned' THEN 1 END) as mention_instances,
    
    c.created_at,
    c.updated_at
    
FROM characters c
LEFT JOIN character_text_segments cts ON c.id = cts.character_id
GROUP BY c.id;
```

#### Dialogue Analysis View

```sql
CREATE VIEW character_dialogue_analysis AS
SELECT 
    c.id as character_id,
    c.name,
    COUNT(cts.id) as dialogue_segments,
    AVG(u.word_count) as avg_words_per_segment,
    STRING_AGG(DISTINCT u.dialogue_classification, ', ') as dialogue_types,
    AVG(cts.confidence_score) as avg_attribution_confidence,
    
    -- Recent dialogue sample
    ARRAY_AGG(u.text ORDER BY u.created_at DESC)[:5] as recent_dialogue_sample
    
FROM characters c
JOIN character_text_segments cts ON c.id = cts.character_id
JOIN utterances u ON cts.utterance_id = u.id
WHERE cts.relationship = 'speaker'
  AND u.dialogue_classification IN ('dialogue', 'mixed')
GROUP BY c.id, c.name;
```

### Data Migration Strategy

#### Migration Script Structure

```sql
-- Migration: Add Two-Agent System Tables
-- Version: 2.0.0
-- Date: 2025-08-23

BEGIN;

-- Create new tables
\i create_characters_table.sql
\i create_character_text_segments_table.sql

-- Modify existing tables
\i modify_utterances_table.sql

-- Create indexes
\i create_indexes.sql

-- Create views
\i create_views.sql

-- Insert initial data
\i seed_character_types.sql

-- Validate migration
SELECT 'Migration completed successfully' as status;

COMMIT;
```

### Performance Optimization

#### Query Optimization Strategies

1. **Character Lookup Optimization**

```sql
-- Optimized character search with aliases
CREATE OR REPLACE FUNCTION find_character(
    p_book_id INTEGER,
    p_name TEXT
) RETURNS TABLE(character_id INTEGER, match_type TEXT, confidence FLOAT) AS $$
BEGIN
    -- Direct name match (highest priority)
    RETURN QUERY
    SELECT c.id, 'exact_name'::TEXT, 1.0::FLOAT
    FROM characters c
    WHERE c.book_id = p_book_id 
      AND (c.name = p_name OR c.canonical_name = p_name OR c.display_name = p_name);
    
    -- If no direct match, check aliases
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT c.id, 'alias_match'::TEXT, (alias->>'confidence')::FLOAT
        FROM characters c,
             jsonb_array_elements(c.aliases) as alias
        WHERE c.book_id = p_book_id
          AND alias->>'name' = p_name
        ORDER BY (alias->>'confidence')::FLOAT DESC
        LIMIT 1;
    END IF;
    
    -- If still no match, fuzzy search
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT c.id, 'fuzzy_match'::TEXT, similarity(c.name, p_name)::FLOAT
        FROM characters c
        WHERE c.book_id = p_book_id
          AND similarity(c.name, p_name) > 0.6
        ORDER BY similarity(c.name, p_name) DESC
        LIMIT 1;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

2. **Batch Processing Optimization**

```sql
-- Batch update character statistics
CREATE OR REPLACE FUNCTION update_character_statistics(p_character_ids INTEGER[]) 
RETURNS VOID AS $$
BEGIN
    UPDATE characters 
    SET 
        dialogue_count = stats.dialogue_count,
        mention_count = stats.mention_count,
        total_word_count = stats.total_words,
        updated_at = CURRENT_TIMESTAMP
    FROM (
        SELECT 
            cts.character_id,
            COUNT(CASE WHEN cts.relationship = 'speaker' THEN 1 END) as dialogue_count,
            COUNT(CASE WHEN cts.relationship = 'mentioned' THEN 1 END) as mention_count,
            SUM(u.word_count) as total_words
        FROM character_text_segments cts
        JOIN utterances u ON cts.utterance_id = u.id
        WHERE cts.character_id = ANY(p_character_ids)
        GROUP BY cts.character_id
    ) stats
    WHERE characters.id = stats.character_id;
END;
$$ LANGUAGE plpgsql;
```

### Data Validation Rules

#### Consistency Checks

```sql
-- Ensure character-utterance associations are valid
CREATE OR REPLACE FUNCTION validate_character_associations() 
RETURNS TABLE(issue_type TEXT, character_id INTEGER, utterance_id INTEGER, description TEXT) AS $$
BEGIN
    -- Check for orphaned character associations
    RETURN QUERY
    SELECT 
        'orphaned_association'::TEXT,
        cts.character_id,
        cts.utterance_id,
        'Character text segment references non-existent character or utterance'::TEXT
    FROM character_text_segments cts
    LEFT JOIN characters c ON cts.character_id = c.id
    LEFT JOIN utterances u ON cts.utterance_id = u.id
    WHERE c.id IS NULL OR u.id IS NULL;
    
    -- Check for inconsistent speaker attributions
    RETURN QUERY
    SELECT 
        'inconsistent_speaker'::TEXT,
        cts.character_id,
        cts.utterance_id,
        'Utterance speaker_character_id differs from character_text_segments speaker relationship'::TEXT
    FROM character_text_segments cts
    JOIN utterances u ON cts.utterance_id = u.id
    WHERE cts.relationship = 'speaker'
      AND (u.speaker_character_id != cts.character_id OR u.speaker_character_id IS NULL);
      
    -- Check for duplicate speaker assignments
    RETURN QUERY
    SELECT 
        'duplicate_speaker'::TEXT,
        cts1.character_id,
        cts1.utterance_id,
        'Multiple characters marked as speaker for same utterance'::TEXT
    FROM character_text_segments cts1
    JOIN character_text_segments cts2 ON cts1.utterance_id = cts2.utterance_id
    WHERE cts1.id != cts2.id
      AND cts1.relationship = 'speaker'
      AND cts2.relationship = 'speaker';
END;
$$ LANGUAGE plpgsql;
```

### Backup and Recovery Considerations

#### Character Data Backup Strategy

```sql
-- Export character data for backup
CREATE OR REPLACE FUNCTION export_character_data(p_book_id INTEGER)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'book_id', p_book_id,
        'export_timestamp', CURRENT_TIMESTAMP,
        'characters', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'character', row_to_json(c),
                    'text_segments', (
                        SELECT jsonb_agg(row_to_json(cts))
                        FROM character_text_segments cts
                        WHERE cts.character_id = c.id
                    )
                )
            )
            FROM characters c
            WHERE c.book_id = p_book_id
        )
    ) INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

This comprehensive data model provides the foundation for the two-agent system with proper normalization, performance optimization, and flexibility for character profile evolution.
