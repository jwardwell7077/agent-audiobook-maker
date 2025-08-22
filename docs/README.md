# Documentation Index

AI‑generated, Copilot‑assisted. Categorized reference for fast navigation.

## Overview & Policy

- KISS policy: [KISS.md](KISS.md)
- Project context: [CONTEXT.md](CONTEXT.md)
- Development journey: [DEVELOPMENT_JOURNEY.md](DEVELOPMENT_JOURNEY.md)
- Lessons learned: [LESSONS_LEARNED.md](LESSONS_LEARNED.md)

### Tenets (short)

- KISS
- TDD + spec-first
- Local-first artifacts
- Contract-first
- Minimal complexity

## Architecture & Specs

- High‑level architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
  - Diagram source: [diagrams/high_level_architecture.mmd](diagrams/high_level_architecture.mmd)
  - Component spec: PDF→Text [PDF_TO_TEXT_SPEC.md](PDF_TO_TEXT_SPEC.md)
  - CLI spec: [PDF_TO_TEXT_CLI_SPEC.md](PDF_TO_TEXT_CLI_SPEC.md)
  - TXT→JSON spec: [TXT_TO_JSON_SPEC.md](TXT_TO_JSON_SPEC.md)

## Data Contracts / Schemas

- Structured JSON (volume manifest + per‑chapter): [STRUCTURED_JSON_SCHEMA.md](STRUCTURED_JSON_SCHEMA.md)
  - Diagram: [diagrams/structured_json_schema.mmd](diagrams/structured_json_schema.mmd)
- Annotation schema: [ANNOTATION_SCHEMA.md](ANNOTATION_SCHEMA.md)

## Section Classifier

- Design spec: [SECTION_CLASSIFIER_SPEC.md](SECTION_CLASSIFIER_SPEC.md)
  - Flow diagram: [diagrams/section_classifier.mmd](diagrams/section_classifier.mmd)
  - FSM diagram: [diagrams/section_classifier_fsm.mmd](diagrams/section_classifier_fsm.mmd)
  - UML: [diagrams/section_classifier_uml.mmd](diagrams/section_classifier_uml.mmd)
  - Outputs: four JSON files (front_matter.json, toc.json, chapters_section.json, back_matter.json); page-number-only lines removed, mixed lines cleaned with warnings
  - Schemas: [schemas/classifier/front_matter.schema.json](schemas/classifier/front_matter.schema.json), [schemas/classifier/toc.schema.json](schemas/classifier/toc.schema.json), [schemas/classifier/chapters_section.schema.json](schemas/classifier/chapters_section.schema.json), [schemas/classifier/back_matter.schema.json](schemas/classifier/back_matter.schema.json)
  - Examples: [examples/classifier/front_matter.example.json](examples/classifier/front_matter.example.json), [examples/classifier/toc.example.json](examples/classifier/toc.example.json), [examples/classifier/chapters_section.example.json](examples/classifier/chapters_section.example.json), [examples/classifier/back_matter.example.json](examples/classifier/back_matter.example.json)

## Chapterizer

- Design spec: [CHAPTERIZER_SPEC.md](CHAPTERIZER_SPEC.md)
  - FSM diagram: [diagrams/chapterizer_fsm.mmd](diagrams/chapterizer_fsm.mmd)
  - UML: [diagrams/chapterizer_uml.mmd](diagrams/chapterizer_uml.mmd)

## CLI quick links (source)

- PDF→Text CLI: `src/abm/ingestion/pdf_to_text_cli.py`
- Classifier CLI: `src/abm/classifier/classifier_cli.py`
- Chapterizer CLI: `src/abm/structuring/chapterizer_cli.py`

## Roadmap

- Multi‑agent roadmap: [MULTI_AGENT_ROADMAP.md](MULTI_AGENT_ROADMAP.md)
- Learning path (LangFlow/LangChain/LangSmith/LangGraph/CrewAI): [LEARNING_PATH_MULTI_AGENT.md](LEARNING_PATH_MULTI_AGENT.md)

## Templates

- Full Design Spec: [templates/FULL_DESIGN_SPEC_TEMPLATE.md](templates/FULL_DESIGN_SPEC_TEMPLATE.md)
- Test Plan: [templates/TEST_PLAN_TEMPLATE.md](templates/TEST_PLAN_TEMPLATE.md)

## Quality

- Quality Gate Spec: [design/QUALITY_GATE_SPEC.md](design/QUALITY_GATE_SPEC.md)

## Diagrams catalog

- High level: [diagrams/high_level_architecture.mmd](diagrams/high_level_architecture.mmd)
- PDF→Text: [diagrams/pdf_to_text_flow.mmd](diagrams/pdf_to_text_flow.mmd), [diagrams/pdf_to_text_uml.mmd](diagrams/pdf_to_text_uml.mmd)
- Section Classifier: [diagrams/section_classifier.mmd](diagrams/section_classifier.mmd), [diagrams/section_classifier_fsm.mmd](diagrams/section_classifier_fsm.mmd), [diagrams/section_classifier_uml.mmd](diagrams/section_classifier_uml.mmd)
- Chapterizer: [diagrams/chapterizer_fsm.mmd](diagrams/chapterizer_fsm.mmd), [diagrams/chapterizer_uml.mmd](diagrams/chapterizer_uml.mmd)
- Quality Gate: [diagrams/quality_gate_architecture.mmd](diagrams/quality_gate_architecture.mmd), [diagrams/quality_gate_fsm.mmd](diagrams/quality_gate_fsm.mmd), [diagrams/quality_gate_uml.mmd](diagrams/quality_gate_uml.mmd)
- Structured JSON: [diagrams/structured_json_schema.mmd](diagrams/structured_json_schema.mmd)

## Examples

- Classifier artifacts: [examples/classifier/](examples/classifier/)

## How to read this repo

- Start with [KISS.md](KISS.md) and the root README’s Quickstart.
- Skim [ARCHITECTURE.md](ARCHITECTURE.md), then the Structured JSON/Annotation schemas.
- Dive into the Section Classifier spec if you’re extending ingestion.
- Reference Context/Journey/Lessons for rationale and decisions.
