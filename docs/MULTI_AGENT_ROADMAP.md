# Multi-Agent Roadmap

Last updated: 2025-08-14

## Purpose

Structured path to evolve from a deterministic ingestion core into a production-grade multi-agent audiobook generation system while preserving reproducibility and local-first constraints.

## Phase Overview

| Phase | Focus | Primary Outputs | Exit Criteria |
|-------|-------|-----------------|---------------|
| 0 | Deterministic Ingestion (DONE) | Chapter JSON, Volume Manifest, Hash Snapshot | Two-cycle identical hashes; snapshot frozen |
| 1 | LangFlow Prototype | Segmentation components (Loader, Segmenter, Writer) | Importable flow writes utterance JSONL |
| 2 | CrewAI Role Agents | Speaker, Emotion, QA agents | Enriched utterances (speaker/emotion/conf flags) |
| 3 | LangGraph Orchestration | Deterministic state graph for annotation | Re-runnable graph with resume & caching |
| 4 | Casting & Voice Profiles | Character bible + voice mapping | Persisted character profiles + TTS profile JSON |
| 5 | TTS Rendering (XTTS/Piper) | Stems + chapter renders | Real audio files + loudness stats stored |
| 6 | Mastering & Assembly | Book-level mastering & QA gating | EBU R128-compliant master + QA report |
| 7 | Observability & Metrics | Structured logs, metrics, tracing | Dashboard with latency, cache hit, GPU util |
| 8 | Optimization & Scaling | Parallelism tuning, caching layers | Throughput meets target chapters/hr locally |

## Detailed Milestones

### Phase 1 → 2 Bridge (LangFlow → CrewAI)

- Replace heuristic dialogue tagging with speaker attribution task agent.
- Introduce message-passing contract: Utterance list -> Task plan -> Attributions.
- Persist interim artifacts (speaker attribution JSONL v2) for rollback.

### CrewAI Agent Roles (Initial)

| Agent | Inputs | Outputs | Notes |
|-------|--------|---------|-------|
| SpeakerAttributionAgent | Utterances (text, is_dialogue) | speaker labels + confidence | LLM (Ollama) + heuristic fallback |
| EmotionAgent | Utterances (speaker tagged) | emotion label + confidence | Local classifier + rule smoothing |
| QAAgent | Annotated utterances | qa_flags per record | Deterministic rules + limited LLM checks |
| ProsodyAgent (later) | Utterances + emotion | prosody struct | Rate/pitch breaks & emphasis suggestions |

### Phase 3 LangGraph Design Principles

- Typed state dataclass: chapter metadata, utterance list, enrichment layers.
- Node granularity: segmentation, speaker_attribution, emotion, prosody, qa, ssml, tts, mastering.
- Determinism: Non-deterministic LLM calls behind caching keyed by (input_hash, model_version, prompt_version).
- Idempotency: Each node writes artifact file + DB row only if hash changed.

### Caching & Hashing Strategy

| Layer | Hash Inputs | Artifact |
|-------|-------------|----------|
| Segmentation | chapter.text_sha256 + segmentation_params | utterances_v1.jsonl |
| Speaker | segmentation_hash + speaker_params + model_version | utterances_speaker_v2.jsonl |
| Emotion | speaker_hash + emotion_model_version | utterances_emotion_v3.jsonl |
| Prosody | emotion_hash + prosody_rules_version | utterances_prosody_v4.jsonl |
| SSML | prosody_hash + ssml_template_version | chapter.ssml |
| TTS | ssml_hash + tts_engine_version + voice_profile_hash | stems/* |
| Master | render_hashes + mastering_params_version | chapter.wav / book_master.wav |

### Failure / Retry Semantics

- Each node writes a status row with attempt counter and last error.
- Graph can short-circuit on hard failure (e.g., missing stems) or continue with degraded path (fallback voice) based on policy flag.

### GPU Utilization Plan

- Queue TTS tasks (redis or in-memory priority queue) – ensure single GPU saturation not thrash.
- Batch SSML requests by engine when possible (XTTS multi-utterance inference).

### Monitoring Targets

| Metric | Goal | Notes |
|--------|------|-------|
| Segmentation latency / 1k chars | <250ms CPU | Heuristic + lightweight sentence split |
| Speaker attribution latency / 100 utterances | <8s (LLM local 8B) | Cache hits aim 70%+ |
| Emotion classification throughput | >2k utt/s CPU | Vectorized model inference |
| TTS real-time factor (RTF) | <1.2 | Sum(stem_duration)/wallclock |
| Mastering RTF | <0.3 | Loudness normalization + concatenation |
| Cache hit rate (overall) | >60% | Across all enrichment layers |

### Quality Gates

- Speaker F1 vs small gold set >0.80 before enabling automatic casting.
- Emotion macro-F1 >0.65 baseline (improve w/ fine-tune later).
- Loudness: All chapters -23 LUFS ±1 LU within spec.
- Hash stability test passes after any text or transform change.

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM drift (model update) | Inconsistent speaker/emotion over time | Pin model digest; hash prompt + model version |
| GPU contention | Slow renders / OOM | Queue + max concurrency=1 for heavy model |
| Schema creep | Backward incompatibility | Versioned annotation layers; migration script |
| Silent cache corruption | Stale artifacts | Include params + version in hash; periodic integrity scan |
| Audio quality regressions | Poor UX | Loudness + clipping metrics gate merges |

### Open Questions

- Will we persist intermediate speaker attribution chain-of-thought? (Probably no; store rationale subset.)
- Introduce embedding-based retrieval for context inside attribution? (Phase 3 add-on.)

### De-Scope Triggers

If any phase exceeds its timebox by >50% without critical learning, capture lessons, document gaps, and advance to next phase (avoid over-fitting prototype).

## Implementation Order (Next 2 Weeks Snapshot)

1. Finalize segmentation JSONL schema versioning (v1) + tests.
2. Implement SpeakerAttributionAgent (CrewAI) with caching.
3. Add enriched schema doc & update `ANNOTATION_SCHEMA.md` (v2 fields).
4. Introduce LangGraph state dataclass & port existing segmentation.
5. Add caching layer for LLM calls (sqlite or simple file map).
6. Implement EmotionAgent + QAAgent deterministic rules.
7. Prep TTS renderer skeleton (XTTS or Piper) reading SSML.

## Exit Criteria to Claim "Annotation Phase Complete"

- All v2 schema fields populated (speaker, emotion, qa_flags, confidence fields).
- Re-runnable LangGraph graph across a sample chapter without non-deterministic diffs (aside from expected LLM rationale text, which is excluded from hash).
- Tests: segmentation determinism, speaker attribution caching, emotion classification throughput baseline.

---

Add new sections as phases progress; keep table at top concise for quick orientation.
