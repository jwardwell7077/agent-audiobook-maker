# Learning Path: Multi‑Agent Systems (Practical, KISS‑aligned)

Last updated: 2025‑09‑04

Goal: Build intuition and muscle memory across LangChain, LangSmith, LangGraph, and CrewAI while shipping small, verifiable slices inside this repo.

Principles

- Keep it local‑first. Prefer toy data and stub models initially. Cloud QA only with explicit approval and a visible cost estimate.
- One concept per commit. Leave breadcrumbs in [Development Journey](../../05-development/journey/DEVELOPMENT_JOURNEY.md).
- Make every step reproducible. Cache/seed where non‑determinism is involved; run per chapter.

Milestones (2–3 hours each)

1. Visual prototyping (optional)

 
- Export the flow as JSON; commit under `docs/flows/segmentation_v1.json`.
- Success: Running the flow writes `data/annotations/utterances_v1.jsonl` deterministically for a sample file.

2. LangChain – components as reusable tools

- Wrap the sentence splitter and JSONL writer as LangChain tools/chains.
– Success: Same output JSONL across implementations for identical inputs (hash match).

3. LangSmith – tracing and evaluation (local/dev)

- Enable LangSmith tracing (env toggled off by default; document how to opt-in).
- Record one segmentation run; attach run URL (or local export) to DEVELOPMENT_JOURNEY.md.
- Success: You can view the run trace and basic timing for each step.

4. CrewAI – task/role agents

- Create three simple agents: SpeakerAttributionAgent (stub rules), EmotionAgent (stub rules), QAAgent (rule checks).
- Orchestrate them with a Crew to process the utterances JSONL from Milestone 1.
- Success: Produce `utterances_speaker_v2.jsonl` with added fields as per [Annotation Schema](../../02-specifications/data-schemas/ANNOTATION_SCHEMA.md); no "UNKNOWN" speakers. When confidence < 0.90, emit your best guess and add `qa_flags: ["MANDATORY_REVIEW_LLM"]`.

5. LangGraph – deterministic orchestration

- Define a typed state dataclass and nodes for: segmentation → speaker_attribution → emotion → qa.
- Implement per‑chapter, file‑based caching keyed by `(text_sha256, params_sha256, version)`.
- Success: Re‑running the graph without changes performs zero work; with change, only affected nodes run.

6. Stitching + tests

- Add unit tests for: caching hit/miss, basic agent transforms, graph resume.
- Wire into `make quality_gate` to keep the bar.
- Success: CI remains green with >99% coverage on new modules and 100% docstrings.

Nice-to-haves (later)

- Replace stub rules with local LLM calls (e.g., Ollama) behind a cache.
- Add simple web UI to visualize the LangGraph state per chapter.
- Introduce LangSmith evaluations for speaker attribution against a tiny gold set.

Pointers

- Roadmap: ../../05-development/planning/MULTI_AGENT_ROADMAP.md
- Schemas: ../../02-specifications/data-schemas/ANNOTATION_SCHEMA.md, ../../02-specifications/data-schemas/STRUCTURED_JSON_SCHEMA.md
- Quality gate: ../../02-specifications/components/QUALITY_GATE_SPEC.md
