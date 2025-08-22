# Learning Path: Multi‑Agent Systems (Practical, KISS‑aligned)

Last updated: 2025‑08‑21

Goal: Build intuition and muscle memory across LangFlow, LangChain, LangSmith, LangGraph, and CrewAI while shipping small, verifiable slices inside this repo.

Principles

- Keep it local-first. Prefer toy data and stub models initially.
- One concept per commit. Leave breadcrumbs in docs/DEVELOPMENT_JOURNEY.md.
- Make every step reproducible. Cache/seed where non-determinism is involved.

Milestones (2–3 hours each)

1. LangFlow – visual prototyping

 - Install LangFlow locally and run a minimal “Segmentation flow”: Input text → sentence split → JSONL writer.
 - Export the flow as JSON; commit under `docs/flows/segmentation_v1.json`.
 - Success: Running the flow writes `data/annotations/utterances_v1.jsonl` deterministically for a sample file.

2. LangChain – components as reusable tools

 - Wrap the sentence splitter and JSONL writer as LangChain tools/chains.
 - Write a tiny script `src/demos/langchain_segmentation.py` that mirrors the LangFlow behavior.
 - Success: Same output JSONL as LangFlow for identical inputs (hash match).

3. LangSmith – tracing and evaluation (local/dev)

 - Enable LangSmith tracing (env toggled off by default; document how to opt-in).
 - Record one segmentation run; attach run URL (or local export) to DEVELOPMENT_JOURNEY.md.
 - Success: You can view the run trace and basic timing for each step.

4. CrewAI – task/role agents

 - Create three simple agents: SpeakerAttributionAgent (stub rules), EmotionAgent (stub rules), QAAgent (rule checks).
 - Orchestrate them with a Crew to process the utterances JSONL from Milestone 1.
 - Success: Produce `utterances_speaker_v2.jsonl` with added fields as per docs/ANNOTATION_SCHEMA.md.

5. LangGraph – deterministic orchestration

 - Define a typed state dataclass and nodes for: segmentation → speaker_attribution → emotion → qa.
 - Implement file-based caching keyed by input hash and params.
 - Success: Re-running the graph without changes performs zero work; with change, only affected nodes run.

6. Stitching + tests

 - Add unit tests for: caching hit/miss, basic agent transforms, graph resume.
 - Wire into `make quality_gate` to keep the bar.
 - Success: CI remains green with >99% coverage on new modules and 100% docstrings.

Nice-to-haves (later)

- Replace stub rules with local LLM calls (e.g., Ollama) behind a cache.
- Add simple web UI to visualize the LangGraph state per chapter.
- Introduce LangSmith evaluations for speaker attribution against a tiny gold set.

Pointers

- Roadmap: docs/MULTI_AGENT_ROADMAP.md
- Schemas: docs/ANNOTATION_SCHEMA.md, docs/STRUCTURED_JSON_SCHEMA.md
- Quality gate: docs/design/QUALITY_GATE_SPEC.md
