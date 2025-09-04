# [DEPRECATED] Two-Agent System Database Schema Diagrams

> Deprecated terminology and scope. Database-backed character tracking is not part of the current spans-first pipeline; this page remains for historical context only.

## Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    books ||--o{ characters : "contains"
    books ||--o{ utterances : "has"
    characters ||--o{ character_aliases : "has"
    characters ||--o{ character_text_associations : "linked_to"
    utterances ||--o{ character_text_associations : "associated_with"
    characters ||--o{ character_interactions : "participates_in"
    characters ||--o{ character_scene_presence : "appears_in"

    books {
        serial id PK
        varchar title
        varchar author
        varchar isbn
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    characters {
        serial id PK
        int book_id FK
        varchar name
        varchar canonical_name
        varchar display_name
        varchar character_type
        varchar importance_level
        jsonb profile
        int first_appearance_segment_id
        int dialogue_count
        int mention_count
        int total_word_count
        timestamp created_at
        timestamp updated_at
    }

    character_aliases {
        serial id PK
        int character_id FK
        varchar alias_name
        varchar alias_type
        float confidence
        varchar context
        int first_used_segment
        int usage_count
        timestamp created_at
    }

    utterances {
        varchar id PK
        int book_id FK
        int chapter_id
        int position_in_chapter
        text content
        varchar classification
        float classification_confidence
        varchar classification_method
        jsonb dialogue_portions
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    character_text_associations {
        serial id PK
        int character_id FK
        varchar utterance_id FK
        varchar segment_type
        varchar relationship
        float confidence_score
        varchar detection_method
        text reasoning
        text context_before
        text context_after
        jsonb context_data
        timestamp created_at
        timestamp updated_at
    }

    character_interactions {
        serial id PK
        int character1_id FK
        int character2_id FK
        int book_id FK
        varchar interaction_type
        int interaction_count
        varchar first_interaction_segment
        varchar last_interaction_segment
        jsonb interaction_details
        timestamp created_at
        timestamp updated_at
    }

    character_scene_presence {
        serial id PK
        int character_id FK
        int book_id FK
        int chapter_id
        varchar segment_id
        varchar presence_type
        int word_count_in_segment
        timestamp created_at
    }
```

## Detailed Table Schema Diagrams

### Core Entity Tables

```mermaid
graph TB
    subgraph "Books Table"
        BooksTable[
            <b>books</b><br/>
            ────────────────<br/>
            🔑 id: SERIAL PRIMARY KEY<br/>
            📖 title: VARCHAR(500) NOT NULL<br/>
            ✍️ author: VARCHAR(200)<br/>
            📚 isbn: VARCHAR(20)<br/>
            🏷️ genre: VARCHAR(100)<br/>
            📄 total_pages: INTEGER<br/>
            📊 metadata: JSONB<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()<br/>
            🔄 updated_at: TIMESTAMP DEFAULT NOW()
        ]
    end

    subgraph "Characters Table"  
        CharsTable[
            <b>characters</b><br/>
            ────────────────<br/>
            🔑 id: SERIAL PRIMARY KEY<br/>
            📚 book_id: INTEGER NOT NULL → books(id)<br/>
            👤 name: VARCHAR(200) NOT NULL<br/>
            📝 canonical_name: VARCHAR(200)<br/>
            🎭 display_name: VARCHAR(200)<br/>
            🏷️ character_type: VARCHAR(50) DEFAULT 'person'<br/>
            ⭐ importance_level: VARCHAR(20) DEFAULT 'unknown'<br/>
            👥 profile: JSONB<br/>
            📍 first_appearance_segment_id: INTEGER<br/>
            💬 dialogue_count: INTEGER DEFAULT 0<br/>
            📣 mention_count: INTEGER DEFAULT 0<br/>
            📝 total_word_count: INTEGER DEFAULT 0<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()<br/>
            🔄 updated_at: TIMESTAMP DEFAULT NOW()
        ]
    end

    subgraph "Utterances Table"
        UtterTable[
            <b>utterances</b><br/>
            ────────────────<br/>
            🔑 id: VARCHAR(100) PRIMARY KEY<br/>
            📚 book_id: INTEGER NOT NULL → books(id)<br/>
            📖 chapter_id: INTEGER<br/>
            📍 position_in_chapter: INTEGER<br/>
            📝 content: TEXT NOT NULL<br/>
            🏷️ classification: VARCHAR(20)<br/>
            🎯 classification_confidence: FLOAT<br/>
            🔧 classification_method: VARCHAR(50)<br/>
            💬 dialogue_portions: JSONB<br/>
            📊 metadata: JSONB<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()<br/>
            🔄 updated_at: TIMESTAMP DEFAULT NOW()
        ]
    end

    BooksTable --> CharsTable
    BooksTable --> UtterTable
```

### Association and Relationship Tables

```mermaid
graph TB
    subgraph "Character Aliases Table"
        AliasTable[
            <b>character_aliases</b><br/>
            ────────────────<br/>
            🔑 id: SERIAL PRIMARY KEY<br/>
            👤 character_id: INTEGER NOT NULL → characters(id)<br/>
            📝 alias_name: VARCHAR(200) NOT NULL<br/>
            🏷️ alias_type: VARCHAR(50)<br/>
            🎯 confidence: FLOAT NOT NULL<br/>
            📝 context: TEXT<br/>
            📍 first_used_segment: INTEGER<br/>
            📊 usage_count: INTEGER DEFAULT 0<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()
        ]
    end

    subgraph "Character Text Associations Table"
        AssocTable[
            <b>character_text_associations</b><br/>
            ────────────────<br/>
            🔑 id: SERIAL PRIMARY KEY<br/>
            👤 character_id: INTEGER NOT NULL → characters(id)<br/>
            💬 utterance_id: VARCHAR(100) NOT NULL → utterances(id)<br/>
            📝 segment_type: VARCHAR(20)<br/>
            🔗 relationship: VARCHAR(50) NOT NULL<br/>
            🎯 confidence_score: FLOAT NOT NULL<br/>
            🔧 detection_method: VARCHAR(100)<br/>
            📝 reasoning: TEXT<br/>
            📖 context_before: TEXT<br/>
            📖 context_after: TEXT<br/>
            📊 context_data: JSONB<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()<br/>
            🔄 updated_at: TIMESTAMP DEFAULT NOW()
        ]
    end

    subgraph "Character Interactions Table"
        InteractTable[
            <b>character_interactions</b><br/>
            ────────────────<br/>
            🔑 id: SERIAL PRIMARY KEY<br/>
            👤 character1_id: INTEGER NOT NULL → characters(id)<br/>
            👥 character2_id: INTEGER NOT NULL → characters(id)<br/>
            📚 book_id: INTEGER NOT NULL → books(id)<br/>
            🏷️ interaction_type: VARCHAR(50)<br/>
            📊 interaction_count: INTEGER DEFAULT 1<br/>
            📍 first_interaction_segment: VARCHAR(100)<br/>
            📍 last_interaction_segment: VARCHAR(100)<br/>
            📊 interaction_details: JSONB<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()<br/>
            🔄 updated_at: TIMESTAMP DEFAULT NOW()
        ]
    end

    subgraph "Character Scene Presence Table"
        PresenceTable[
            <b>character_scene_presence</b><br/>
            ────────────────<br/>
            🔑 id: SERIAL PRIMARY KEY<br/>
            👤 character_id: INTEGER NOT NULL → characters(id)<br/>
            📚 book_id: INTEGER NOT NULL → books(id)<br/>
            📖 chapter_id: INTEGER<br/>
            📍 segment_id: VARCHAR(100)<br/>
            👁️ presence_type: VARCHAR(20)<br/>
            📊 word_count_in_segment: INTEGER<br/>
            ⏰ created_at: TIMESTAMP DEFAULT NOW()
        ]
    end
```

## Database Indexes and Performance Schema

```mermaid
graph TD
    subgraph "Primary Indexes"
        PK1[books.id - PRIMARY KEY]
        PK2[characters.id - PRIMARY KEY]
        PK3[utterances.id - PRIMARY KEY]
        PK4[character_aliases.id - PRIMARY KEY]
        PK5[character_text_associations.id - PRIMARY KEY]
    end

    subgraph "Foreign Key Indexes"
        FK1[characters.book_id - INDEX]
        FK2[utterances.book_id - INDEX]
        FK3[character_aliases.character_id - INDEX]
        FK4[character_text_associations.character_id - INDEX]
        FK5[character_text_associations.utterance_id - INDEX]
    end

    subgraph "Search and Query Indexes"
        SI1[characters.name - INDEX]
        SI2[characters.canonical_name - INDEX]
        SI3[character_aliases.alias_name - INDEX]
        SI4[utterances.classification - INDEX]
        SI5[character_text_associations.relationship - INDEX]
        SI6[character_text_associations.confidence_score - INDEX]
    end

    subgraph "Composite Indexes"
        CI1[characters(book_id, name) - UNIQUE]
        CI2[character_aliases(character_id, alias_name) - UNIQUE]
        CI3[utterances(book_id, chapter_id, position_in_chapter) - INDEX]
        CI4[character_text_associations(character_id, relationship) - INDEX]
        CI5[character_interactions(character1_id, character2_id) - UNIQUE]
    end

    subgraph "JSONB Indexes"
        JI1[characters.profile - GIN INDEX]
        JI2[utterances.metadata - GIN INDEX]
        JI3[utterances.dialogue_portions - GIN INDEX]
        JI4[character_text_associations.context_data - GIN INDEX]
    end

    subgraph "Performance Monitoring"
        PM1[Query Execution Stats]
        PM2[Index Usage Statistics]
        PM3[Table Size Monitoring]
        PM4[Connection Pool Metrics]
    end
```

## Character Profile JSONB Schema

```mermaid
graph TB
    subgraph "Character Profile JSONB Structure"
        ProfileRoot[character.profile: JSONB]

        BasicInfo[basic_info:<br/>- age: string<br/>- gender: string<br/>- occupation: array<br/>- title: string<br/>- family_status: string<br/>- social_class: string]

        PhysDesc[physical_description:<br/>- height: string<br/>- build: string<br/>- hair: string<br/>- eyes: string<br/>- distinguishing_features: array<br/>- clothing_style: string]

        Personality[personality:<br/>- traits: array<br/>- temperament: string<br/>- motivations: array<br/>- fears: array<br/>- values: array<br/>- flaws: array]

        SpeechPatterns[speech_patterns:<br/>- vocabulary_level: string<br/>- common_phrases: array<br/>- dialect_markers: array<br/>- formality_level: string<br/>- emotional_range: array<br/>- speech_tempo: string]

        DialogueStats[dialogue_statistics:<br/>- total_words: integer<br/>- total_segments: integer<br/>- avg_words_per_segment: float<br/>- vocabulary_richness: float<br/>- most_common_words: array<br/>- emotional_tone_distribution: object<br/>- question_ratio: float<br/>- exclamation_ratio: float]

        ScenePresence[scene_presence:<br/>- chapters_appeared: array<br/>- total_segments: integer<br/>- first_appearance: string<br/>- last_appearance: string<br/>- presence_density: float]

        Interactions[character_interactions:<br/>- speaks_to: object<br/>- addressed_by: object<br/>- mentioned_with: object<br/>- relationship_hints: object]

        VoiceCasting[voice_casting_data:<br/>- estimated_age: string<br/>- gender_presentation: string<br/>- accent_hints: array<br/>- vocal_characteristics: array<br/>- emotional_range: string<br/>- formality_preference: string<br/>- casting_notes: string]

        NarrativeRole[narrative_role:<br/>- role_type: string<br/>- importance_arc: array<br/>- character_development: object<br/>- plot_relevance: string]

        Metadata[metadata:<br/>- profile_completeness: float<br/>- last_updated: timestamp<br/>- data_sources: array<br/>- confidence_scores: object<br/>- review_flags: array]
    end

    ProfileRoot --> BasicInfo
    ProfileRoot --> PhysDesc
    ProfileRoot --> Personality
    ProfileRoot --> SpeechPatterns
    ProfileRoot --> DialogueStats
    ProfileRoot --> ScenePresence
    ProfileRoot --> Interactions
    ProfileRoot --> VoiceCasting
    ProfileRoot --> NarrativeRole
    ProfileRoot --> Metadata
```

## Database Migration Schema

```mermaid
flowchart TD
    subgraph "Migration Strategy"
        M1[Migration 001: Core Tables<br/>- Create books table<br/>- Create characters table<br/>- Create utterances table<br/>- Add basic constraints]

        M2[Migration 002: Aliases<br/>- Create character_aliases table<br/>- Add foreign key constraints<br/>- Create search indexes]

        M3[Migration 003: Associations<br/>- Create character_text_associations<br/>- Add relationship constraints<br/>- Create composite indexes]

        M4[Migration 004: Interactions<br/>- Create character_interactions<br/>- Create character_scene_presence<br/>- Add performance indexes]

        M5[Migration 005: JSONB Optimization<br/>- Add GIN indexes for JSONB<br/>- Create partial indexes<br/>- Add check constraints]

        M6[Migration 006: Performance Tuning<br/>- Add query-specific indexes<br/>- Create materialized views<br/>- Set up connection pooling]

        Rollback1[Rollback Scripts<br/>- Drop constraints first<br/>- Drop indexes<br/>- Drop tables in reverse order]
    end

    subgraph "Data Validation"
        V1[Constraint Validation<br/>- NOT NULL constraints<br/>- FOREIGN KEY integrity<br/>- UNIQUE constraints<br/>- CHECK constraints]

        V2[JSONB Schema Validation<br/>- Required field validation<br/>- Data type validation<br/>- Nested object constraints]

        V3[Business Logic Validation<br/>- Character name uniqueness<br/>- Confidence score ranges<br/>- Relationship type validation]
    end

    subgraph "Data Seeding"
        S1[Test Data Seeding<br/>- Sample book data<br/>- Character examples<br/>- Test utterances<br/>- Development fixtures]

        S2[Reference Data<br/>- Character types<br/>- Relationship types<br/>- Classification categories<br/>- Default configurations]
    end

    M1 --> M2
    M2 --> M3
    M3 --> M4
    M4 --> M5
    M5 --> M6

    M6 --> V1
    V1 --> V2
    V2 --> V3

    V3 --> S1
    S1 --> S2

    M6 -.-> Rollback1
```

## Database Connection and Pooling Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        App1[LangFlow Component 1]
        App2[LangFlow Component 2]
        App3[Background Processor]
        App4[API Service]
    end

    subgraph "Connection Pool Layer"
        PoolManager[Connection Pool Manager<br/>- Max connections: 20<br/>- Min connections: 5<br/>- Connection timeout: 30s<br/>- Idle timeout: 300s]

        Pool1[Pool 1: Read Operations<br/>- Size: 10<br/>- Character lookups<br/>- Profile queries]

        Pool2[Pool 2: Write Operations<br/>- Size: 8<br/>- Character creation<br/>- Association updates]

        Pool3[Pool 3: Batch Operations<br/>- Size: 2<br/>- Bulk inserts<br/>- Statistics updates]
    end

    subgraph "Database Layer"
        PrimDB[(PostgreSQL Primary<br/>- Write operations<br/>- Consistency critical)]

        ReadReplica1[(Read Replica 1<br/>- Character lookups<br/>- Profile queries)]

        ReadReplica2[(Read Replica 2<br/>- Statistics queries<br/>- Reporting)]

        BackupDB[(Backup Database<br/>- Point-in-time recovery<br/>- Disaster recovery)]
    end

    subgraph "Caching Layer"
        RedisCache[(Redis Cache<br/>- Character cache<br/>- Query result cache<br/>- Session data)]

        MemCache[In-Memory Cache<br/>- Frequently accessed characters<br/>- Recent associations<br/>- LRU eviction]
    end

    App1 --> PoolManager
    App2 --> PoolManager
    App3 --> PoolManager
    App4 --> PoolManager

    PoolManager --> Pool1
    PoolManager --> Pool2
    PoolManager --> Pool3

    Pool1 --> ReadReplica1
    Pool1 --> ReadReplica2
    Pool2 --> PrimDB
    Pool3 --> PrimDB

    PrimDB --> ReadReplica1
    PrimDB --> ReadReplica2
    PrimDB --> BackupDB

    Pool1 <--> RedisCache
    Pool2 <--> RedisCache
    App1 <--> MemCache
    App2 <--> MemCache
```

## Query Performance Analysis Schema

```mermaid
graph TD
    subgraph "Common Query Patterns"
        Q1[Character Lookup by Name<br/>SELECT * FROM characters c<br/>LEFT JOIN character_aliases a<br/>WHERE c.name = ? OR a.alias_name = ?<br/>Index: characters_name_idx, aliases_name_idx]

        Q2[Find Character Associations<br/>SELECT c.*, cta.*<br/>FROM characters c<br/>JOIN character_text_associations cta<br/>WHERE cta.utterance_id = ?<br/>Index: assoc_utterance_idx]

        Q3[Character Profile Query<br/>SELECT profile FROM characters<br/>WHERE id = ?<br/>JSONB operations on profile data<br/>Index: characters_pkey, profile_gin_idx]

        Q4[Batch Association Insert<br/>INSERT INTO character_text_associations<br/>(character_id, utterance_id, relationship, ...)<br/>VALUES (?, ?, ?, ...), ...<br/>Batch size: 100-500 records]

        Q5[Character Statistics<br/>SELECT character_id, COUNT(*), AVG(confidence_score)<br/>FROM character_text_associations<br/>GROUP BY character_id<br/>Index: assoc_char_conf_idx]
    end

    subgraph "Performance Metrics"
        P1[Query Execution Time<br/>- Target: < 50ms for lookups<br/>- Target: < 200ms for complex joins<br/>- Target: < 1s for statistics]

        P2[Index Usage Statistics<br/>- Index hit ratio: > 95%<br/>- Sequential scan ratio: < 5%<br/>- Index cache efficiency: > 90%]

        P3[Connection Pool Metrics<br/>- Active connections: monitored<br/>- Wait time: < 10ms<br/>- Connection lifetime: optimized]

        P4[JSONB Performance<br/>- GIN index usage: monitored<br/>- Query optimization: enabled<br/>- Profile query time: < 100ms]
    end

    subgraph "Optimization Strategies"
        O1[Query Optimization<br/>- Prepared statements<br/>- Query plan analysis<br/>- Index hint usage<br/>- Batch operations]

        O2[Index Strategy<br/>- Composite indexes for common queries<br/>- Partial indexes for filtered data<br/>- GIN indexes for JSONB<br/>- Regular index maintenance]

        O3[Caching Strategy<br/>- Character profile caching<br/>- Query result caching<br/>- Application-level caching<br/>- Cache invalidation strategy]

        O4[Hardware Optimization<br/>- SSD storage utilization<br/>- Memory allocation tuning<br/>- Connection pooling configuration<br/>- CPU core utilization]
    end

    Q1 --> P1
    Q2 --> P1
    Q3 --> P1
    Q4 --> P1
    Q5 --> P1

    P1 --> O1
    P2 --> O2
    P3 --> O1
    P4 --> O3

    O1 --> O4
    O2 --> O4
    O3 --> O4
```

This comprehensive database schema documentation provides detailed table structures, relationships, indexing strategies, and performance considerations for the two-agent dialogue classification and speaker attribution system's PostgreSQL database.
