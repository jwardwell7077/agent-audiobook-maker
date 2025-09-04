# [DEPRECATED] Supplementary Two-Agent System Diagrams

> Deprecated terminology. Retained as historical notes; not representative of the current spans-first two-stage implementation.

## Early Design Evolution Diagrams

This document captures specific diagrams and data models discussed during the design evolution of the two-agent system, including alternative approaches considered before the final PostgreSQL-based design.

## Proposed Character Data Model (File-Based Approach)

### Master Character Registry Structure

```mermaid
graph TB
    subgraph "File-Based Character Data Structure"
        A[data/characters/{book_id}/]
        A --> B[character_profiles.json]
        A --> C[dialogue_collection.jsonl]  
        A --> D[narration_context.jsonl]
        A --> E[casting_metadata.json]
    end

    subgraph "character_profiles.json Structure"
        B --> F[Character ID Mappings<br/>- canonical_name: string<br/>- display_name: string<br/>- aliases: array<br/>- character_type: string<br/>- first_appearance: string]
    end

    subgraph "dialogue_collection.jsonl Structure"
        C --> G[Per-Line Records<br/>- character_id: string<br/>- utterance_id: string<br/>- text: string<br/>- context_before: string<br/>- context_after: string<br/>- confidence: float]
    end

    subgraph "narration_context.jsonl Structure"
        D --> H[Context Records<br/>- character_id: string<br/>- segment_id: string<br/>- text: string<br/>- relationship: string<br/>- mention_type: string]
    end

    subgraph "casting_metadata.json Structure"
        E --> I[Voice Casting Data<br/>- character_id: string<br/>- estimated_age: string<br/>- gender_markers: array<br/>- speech_patterns: object<br/>- vocal_characteristics: array]
    end
```

### File-Based Data Flow

```mermaid
flowchart LR
    A[Text Segments] --> B[Agent 1: Classification]
    B --> C[Agent 2: Speaker Attribution]
    C --> D{Character Exists?}
    D -->|Yes| E[Load character_profiles.json]
    D -->|No| F[Create New Character Entry]
    E --> G[Append to dialogue_collection.jsonl]
    F --> G
    G --> H[Update narration_context.jsonl]
    H --> I[Generate casting_metadata.json]
    I --> J[Character Database Ready]
```

## Enhanced Agent 2: Speaker Attribution with DB Lookup

### Enhanced Character Database Schema (Early Design)

```mermaid
erDiagram
    Character_Registry ||--o{ Character_Dialogues : contains
    Character_Registry ||--o{ Character_Context : references
    Character_Registry ||--o{ Character_Aliases : has
    Character_Registry ||--o{ Casting_Metadata : generates

    Character_Registry {
        string character_id PK
        string canonical_name
        string display_name
        string character_type
        int first_appearance_segment
        json aliases
        json profile_data
        timestamp created_at
        timestamp updated_at
    }

    Character_Dialogues {
        string id PK
        string character_id FK
        string utterance_id
        text dialogue_text
        string context_before
        string context_after
        float confidence_score
        string detection_method
        timestamp recorded_at
    }

    Character_Context {
        string id PK
        string character_id FK
        string segment_id
        text context_text
        string relationship_type
        string mention_type
        float relevance_score
        timestamp recorded_at
    }

    Character_Aliases {
        string id PK
        string character_id FK
        string alias_name
        string alias_type
        float usage_confidence
        int first_used_segment
        timestamp created_at
    }

    Casting_Metadata {
        string character_id PK
        string estimated_age
        string gender_presentation
        json speech_patterns
        json vocal_characteristics
        json personality_hints
        float profile_completeness
        timestamp last_updated
    }
```

### Speaker vs Addressee Detection Logic

```mermaid
flowchart TD
    A[Dialogue Segment Input] --> B[Extract Character Names]
    B --> C[Analyze Dialogue Tags]
    C --> D[Check Quote Attribution]
    D --> E{Has Clear Attribution?}

    E -->|Yes| F[Direct Speaker Assignment]
    E -->|No| G[Contextual Analysis]

    G --> H[Check Previous Context]
    H --> I[Look for Address Patterns]
    I --> J[Check Name Proximity]
    J --> K{Multiple Candidates?}

    K -->|No| L[Single Speaker Assignment]
    K -->|Yes| M[Apply Disambiguation Rules]

    M --> N[Check Conversation Flow]
    N --> O[Analyze Speaking Patterns]
    O --> P[Apply Confidence Scoring]

    P --> Q{Confidence > Threshold?}
    Q -->|Yes| R[Speaker Assignment]
    Q -->|No| S[Flag for Manual Review]

    F --> T[Identify Addressee Candidates]
    L --> T
    R --> T

    T --> U[Check Direct Address Patterns]
    U --> V[Analyze Character Mentions]
    V --> W[Apply Context Rules]
    W --> X[Addressee Assignment]

    S --> Y[Uncertain Attribution Record]
    X --> Z[Complete Attribution Record]
    Y --> Z

    Z --> AA[Update Character Database]
```

### Character Lookup Flow

```mermaid
flowchart TB
    A[Character Name Extracted] --> B[Normalize Name]
    B --> C[Primary Name Lookup]
    C --> D{Found in Character Registry?}

    D -->|Yes| E[Return Character Record]
    D -->|No| F[Alias Lookup]

    F --> G[Search Character Aliases]
    G --> H{Alias Match Found?}

    H -->|Yes| I[Return Parent Character]
    H -->|No| J[Fuzzy Name Matching]

    J --> K[Calculate Name Similarity]
    K --> L{Similarity > Threshold?}

    L -->|Yes| M[Return Best Match with Confidence]
    L -->|No| N[Create New Character Record]

    N --> O[Generate Character ID]
    O --> P[Initialize Character Profile]
    P --> Q[Add to Character Registry]
    Q --> R[Return New Character Record]

    E --> S[Update Character Statistics]
    I --> S
    M --> S
    R --> S

    S --> T[Character Lookup Complete]
```

## Data Loading Strategy for 5-Segment Context Windows

### Context Window Data Loading

```mermaid
flowchart LR
    subgraph "Memory-Efficient Loading Strategy"
        A[Text Segment Queue] --> B[Context Window Builder]
        B --> C[5-Segment Buffer]
        C --> D[Target Segment Analysis]

        subgraph "Buffer Management"
            E[Previous 2 Segments]
            F[Current Target]
            G[Following 2 Segments]
            C --> E
            C --> F
            C --> G
        end

        D --> H[Agent Processing]
        H --> I[Slide Window Forward]
        I --> B
    end

    subgraph "Database Query Strategy"
        J[Segment ID Input] --> K[Query Adjacent Segments]
        K --> L[ORDER BY position_in_chapter]
        L --> M[LIMIT 5 OFFSET calculated]
        M --> N[Return Context Window]
    end

    subgraph "Memory Optimization"
        O[Context Cache] --> P[LRU Eviction]
        P --> Q[Memory Threshold Check]
        Q --> R[Release Processed Windows]
        R --> S[Maintain 10 Windows Max]
    end
```

### Database Query Strategy

```mermaid
sequenceDiagram
    participant App as Application
    participant Cache as Context Cache
    participant DB as Database
    participant Proc as Processor

    App->>Cache: Request context window for segment_123
    Cache->>Cache: Check if window cached

    alt Cache Hit
        Cache->>App: Return cached window
    else Cache Miss
        Cache->>DB: Query adjacent segments
        DB->>DB: SELECT * FROM utterances WHERE chapter_id = ? ORDER BY position LIMIT 5 OFFSET ?
        DB->>Cache: Return 5 segments
        Cache->>Cache: Build context window
        Cache->>App: Return new window
    end

    App->>Proc: Process context window
    Proc->>Proc: Classification/Attribution
    Proc->>App: Return results

    App->>Cache: Mark window as processed
    Cache->>Cache: Update LRU position

    loop Memory Management
        Cache->>Cache: Check memory usage
        Cache->>Cache: Evict oldest windows if needed
    end
```

### Memory-Efficient Data Structure

```mermaid
classDiagram
    class ContextWindow {
        +string target_segment_id
        +List~Segment~ context_segments
        +int estimated_memory_kb
        +DateTime last_accessed
        +bool is_processed
        +get_memory_footprint() int
        +slide_forward() ContextWindow
        +to_processing_format() Dict
    }

    class SegmentBuffer {
        +int max_size = 5
        +Queue~Segment~ segments
        +int total_memory_kb
        +add_segment(segment: Segment) void
        +get_context_around(position: int) List~Segment~
        +evict_oldest() void
        +calculate_memory_usage() int
    }

    class ContextCache {
        +Dict~string, ContextWindow~ cache
        +int max_memory_mb = 100
        +int current_memory_kb
        +LRUPolicy eviction_policy
        +get(segment_id: string) ContextWindow
        +put(window: ContextWindow) void
        +evict_lru() void
        +memory_pressure_check() bool
    }

    class OptimizedProcessor {
        +ContextCache cache
        +SegmentBuffer buffer
        +int batch_size = 32
        +process_batch(segments: List~string~) List~Result~
        +optimize_memory_usage() void
        +get_processing_stats() ProcessingStats
    }

    ContextWindow --> SegmentBuffer : uses
    OptimizedProcessor --> ContextCache : manages
    OptimizedProcessor --> SegmentBuffer : maintains
    ContextCache --> ContextWindow : stores
```

### Storage Optimization for Samsung 990 Pro

```mermaid
flowchart TB
    subgraph "NVMe Optimization Strategy"
        A[Samsung 990 Pro NVMe] --> B[Sequential Write Optimization]
        B --> C[4KB Block Alignment]
        C --> D[Write Coalescing Buffer]
        D --> E[Batch Database Commits]
    end

    subgraph "Database Storage Layout"
        F[PostgreSQL Data Directory] --> G[Character Tables: Fast Access]
        F --> H[Association Tables: Sequential Layout]
        F --> I[JSONB Data: Compressed Storage]
        F --> J[Index Files: Memory Mapped]
    end

    subgraph "Caching Strategy"
        K[Database Cache: 8GB] --> L[Character Profiles: Hot Data]
        K --> M[Recent Associations: Warm Data]
        K --> N[Statistics: Cold Data]
    end

    subgraph "Write Optimization"
        O[Batch Size: 100 records] --> P[Transaction Grouping]
        P --> Q[WAL Optimization]
        Q --> R[fsync Tuning]
        R --> S[Checkpoint Intervals]
    end

    A --> F
    K --> A
    O --> A
```

## Enhanced Segmentation Output Structure

### Segmentation Enhancement Metadata

```mermaid
graph TB
    subgraph "Enhanced Segment Structure"
        A[Base Segment] --> B[Metadata Enhancement]
        B --> C[Processing Hints]
        B --> D[Classification Preparation]
        B --> E[Context Markers]
        B --> F[Performance Metrics]
    end

    subgraph "Metadata Fields"
        G[segment_id: unique identifier]
        H[text: cleaned content]
        I[word_count: processing size]
        J[has_quotes: dialogue indicator]
        K[paragraph_type: structural hint]
        L[complexity_score: processing difficulty]
        M[context_importance: relevance weight]
        N[processing_priority: queue order]
    end

    B --> G
    B --> H
    B --> I
    B --> J
    B --> K
    B --> L
    B --> M
    B --> N

    subgraph "Enhanced Output Format"
        O[JSON Structure]
        P["segments": array of enhanced segments]
        Q["metadata": processing statistics]
        R["quality_indicators": validation results]
        S["optimization_hints": performance guidance]
    end

    A --> O
    O --> P
    O --> Q
    O --> R
    O --> S
```

### Processing Pipeline Enhancement

```mermaid
sequenceDiagram
    participant Input as Raw Text
    participant Seg as Enhanced Segmenter
    participant Meta as Metadata Enricher
    participant Valid as Validator
    participant Out as Enhanced Output

    Input->>Seg: Chapter text with structure
    Seg->>Seg: Split by blank lines
    Seg->>Seg: Generate segment IDs
    Seg->>Meta: Basic segments

    Meta->>Meta: Calculate word counts
    Meta->>Meta: Detect quote patterns
    Meta->>Meta: Analyze paragraph structure
    Meta->>Meta: Estimate complexity
    Meta->>Meta: Add processing hints
    Meta->>Valid: Enhanced segments

    Valid->>Valid: Validate text quality
    Valid->>Valid: Check segment boundaries
    Valid->>Valid: Verify metadata consistency
    Valid->>Out: Validated segments

    Out->>Out: Format for agent processing
    Out->>Out: Add performance metadata
    Out->>Out: Generate processing statistics
```

These diagrams capture the key design elements and data models discussed during our conversation evolution, showing both the file-based approach initially considered and the detailed processing flows that informed the final PostgreSQL-based design.
