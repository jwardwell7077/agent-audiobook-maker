# Multi-Agent Roadmap

Last updated: 2025-01-14

> KISS scope note: This roadmap reflects the evolution to a two-agent system architecture. On the current KISS branch, we now include PostgreSQL for character database functionality. Start with the `.venv` and `requirements-dev.txt`, then add PostgreSQL as needed for two-agent system implementation.

## Purpose

Structured path to evolve from deterministic ingestion through a sophisticated two-agent system to a production-grade multi-agent audiobook generation system while preserving reproducibility and local-first constraints.

## Phase Overview

| Phase | Focus                          | Primary Outputs                                     | Exit Criteria                                      |
| ----- | ------------------------------ | --------------------------------------------------- | -------------------------------------------------- |
| 0     | Deterministic Ingestion (DONE) | Chapter JSON, Volume Manifest, Hash Snapshot        | Two-cycle identical hashes; snapshot frozen        |
| 1     | LangFlow Prototype (DONE)      | Segmentation components (Loader, Segmenter, Writer) | Importable flow writes utterance JSONL             |
| 1.5   | Two-Agent System (CURRENT)     | Dialogue classifier + Speaker attribution agents    | Database-driven character tracking with confidence |
| 2     | CrewAI Role Agents             | Enhanced QA and emotion analysis agents             | Enriched utterances with quality metrics           |
| 3     | LangGraph Orchestration        | Deterministic state graph for annotation            | Re-runnable graph with resume & caching            |
| 4     | Casting & Voice Profiles       | Character bible + voice mapping                     | Persisted character profiles + TTS profile JSON    |
| 5     | TTS Rendering (XTTS/Piper)     | Stems + chapter renders                             | Real audio files + loudness stats stored           |
| 6     | Mastering & Assembly           | Book-level mastering & QA gating                    | EBU R128-compliant master + QA report              |
| 7     | Observability & Metrics        | Structured logs, metrics, tracing                   | Dashboard with latency, cache hit, GPU util        |
| 8     | Optimization & Scaling         | Parallelism tuning, caching layers                  | Throughput meets target chapters/hr locally        |

## Phase 1.5: Two-Agent System (NEW)

### Architecture Components

| Agent                   | Inputs                      | Outputs                               | Notes                                     |
| ----------------------- | --------------------------- | ------------------------------------- | ----------------------------------------- |
| DialogueClassifierAgent | Raw text segments           | dialogue/narration/mixed + confidence | Hybrid heuristic + AI fallback approach   |
| SpeakerAttributionAgent | Dialogue segments + context | character associations + metadata     | PostgreSQL character database integration |

### Database Integration

- **Character Database**: PostgreSQL with JSONB profiles for flexible character data
- **Alias Resolution**: Automatic handling of character name variations
- **Context Tracking**: Before/after context storage for improved attribution accuracy
- **Confidence Scoring**: Quality metrics for both classification and attribution

### Key Features

- **Hybrid Classification**: 90% heuristic processing, AI fallback for ambiguous cases
- **Character Profiling**: Automatic character record creation and profile building
- **Voice Casting Integration**: Database structure designed for casting decisions
- **Context Windows**: 5-segment analysis windows for improved accuracy

## Detailed Milestones

### Phase 1.5 → 2 Bridge (Two-Agent → CrewAI)

- Integrate existing DialogueClassifierAgent and SpeakerAttributionAgent into CrewAI framework
- Enhance with emotion analysis and advanced QA agents
- Expand character database with behavioral and emotional profiling
- Introduce orchestrated task planning with role-based agent coordination

### CrewAI Agent Roles (Enhanced from Two-Agent Foundation)

| Agent                   | Inputs                           | Outputs                               | Notes                                             |
| ----------------------- | -------------------------------- | ------------------------------------- | ------------------------------------------------- |
| DialogueClassifierAgent | Raw text segments                | dialogue/narration/mixed + confidence | **Existing**: Hybrid heuristic + AI approach      |
| SpeakerAttributionAgent | Dialogue segments + character DB | speaker labels + character metadata   | **Existing**: PostgreSQL integration              |
| EmotionAgent            | Utterances (speaker tagged)      | emotion label + confidence            | **New**: Local classifier + rule smoothing        |
| QAAgent                 | Annotated utterances             | qa_flags per record                   | **New**: Deterministic rules + limited LLM checks |
| ProsodyAgent (later)    | Utterances + emotion             | prosody struct                        | **Future**: Rate/pitch breaks & emphasis          |

### Phase 3 LangGraph Design Principles

- Typed state dataclass: chapter metadata, utterance list, enrichment layers.
- Node granularity: segmentation, speaker_attribution, emotion, prosody, qa, ssml, tts, mastering.
- Determinism: Non-deterministic LLM calls behind caching keyed by (input_hash, model_version, prompt_version).
- Idempotency: Each node writes artifact file + DB row only if hash changed.

### Caching & Hashing Strategy

| Layer        | Hash Inputs                                           | Artifact                      | Notes                                |
| ------------ | ----------------------------------------------------- | ----------------------------- | ------------------------------------ |
| Segmentation | chapter.text_sha256 + segmentation_params             | utterances_v1.jsonl           | Legacy LangFlow component            |
| Dialogue     | segmentation_hash + classifier_params + model_version | utterances_dialogue_v2.jsonl  | **Two-Agent**: Hybrid classification |
| Speaker      | dialogue_hash + speaker_params + char_db_version      | utterances_speaker_v3.jsonl   | **Two-Agent**: Database integration  |
| Emotion      | speaker_hash + emotion_model_version                  | utterances_emotion_v4.jsonl   | Enhanced CrewAI agent                |
| Prosody      | emotion_hash + prosody_rules_version                  | utterances_prosody_v5.jsonl   | Future enhancement                   |
| SSML         | prosody_hash + ssml_template_version                  | chapter.ssml                  | Production rendering                 |
| TTS          | ssml_hash + tts_engine_version + voice_profile_hash   | stems/\*                      | Audio generation                     |
| Master       | render_hashes + mastering_params_version              | chapter.wav / book_master.wav | Final assembly                       |

### Failure / Retry Semantics

- Each node writes a status row with attempt counter and last error.
- Graph can short-circuit on hard failure (e.g., missing stems) or continue with degraded path (fallback voice) based on policy flag.

### GPU Utilization Plan

- Queue TTS tasks (redis or in-memory priority queue) – ensure single GPU saturation not thrash.
- Batch SSML requests by engine when possible (XTTS multi-utterance inference).

### Monitoring Targets

| Metric                                       | Goal                | Notes                                  |
| -------------------------------------------- | ------------------- | -------------------------------------- |
| Segmentation latency / 1k chars              | \<250ms CPU         | Heuristic + lightweight sentence split |
| Speaker attribution latency / 100 utterances | \<8s (LLM local 8B) | Cache hits aim 70%+                    |
| Emotion classification throughput            | >2k utt/s CPU       | Vectorized model inference             |
| TTS real-time factor (RTF)                   | \<1.2               | Sum(stem_duration)/wallclock           |
| Mastering RTF                                | \<0.3               | Loudness normalization + concatenation |
| Cache hit rate (overall)                     | >60%                | Across all enrichment layers           |

### Quality Gates

- Speaker F1 vs small gold set >0.80 before enabling automatic casting.
- Emotion macro-F1 >0.65 baseline (improve w/ fine-tune later).
- Loudness: All chapters -23 LUFS ±1 LU within spec.
- Hash stability test passes after any text or transform change.

### Risks & Mitigations

| Risk                      | Impact                                 | Mitigation                                                |
| ------------------------- | -------------------------------------- | --------------------------------------------------------- |
| LLM drift (model update)  | Inconsistent speaker/emotion over time | Pin model digest; hash prompt + model version             |
| GPU contention            | Slow renders / OOM                     | Queue + max concurrency=1 for heavy model                 |
| Schema creep              | Backward incompatibility               | Versioned annotation layers; migration script             |
| Silent cache corruption   | Stale artifacts                        | Include params + version in hash; periodic integrity scan |
| Audio quality regressions | Poor UX                                | Loudness + clipping metrics gate merges                   |

### Open Questions

- Will we persist intermediate speaker attribution chain-of-thought? (Probably no; store rationale subset.)
- Introduce embedding-based retrieval for context inside attribution? (Phase 3 add-on.)

### De-Scope Triggers

If any phase exceeds its timebox by >50% without critical learning, capture lessons, document gaps, and advance to next phase (avoid over-fitting prototype).

## Implementation Order (Next 2 Weeks Snapshot)

1. Finalize segmentation JSONL schema versioning (v1) + tests.
1. Implement SpeakerAttributionAgent (CrewAI) with caching.
1. Add enriched schema doc & update `ANNOTATION_SCHEMA.md` (v2 fields).
1. Introduce LangGraph state dataclass & port existing segmentation.
1. Add caching layer for LLM calls (sqlite or simple file map).
1. Implement EmotionAgent + QAAgent deterministic rules.
1. Prep TTS renderer skeleton (XTTS or Piper) reading SSML.

## Exit Criteria to Claim "Annotation Phase Complete"

- All v2 schema fields populated (speaker, emotion, qa_flags, confidence fields).
- Re-runnable LangGraph graph across a sample chapter without non-deterministic diffs (aside from expected LLM rationale text, which is excluded from hash).
- Tests: segmentation determinism, speaker attribution caching, emotion classification throughput baseline.

______________________________________________________________________

Add new sections as phases progress; keep table at top concise for quick orientation.
