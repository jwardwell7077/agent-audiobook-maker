# Two-Agent System Architecture Diagrams

Note: This page retains legacy naming for historical continuity. The current
annotation architecture is described as a spans-first two-stage system
(dialogue classification → deterministic speaker attribution). The diagrams
below remain valid conceptually and will be renamed in a future pass.

## System Architecture Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Input Processing"
        A[Chapter Text] --> B[ABM Segment Dialogue/Narration]
        B --> C[Enhanced Segments with Metadata]
    end
    
    subgraph "Two-Agent Processing Pipeline"
        C --> D[Agent 1: Hybrid Dialogue Classifier]
        D --> E{Classification Type}
        E -->|Dialogue/Mixed| F[Agent 2: Speaker Attribution]
        E -->|Narration| G[Character Context Collector]
        F --> H[Character Database Lookup]
        G --> H
        H --> I[Character Profile Updates]
    end
    
    subgraph "Database Layer"
        J[(Characters Table)]
        K[(Character Text Segments)]
        L[(Enhanced Utterances)]
        I --> J
        I --> K
        I --> L
    end
    
    subgraph "Output Products"
        J --> M[Character Profiles]
        K --> N[Voice Casting Data]
        L --> O[Enhanced Annotations]
    end
```

### Component Architecture Diagram

```mermaid
graph LR
    subgraph "LangFlow Pipeline"
        A[Chapter Loader] --> B[Chapter Selector]
        B --> C[Segment Dialogue/Narration]
        C --> D[Context Window Builder]
        
        subgraph "Agent Processing Layer"
            D --> E[Hybrid Dialogue Classifier]
            E --> F[Speaker Attribution Agent]
            F --> G[Character Data Collector]
        end
        
        subgraph "Database Integration"
            H[Character Database Manager]
            I[Profile Builder]
            J[Data Validator]
        end
        
        G --> H
        H --> I
        I --> J
    end
    
    subgraph "External Systems"
        K[PostgreSQL Database]
        L[LLM Services]
        M[Character Profile API]
    end
    
    H -.-> K
    E -.-> L
    F -.-> L
    J -.-> M
```

### Data Flow Architecture

```mermaid
sequenceDiagram
    participant CT as Chapter Text
    participant SEG as Segmenter
    participant CWB as Context Window Builder
    participant AG1 as Agent 1 (Classifier)
    participant AG2 as Agent 2 (Attribution)
    participant DB as Character Database
    participant PR as Profile Builder
    
    CT->>SEG: Raw chapter text
    SEG->>CWB: Text segments with metadata
    CWB->>AG1: Context windows (5 segments)
    
    AG1->>AG1: Apply heuristic rules
    alt Clear Classification
        AG1->>AG2: Direct classification result
    else Ambiguous Case
        AG1->>AG1: Apply AI classification
        AG1->>AG2: AI classification result
    end
    
    AG2->>DB: Character lookup query
    DB->>AG2: Character matches + aliases
    AG2->>AG2: Speaker vs addressee logic
    AG2->>DB: Create/update character records
    AG2->>PR: Character-text associations
    PR->>DB: Update character profiles
    DB->>PR: Complete character data
```

### Processing State Machine Architecture

```mermaid
stateDiagram-v2
    [*] --> SegmentReady
    
    SegmentReady --> ClassifyingDialogue: Process segment with context
    
    state ClassifyingDialogue {
        [*] --> ApplyHeuristics
        ApplyHeuristics --> HeuristicMatch: Clear patterns found
        ApplyHeuristics --> RequiresAI: Ambiguous patterns
        
        HeuristicMatch --> [*]: Fast classification
        RequiresAI --> AIProcessing
        AIProcessing --> [*]: Context-aware classification
    }
    
    ClassifyingDialogue --> DialogueDetected: Dialogue/Mixed
    ClassifyingDialogue --> NarrationDetected: Narration
    
    DialogueDetected --> AttributingSpeaker: Character identification needed
    NarrationDetected --> CollectingContext: Character context analysis
    
    state AttributingSpeaker {
        [*] --> DatabaseLookup
        DatabaseLookup --> CharacterFound: Match found
        DatabaseLookup --> CreateCharacter: New character
        
        CharacterFound --> RoleAnalysis
        CreateCharacter --> RoleAnalysis
        RoleAnalysis --> [*]: Speaker/Addressee determined
    }
    
    state CollectingContext {
        [*] --> AnalyzeNarration
        AnalyzeNarration --> CharacterMentions: Characters referenced
        AnalyzeNarration --> SceneContext: Scene description
        CharacterMentions --> [*]
        SceneContext --> [*]
    }
    
    AttributingSpeaker --> UpdatingProfiles: Character associations made
    CollectingContext --> UpdatingProfiles: Context data collected
    UpdatingProfiles --> Complete: Database updated
    Complete --> [*]
```

### Hybrid Classification Decision Tree

```mermaid
flowchart TD
    A[Text Segment Input] --> B{Contains Quote Marks?}
    B -->|Yes| C{Has Dialogue Tags?}
    B -->|No| D{Has Speech Indicators?}
    
    C -->|"said", "asked", etc.| E[DIALOGUE - Heuristic]
    C -->|No clear tags| F{Context Analysis Needed?}
    
    D -->|"shouted", "whispered"| E
    D -->|No indicators| G{Descriptive Language?}
    
    F -->|Yes| H[Send to AI Agent]
    F -->|No| I[MIXED - Heuristic]
    
    G -->|Action, setting, etc.| J[NARRATION - Heuristic]
    G -->|Unclear| H
    
    H --> K{AI Classification}
    K --> L[DIALOGUE - AI]
    K --> M[NARRATION - AI]
    K --> N[MIXED - AI]
    
    E --> O[High Confidence]
    I --> P[Medium Confidence]
    J --> O
    L --> Q[AI Confidence Score]
    M --> Q
    N --> Q
    
    O --> R[Proceed to Speaker Attribution]
    P --> R
    Q --> R
```

### Database Integration Architecture

```mermaid
erDiagram
    BOOKS ||--o{ CHAPTERS : contains
    CHAPTERS ||--o{ UTTERANCES : contains
    BOOKS ||--o{ CHARACTERS : features
    CHARACTERS ||--o{ CHARACTER_TEXT_SEGMENTS : associated_with
    UTTERANCES ||--o{ CHARACTER_TEXT_SEGMENTS : references
    
    BOOKS {
        int id PK
        string title
        string author
        jsonb metadata
        timestamp created_at
    }
    
    CHAPTERS {
        int id PK
        int book_id FK
        int chapter_index
        string title
        text body_text
        jsonb metadata
    }
    
    UTTERANCES {
        int id PK
        int book_id FK
        int chapter_id FK
        text content
        int position_in_chapter
        string dialogue_classification
        float dialogue_confidence
        int speaker_character_id FK
        float speaker_confidence
        timestamp processed_by_agents
    }
    
    CHARACTERS {
        int id PK
        int book_id FK
        string name
        string canonical_name
        jsonb aliases
        int first_appearance_segment_id FK
        string character_type
        jsonb profile
        timestamp created_at
        timestamp updated_at
    }
    
    CHARACTER_TEXT_SEGMENTS {
        int id PK
        int character_id FK
        int utterance_id FK
        string segment_type
        string relationship
        text context_before
        text context_after
        float confidence_score
        jsonb context_data
        timestamp created_at
    }
```

### Context Window Processing Architecture

```mermaid
graph TD
    subgraph "Context Window Construction"
        A[Utterance Queue] --> B[Window Builder]
        B --> C[5-Segment Window]
        
        C --> D[Context Before: 2 segments]
        C --> E[Target Segment: 1]
        C --> F[Context After: 2 segments]
    end
    
    subgraph "Window Processing"
        D --> G[Previous Classifications]
        E --> H[Target Analysis]
        F --> I[Following Context Hints]
        
        G --> J[Pattern Recognition]
        H --> J
        I --> J
    end
    
    subgraph "Classification Decision"
        J --> K{Confidence Level}
        K -->|High| L[Heuristic Result]
        K -->|Low| M[AI Processing]
        
        M --> N[Context-Aware LLM]
        N --> O[AI Classification Result]
    end
    
    L --> P[Classification Output]
    O --> P
    
    P --> Q[Next Window]
    Q --> B
```

### Character Database Lookup Architecture

```mermaid
graph LR
    subgraph "Speaker Identification Process"
        A[Dialogue Segment] --> B[Extract Names]
        B --> C[Name Normalization]
        
        C --> D[Database Query]
        
        subgraph "Query Strategy"
            D --> E[Exact Name Match]
            D --> F[Canonical Name Match]
            D --> G[Alias Search JSONB]
        end
        
        E --> H{Match Found?}
        F --> H
        G --> H
    end
    
    subgraph "Character Resolution"
        H -->|Yes| I[Character Record]
        H -->|No| J[Create New Character]
        
        I --> K[Role Analysis]
        J --> L[Initialize Profile]
        L --> K
        
        K --> M{Speaker or Addressee?}
        M -->|Speaker| N[Attribute Dialogue]
        M -->|Addressee| O[Mark as Mentioned]
        M -->|Unclear| P[Store Both Options]
    end
    
    subgraph "Profile Updates"
        N --> Q[Update Character Profile]
        O --> R[Update Mention Count]
        P --> S[Flag for Review]
        
        Q --> T[Character Database]
        R --> T
        S --> T
    end
```

### Agent Processing Pipeline Architecture

```mermaid
graph TB
    subgraph "Agent 1: Hybrid Dialogue Classifier"
        A1[Context Window Input] --> B1{Heuristic Analysis}
        B1 -->|Clear Pattern| C1[Fast Classification]
        B1 -->|Ambiguous| D1[AI Classification Queue]
        
        D1 --> E1[Batch AI Processing]
        E1 --> F1[Context-Aware Results]
        
        C1 --> G1[Classification Output]
        F1 --> G1
    end
    
    subgraph "Agent 2: Speaker Attribution"
        G1 --> A2{Dialogue Detected?}
        A2 -->|Yes| B2[Character Database Lookup]
        A2 -->|No| C2[Context Collection]
        
        B2 --> D2[Speaker Pattern Analysis]
        D2 --> E2[Role Assignment Logic]
        E2 --> F2[Character Association]
        
        C2 --> G2[Character Reference Detection]
        G2 --> H2[Scene Context Analysis]
    end
    
    subgraph "Database Integration Layer"
        F2 --> I[Character Record Updates]
        H2 --> J[Context Data Storage]
        
        I --> K[Character Profiles Table]
        J --> L[Character Text Segments Table]
        
        K --> M[Profile Builder]
        L --> M
        M --> N[Enhanced Character Data]
    end
```

## Integration Points

### LangFlow Component Integration

```mermaid
graph LR
    subgraph "ABM Core Components"
        A[ABMChapterLoader]
        B[ABMBlockIterator]
        C[ABMDialogueClassifier]
        D[ABMSpeakerAttribution]
        E[ABMResultsAggregator]
        F[ABM Results → Utterances]
        G[ABMAggregatedJsonlWriter]
    end

    A --> B --> C --> D --> E --> F --> G
```

### Hardware Optimization Architecture

```mermaid
graph TB
    subgraph "Processing Optimization"
        A[Context Window Batch: 500 segments]
        B[Memory Pool: 8GB]
        C[GPU Queue: RTX 4070]
        D[NVMe Cache: Samsung 990 Pro]
    end
    
    subgraph "Parallel Processing"
        E[Dialogue Classifier Workers: 8]
        F[Speaker Attribution Workers: 6]
        G[Database Workers: 4]
    end
    
    subgraph "Resource Management"
        H[Memory Monitor]
        I[GPU Utilization Tracker]
        J[I/O Performance Monitor]
    end
    
    A --> E
    E --> C
    F --> G
    G --> D
    H --> B
    I --> C
    J --> D
```
