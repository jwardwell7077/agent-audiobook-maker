# Multi‑Agent Architecture (MVP, deterministic-first)

Date: 2025-08-26

This document defines the agent lineup, contracts, data flows, and determinism guardrails for the MVP end‑to‑end audiobook pipeline using Postgres and local files.

## Agent lineup (MVP)

1. DialogueClassifierAgent (deterministic)

- Input: `chapters.json` paragraphs
- Output: `utterances.jsonl` with dialogue/narration labels + stats
- DB: Insert/Update `annotations` (records JSONB pointer, counts, hashes)

1. SpeakerAttributionAgent (deterministic-first; AI optional)

- Input: `utterances.jsonl`
- Output: speaker labels per utterance or UNKNOWN; QA flags
- DB: Upsert `characters`; Update `annotations` with speaker labels

1. AliasResolverAgent (deterministic)

- Input: character mentions & frequencies
- Output: canonical name map; aliases list
- DB: Update `characters.profile` JSONB (aliases)

1. CastingAssistantAgent (deterministic)

- Input: labeled utterances
- Output: `character_profiles.json`; trait placeholders
- DB: Update `characters.profile` JSONB (traits scaffold)

1. CastingDirectorAgent (deterministic)

- Input: CharacterProfiles + local voice catalog
- Output: `casting_plan.json`; upsert `tts_profiles`
- DB: Upsert `tts_profiles`

1. SSMLAgent (deterministic)

- Input: utterances + casting
- Output: SSML files per chapter; paths recorded in DB
- DB: Update `annotations` (ssml paths)

1. TTSAgent (deterministic-config; bounded variance)

- Input: SSML files, voice ids
- Output: audio stems on disk
- DB: Insert `stems` rows (path, duration, hashes, status)

1. MasteringAgent (deterministic)

- Input: stems
- Output: chapter WAV normalized to EBU R128; loudness metrics
- DB: Upsert `renders` row (path, loudness_lufs, peak_dbfs, duration, hashes)

## Determinism policy

- Deterministic: ingestion, section classification, SSML, DB upserts, orchestration.
- AI/LLM (optional): temp=0, fixed seeds; always cached by (input, model, prompt, version).
- Audio: accept bounded variance; enforce metric bands (LUFS ±0.1 dB, duration ±5 ms).

## Orchestration & idempotency

- Run per chapter in order: Dialogue → Speaker → Alias → Casting → SSML → TTS → Master.
- Hash inputs as (text_sha256, params_sha256, version); skip when unchanged.
- Postgres upserts with unique keys ensure exactly-once semantics for re-runs.

## Diagram

See these diagrams in `docs/diagrams/`:

- `multi_agent_sequence.mmd` – agent interaction sequence with DB and filesystem
- `multi_agent_c4_context.mmd` – C4 System Context (local-first boundary)
- `multi_agent_c4_container.mmd` – C4 Container view (components and relations)
