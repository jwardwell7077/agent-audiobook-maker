# High-Level Architecture

KISS today: local CLI + deterministic ingestion and simple annotation to files. Later: multi-agent enrichment, orchestration, TTS, and optional DB.

Source: [docs/diagrams/high_level_architecture.mmd](../04-diagrams/architecture/high_level_architecture.mmd)

```mermaid
flowchart LR
  subgraph Dev["Local-first (KISS today)"]
    CLI["CLI (ingest, annotate)"]
    PDF[("PDF")]
    TXT[("Simple TXT")]
    JSONRaw[("JSON (per-chapter raw)")]
    JSONStruct[("Structured JSON (manifest + chapters)")]
    Annot["Annotation v1 (segmentation: dialogue/narration)"]
    Artifacts[("data/clean/book/chapter.json")]
    Annos[("data/annotations/book/chapter.jsonl")]
  end

  CLI --> PDF --> TXT --> JSONRaw --> JSONStruct --> Artifacts
  Artifacts --> Annot --> Annos

  subgraph Later["Later (roadmap)"]
    Casting["Casting (character bible)"]
    SSML["SSML Assembly"]
    TTS["TTS (XTTS/Piper)"]
    Stems[("data/stems/")]
    Renders[("data/renders/book/chapter.wav")]
    Master[("book_master.wav")]
    Orchestrator["Dagster / LangGraph"]
    DB[("Postgres (JSONB)")]
  end

  Annos -.-> Casting -.-> SSML -.-> TTS --> Stems --> Renders --> Master
  Orchestrator -.controls.-> JSONStruct
  Orchestrator -.controls.-> Annot
  Orchestrator -.controls.-> TTS

  Artifacts -.sync.-> DB
  Annos -.sync.-> DB
  Renders -.sync.-> DB
```

## Legend

- **Solid nodes/edges**: implemented in the KISS slice (today)
- **Dashed edges/nodes**: future roadmap components

## Key Components

### Current Implementation (KISS)

- **CLI Interface**: Simple command-line tools for ingestion and annotation
- **PDF Processing**: Direct conversion to clean text files
- **JSON Structure**: Per-chapter JSON files with volume manifests
- **Basic Annotation**: Dialogue/narration segmentation

### Future Roadmap

- **Multi-Agent Orchestra**: Dagster/LangGraph coordination
- **Character Casting**: Speaker identification and voice assignment
- **TTS Integration**: Text-to-speech with XTTS/Piper
- **Database Layer**: PostgreSQL with JSONB for structured data
- **Audio Pipeline**: Stem generation and final rendering

## Design Principles

1. **KISS Today**: Start simple, build incrementally
2. **Local-First**: No cloud dependencies for core functionality
3. **File-Based**: Explicit artifact storage for reproducibility
4. **Deterministic**: Consistent outputs for same inputs
5. **Extensible**: Architecture supports future enhancements
