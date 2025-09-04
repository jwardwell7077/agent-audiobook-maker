-- ABM Two-Agent System Database Schema
-- PostgreSQL initialization script for character tracking and dialogue classification
-- Database schema (initialization). Historical two-agent schema docs removed.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Books table (basic book metadata)
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    isbn VARCHAR(20),
    file_path TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chapters table (book structure)
CREATE TABLE IF NOT EXISTS chapters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title VARCHAR(500),
    content_hash VARCHAR(64),
    word_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, chapter_number)
);

-- Utterances table (segmented text with classification)
CREATE TABLE IF NOT EXISTS utterances (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    utterance_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    text_hash VARCHAR(64) NOT NULL,
    
    -- Agent 1: Dialogue Classification
    dialogue_classification VARCHAR(20) CHECK (dialogue_classification IN ('dialogue', 'narration', 'mixed')),
    classification_confidence FLOAT DEFAULT 0.0 CHECK (classification_confidence >= 0.0 AND classification_confidence <= 1.0),
    classification_method VARCHAR(20) CHECK (classification_method IN ('heuristic', 'ai_fallback', 'manual')),
    
    -- Context and metadata
    context_before TEXT,
    context_after TEXT,
    segment_metadata JSONB DEFAULT '{}'::JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(book_id, chapter_id, utterance_index)
);

-- Characters table (speaker identification and profiling)
CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255),
    aliases JSONB DEFAULT '[]'::JSONB,
    first_appearance_segment_id INTEGER REFERENCES utterances(id),
    character_type VARCHAR(50) DEFAULT 'person' CHECK (character_type IN ('person', 'narrator', 'group', 'unknown')),
    
    -- Character profiling for voice casting
    profile JSONB DEFAULT '{}'::JSONB,
    voice_characteristics JSONB DEFAULT '{}'::JSONB,
    
    -- Statistics
    dialogue_count INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(book_id, canonical_name)
);

-- Character text segments table (Agent 2: Speaker Attribution)
CREATE TABLE IF NOT EXISTS character_text_segments (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    utterance_id INTEGER NOT NULL REFERENCES utterances(id) ON DELETE CASCADE,
    segment_type VARCHAR(20) NOT NULL CHECK (segment_type IN ('dialogue', 'narration', 'reference')),
    relationship VARCHAR(50) CHECK (relationship IN ('speaker', 'addressee', 'reference', 'context')),
    
    -- Attribution confidence and method
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    attribution_method VARCHAR(20) CHECK (attribution_method IN ('heuristic', 'database_lookup', 'ai_inference', 'manual')),
    
    -- Context tracking
    context_before TEXT,
    context_after TEXT,
    attribution_metadata JSONB DEFAULT '{}'::JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing status tracking
CREATE TABLE IF NOT EXISTS processing_status (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    processing_stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    agent VARCHAR(50),
    error_message TEXT,
    processing_metadata JSONB DEFAULT '{}'::JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_utterances_book_chapter ON utterances(book_id, chapter_id);
CREATE INDEX IF NOT EXISTS idx_utterances_classification ON utterances(dialogue_classification);
CREATE INDEX IF NOT EXISTS idx_utterances_text_hash ON utterances(text_hash);

CREATE INDEX IF NOT EXISTS idx_characters_book_id ON characters(book_id);
CREATE INDEX IF NOT EXISTS idx_characters_canonical_name ON characters(canonical_name);
CREATE INDEX IF NOT EXISTS idx_characters_aliases ON characters USING GIN(aliases);

CREATE INDEX IF NOT EXISTS idx_character_segments_character ON character_text_segments(character_id);
CREATE INDEX IF NOT EXISTS idx_character_segments_utterance ON character_text_segments(utterance_id);
CREATE INDEX IF NOT EXISTS idx_character_segments_type ON character_text_segments(segment_type);

CREATE INDEX IF NOT EXISTS idx_processing_status_book ON processing_status(book_id);
CREATE INDEX IF NOT EXISTS idx_processing_status_stage ON processing_status(processing_stage, status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to all tables
CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chapters_updated_at BEFORE UPDATE ON chapters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_utterances_updated_at BEFORE UPDATE ON utterances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_characters_updated_at BEFORE UPDATE ON characters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_character_segments_updated_at BEFORE UPDATE ON character_text_segments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for development (optional)
INSERT INTO books (title, author, metadata) VALUES 
    ('Sample Book for Testing', 'Test Author', '{"genre": "fiction", "test_data": true}')
ON CONFLICT DO NOTHING;

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abm_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abm_user;
