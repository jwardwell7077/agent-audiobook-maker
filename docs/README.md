# Documentation Index

AI‑generated, Copilot‑assisted. Categorized reference for fast navigation.

## Overview & Policy

- KISS policy: [01-project-overview/KISS.md](01-project-overview/KISS.md)
- Project context: [01-project-overview/CONTEXT.md](01-project-overview/CONTEXT.md)
- Development journey: [05-development/journey/DEVELOPMENT_JOURNEY.md](05-development/journey/DEVELOPMENT_JOURNEY.md)
- Lessons learned: [05-development/journey/LESSONS_LEARNED.md](05-development/journey/LESSONS_LEARNED.md)

### Tenets (short)

- KISS
- TDD + spec-first
- Local-first artifacts
- Contract-first
- Minimal complexity

## Architecture & Specs

- High‑level architecture: [01-project-overview/ARCHITECTURE.md](01-project-overview/ARCHITECTURE.md)
  - Diagram source: [04-diagrams/architecture/high_level_architecture.mmd](04-diagrams/architecture/high_level_architecture.mmd)
  - Component spec: PDF→Text [02-specifications/components/PDF_TO_TEXT_SPEC.md](02-specifications/components/PDF_TO_TEXT_SPEC.md)
  - CLI spec: [02-specifications/components/PDF_TO_TEXT_CLI_SPEC.md](02-specifications/components/PDF_TO_TEXT_CLI_SPEC.md)
  - TXT→JSON spec: [02-specifications/components/TXT_TO_JSON_SPEC.md](02-specifications/components/TXT_TO_JSON_SPEC.md)

## Data Contracts / Schemas

- Structured JSON (volume manifest + per‑chapter): [02-specifications/data-schemas/STRUCTURED_JSON_SCHEMA.md](02-specifications/data-schemas/STRUCTURED_JSON_SCHEMA.md)
  - Diagram: [04-diagrams/flows/structured_json_schema.mmd](04-diagrams/flows/structured_json_schema.mmd)
- Annotation schema: [02-specifications/data-schemas/ANNOTATION_SCHEMA.md](02-specifications/data-schemas/ANNOTATION_SCHEMA.md)

## Section Classifier

- Design spec: [02-specifications/components/SECTION_CLASSIFIER_SPEC.md](02-specifications/components/SECTION_CLASSIFIER_SPEC.md)
  - Flow diagram: [04-diagrams/flows/section_classifier.mmd](04-diagrams/flows/section_classifier.mmd)
  - FSM diagram: [04-diagrams/state-machines/section_classifier_fsm.mmd](04-diagrams/state-machines/section_classifier_fsm.mmd)
  - UML: [04-diagrams/uml/section_classifier_uml.mmd](04-diagrams/uml/section_classifier_uml.mmd)
  - Outputs: four JSON files (front_matter.json, toc.json, chapters_section.json, back_matter.json); page-number-only lines removed, mixed lines cleaned with warnings
  - Schemas: [02-specifications/data-schemas/schemas/classifier/front_matter.schema.json](02-specifications/data-schemas/schemas/classifier/front_matter.schema.json), [02-specifications/data-schemas/schemas/classifier/toc.schema.json](02-specifications/data-schemas/schemas/classifier/toc.schema.json), [02-specifications/data-schemas/schemas/classifier/chapters_section.schema.json](02-specifications/data-schemas/schemas/classifier/chapters_section.schema.json), [02-specifications/data-schemas/schemas/classifier/back_matter.schema.json](02-specifications/data-schemas/schemas/classifier/back_matter.schema.json)
  - Examples: [03-implementation/examples/classifier/front_matter.example.json](03-implementation/examples/classifier/front_matter.example.json), [03-implementation/examples/classifier/toc.example.json](03-implementation/examples/classifier/toc.example.json), [03-implementation/examples/classifier/chapters_section.example.json](03-implementation/examples/classifier/chapters_section.example.json), [03-implementation/examples/classifier/back_matter.example.json](03-implementation/examples/classifier/back_matter.example.json)

## Chapterizer

- Design spec: [02-specifications/components/CHAPTERIZER_SPEC.md](02-specifications/components/CHAPTERIZER_SPEC.md)
  - FSM diagram: [04-diagrams/state-machines/chapterizer_fsm.mmd](04-diagrams/state-machines/chapterizer_fsm.mmd)
  - UML: [04-diagrams/uml/chapterizer_uml.mmd](04-diagrams/uml/chapterizer_uml.mmd)

## CLI quick links (source)

- PDF→Text CLI: `src/abm/ingestion/pdf_to_text_cli.py`
- Classifier CLI: `src/abm/classifier/classifier_cli.py`
- Chapterizer CLI: `src/abm/structuring/chapterizer_cli.py`

## Roadmap

- Multi‑agent roadmap: [05-development/planning/MULTI_AGENT_ROADMAP.md](05-development/planning/MULTI_AGENT_ROADMAP.md)
- Learning path (LangGraph/CrewAI): [03-implementation/multi-agent/LEARNING_PATH_MULTI_AGENT.md](03-implementation/multi-agent/LEARNING_PATH_MULTI_AGENT.md)

## Templates

- Full Design Spec: [templates/FULL_DESIGN_SPEC_TEMPLATE.md](templates/FULL_DESIGN_SPEC_TEMPLATE.md)
- Test Plan: [templates/TEST_PLAN_TEMPLATE.md](templates/TEST_PLAN_TEMPLATE.md)

## Quality

- Quality Gate Spec: [02-specifications/components/QUALITY_GATE_SPEC.md](02-specifications/components/QUALITY_GATE_SPEC.md)

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
