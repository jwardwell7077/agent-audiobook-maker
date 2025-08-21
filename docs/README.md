# Documentation Index

AI‑generated, Copilot‑assisted. This index organizes the docs for fast navigation.

## Overview & Policy

- KISS policy: [KISS.md](KISS.md)
- Project context: [CONTEXT.md](CONTEXT.md)
- Development journey: [DEVELOPMENT_JOURNEY.md](DEVELOPMENT_JOURNEY.md)
- Lessons learned: [LESSONS_LEARNED.md](LESSONS_LEARNED.md)

### Tenets (short)

- KISS
- TDD + spec-first
- Local-first artifacts
- Deterministic + contract-first

## Architecture

- High‑level architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
  - Diagram source: [diagrams/high_level_architecture.mmd](diagrams/high_level_architecture.mmd)

## Data Contracts / Schemas

- Structured JSON (volume manifest + per‑chapter): [STRUCTURED_JSON_SCHEMA.md](STRUCTURED_JSON_SCHEMA.md)
  - Diagram: [diagrams/structured_json_schema.mmd](diagrams/structured_json_schema.mmd)
- Annotation schema: [ANNOTATION_SCHEMA.md](ANNOTATION_SCHEMA.md)

## Section Classifier

- Design spec: [SECTION_CLASSIFIER_SPEC.md](SECTION_CLASSIFIER_SPEC.md)
  - Flow diagram: [diagrams/section_classifier.mmd](diagrams/section_classifier.mmd)
  - FSM diagram: [diagrams/section_classifier_fsm.mmd](diagrams/section_classifier_fsm.mmd)

## Roadmap

- Multi‑agent roadmap: [MULTI_AGENT_ROADMAP.md](MULTI_AGENT_ROADMAP.md)

## Templates

- Full Design Spec: [templates/FULL_DESIGN_SPEC_TEMPLATE.md](templates/FULL_DESIGN_SPEC_TEMPLATE.md)
- Test Plan: [templates/TEST_PLAN_TEMPLATE.md](templates/TEST_PLAN_TEMPLATE.md)

## How to read this repo

- Start with [KISS.md](KISS.md) and the root README’s Quickstart.
- Skim [ARCHITECTURE.md](ARCHITECTURE.md), then the Structured JSON/Annotation schemas.
- Dive into the Section Classifier spec if you’re extending ingestion.
- Reference Context/Journey/Lessons for rationale and decisions.
