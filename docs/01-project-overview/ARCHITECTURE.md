# High-Level Architecture

KISS today: local CLI + deterministic ingestion transitioning to a sophisticated two-agent annotation system. The new architecture features hybrid dialogue classification and speaker attribution with PostgreSQL character database integration. Later: multi-agent enrichment, orchestration, TTS, and optional DB.

Source: [docs/diagrams/high_level_architecture.mmd](diagrams/high_level_architecture.mmd)

**Two-Agent System Integration**: The annotation pipeline now incorporates a two-agent system for advanced dialogue processing and character tracking. See [Two-Agent System Specification](../02-specifications/components/two-agent-dialogue-speaker-system.md) for complete details.

```mermaid
flowchart LR
  subgraph Dev["Local-first (KISS today + Two-Agent System)"]
    CLI["CLI (ingest, annotate)"]
    PDF(("PDF"))
    TXT(("Simple TXT"))

    %% Upstream structuring stages (new)
    SectionClassifier["Section Classifier"]
    Classified(("classified/front_matter.json | toc.json |\nchapters_section.json | back_matter.json"))
  %% Chapterizer removed; chapter structure derived from classifier outputs
  TxtStructured["TXT→Structured (paragraphs[])"]

    JSONStruct(("Structured JSON (manifest + chapters)"))
    
    subgraph TwoAgent["Two-Agent Annotation System"]
      DialogueAgent["Dialogue Classifier<br/>(Hybrid: Heuristic + AI)"]
      SpeakerAgent["Speaker Attribution<br/>(Character Database)"]
      CharDB(("Character DB<br/>(PostgreSQL)"))
    end
    
    Artifacts(("data/clean/<book>/<chapter>.json\n<pdf_stem>_volume.json"))
    Annos(("data/annotations/<book>/<chapter>.jsonl"))
  end

  %% Ingest and structuring pipeline
  CLI --> PDF --> TXT --> SectionClassifier --> Classified --> TxtStructured --> JSONStruct --> Artifacts

  %% Two-agent consumption
  Artifacts --> DialogueAgent
  DialogueAgent --> SpeakerAgent
  SpeakerAgent <--> CharDB
  SpeakerAgent --> Annos

  subgraph Later["Later (roadmap)"]
    Casting["Casting (character bible)"]
    SSML["SSML Assembly"]
    TTS["TTS (XTTS/Piper)"]
    Stems(("data/stems/…"))
    Renders(("data/renders/<book>/<chapter>.wav"))
    Master(("book_master.wav"))
    Orchestrator["Dagster / LangGraph"]
    DB(("Postgres (JSONB)"))
  end

  CharDB -.integrates.-> DB
  Annos -.-> Casting -.-> SSML -.-> TTS --> Stems --> Renders --> Master
  Orchestrator -.controls.-> JSONStruct
  Orchestrator -.controls.-> TwoAgent
  Orchestrator -.controls.-> TTS

  Artifacts -.sync.-> DB
  Annos -.sync.-> DB
  Renders -.sync.-> DB
```

Legend

- Solid nodes/edges: implemented in the KISS slice (today)
- Dashed edges/nodes: future roadmap components

Notes

- Upstream source of truth for the two-agent system is the chapters_section.json produced by Section Classifier; TXT→Structured consumes chapter spans directly; paragraphs and blank lines are preserved for downstream fidelity.
