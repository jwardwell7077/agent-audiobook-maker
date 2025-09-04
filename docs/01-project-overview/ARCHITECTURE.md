# High-Level Architecture

KISS today: local CLI + deterministic ingestion transitioning to a spans-first two-stage annotation system. The architecture features hybrid dialogue classification and deterministic speaker attribution. A character database may be added later as an optional enhancement. Later: multi-agent enrichment, orchestration, TTS, and optional DB.

Source: See diagrams index: [04-diagrams/README.md](../04-diagrams/README.md)

Annotation integration: The annotation pipeline incorporates a two-stage flow (dialogue classification → speaker attribution).

```mermaid
flowchart LR
  subgraph Dev["Local-first (KISS today + spans-first two-stage)"]
    CLI["CLI (ingest, annotate)"]
    PDF(("PDF"))
    TXT(("Simple TXT"))

    %% Upstream structuring stages (new)
    SectionClassifier["Section Classifier"]
    Classified(("classified/front_matter.json | toc.json |\nchapters_section.json | back_matter.json"))
  ChapterStructure["Chapter Structure (derived from classifier)"]
  TxtStructured["TXT→Structured (paragraphs[])"]

    JSONStruct(("Structured JSON (manifest + chapters)"))

  subgraph Anno["Spans-first two-stage Annotation"]
      DialogueAgent["Dialogue Classifier<br/>(Hybrid: Heuristic + AI)"]
  SpeakerAgent["Speaker Attribution"]
  CharDB(("Character DB (optional)"))
    end

    Artifacts(("data/clean/<book>/<chapter>.json\n<pdf_stem>_volume.json"))
    Annos(("data/annotations/<book>/<chapter>.jsonl"))
  end

  %% Ingest and structuring pipeline
  CLI --> PDF --> TXT --> SectionClassifier --> Classified --> ChapterStructure --> TxtStructured --> JSONStruct --> Artifacts

  %% Two-stage consumption
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
  Orchestrator -.controls.-> Anno
  Orchestrator -.controls.-> TTS

  Artifacts -.sync.-> DB
  Annos -.sync.-> DB
  Renders -.sync.-> DB
```

Legend

- Solid nodes/edges: implemented in the KISS slice (today)
- Dashed edges/nodes: future roadmap components

Notes

- Upstream source of truth for the annotation system is the chapters_section.json produced by Section Classifier; chapter structure is derived directly from this span (legacy Chapterizer removed); TXT→Structured preserves paragraphs and blank lines for downstream fidelity.
