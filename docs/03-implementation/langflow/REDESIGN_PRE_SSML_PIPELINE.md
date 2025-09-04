# Pre-SSML Multi-Agent Pipeline Redesign (Blocks → Spans → Style)

This document captures the agreed redesign to split the audiobook pipeline at the SSML/style boundary and standardize upstream components around JSONL artifacts, deterministic IDs, and 0-based indexing.

## Goals

- Separate text intelligence (upstream) from audio execution (downstream).
- Make each stage idempotent, resumable, and cacheable via JSONL artifacts + sidecar meta.
- Standardize on Blocks and 0-based indices; retain chapter_number (1-based) for reporting.
- Remove legacy components/terminology; keep unified loader.

## Boundary: SSML/Style as the Seam

- Upstream (this doc): segmentation, mixed-block resolution, classification, speaker attribution, character casting, style planning (engine-agnostic StylePlan; optional default SSML).
- Downstream (later): TTS rendering (engine-specific SSML), post-processing, chapter mixing, QC.

Benefits

- Clear separation of concerns and swappable TTS engines.
- Deterministic caches at both sides (text+style vs ssml+engine).
- Test upstream fully offline; avoid TTS costs during development.

## Upstream Stages (pre-SSML)

### 1. Block Schema Validator

- Input: chapters.json (normalized) or in-memory chapters/blocks.
- Output: blocks.jsonl + blocks.meta.json
- Responsibilities:
  - Enforce 0-based: chapter_index, block_id.
  - Include chapter_number (1-based) alongside chapter_index (0-based).
  - Text hygiene: normalize quotes/whitespace; store text_raw and text_norm.
  - Deterministic IDs: block_uid = sha1(book_id|chapter_index|block_id|text_norm_normed).
  - Fail fast on schema issues; count and report in meta.

### 2. Mixed-Block Resolver

- Input: blocks.jsonl
- Output: spans.jsonl + spans.meta.json
- Responsibilities:
  - Split mixed blocks into ordered spans by quote boundaries and obvious markers.
  - Assign segment_id 0-based per block; role ∈ {narration, dialogue} per span.
  - span_uid = sha1(block_uid|segment_id|text_norm_normed).

### 3. Span-level Classifier + Speaker Attribution

- Input: spans.jsonl
- Output: spans_cls.jsonl + spans_cls.meta.json
- Responsibilities:
  - Classifier: type (dialogue/narration/mixed as features), lightweight features (optional).
  - Attribution (dialogue only): speaker (canonical), confidence \[0..1\], evidence\[\], provenance (rules used).
  - Deterministic given same inputs.

### 4. Character Casting

- Input: spans_cls.jsonl + data/casting/voice_bank.json
- Output: spans_cast.jsonl + spans_cast.meta.json
- Responsibilities:
  - Map speaker → voice_id deterministically; provide narrator defaults.
  - Add style_defaults (rate, pitch, emotion) for later style planning.

### 5. Style Planner (Optional here; still upstream)

- Produce vendor-neutral StylePlan: pacing (rate, pauses), pitch, volume, emotion, emphasis spans, pronunciation.
- Optionally render a default SSML dialect (engine tag) for convenience.
- Implemented as `ABMStylePlanner` component. Place after `ABMSpanAttribution`.
- Orchestrator toggle: `enable_style_planner` (writes to `output/<book>/ch<NN>/spans_style.jsonl`).

Downstream starts after this point (TTS, post, mix, QC) and is out of scope for this document.

## JSONL Contracts

All records should include timestamps and version fields in practice (omitted here for brevity). Sidecar meta.json files report counts, timings, and component versions.

- Block record (blocks.jsonl)

  - book_id, chapter_number (1-based), chapter_index (0-based)
  - block_id (0-based), role (if pre-labeled), text_raw, text_norm
  - block_uid (sha1)

- Span record (spans.jsonl)

  - book_id, chapter_index, block_id, segment_id (0-based within block)
  - role ∈ {narration, dialogue}, text_raw, text_norm
  - span_uid (sha1)

- Classified span (spans_cls.jsonl)

  - span_uid, role, text_norm
  - type (dialogue/narration/mixed as classifier label), features? {}
  - speaker?, confidence?, evidence\[\] (dialogue only)
  - provenance {rules, thresholds}

- Cast span (spans_cast.jsonl)

  - span_uid, speaker, voice_id
  - style_defaults {rate, pitch, emotion}
  - casting_provenance

- Styled span (spans_style.jsonl)

  - span_uid, voice_id, StylePlan {...}
  - ssml_default_engine? (optional convenience render)

Deterministic hashing

- Normalize to NFC, lowercase, collapse internal whitespace, trim; then sha1 of the concatenated key string.

## Indexing and Terminology Rules

- Use Blocks and Spans. No “chunks.”
- 0-based indices internally: chapter_index, block_id, segment_id.
- Always include chapter_number (1-based) for human-readable reporting.

## Components: Keep / Tweak / Delete

Delete now

- src/abm/lf_components/audiobook/abm_enhanced_chapter_loader.py (legacy “chunk” component).

Keep (minimal/no change)

- abm_chapter_loader.py (unified loader; ensure it outputs both chapter_index and chapter_number in meta).
- Utilities: abm_data_config.py, abm_postgres_client.py, echo.py.

Tweak to match the new plan

- abm_block_iterator.py → iterate spans (not blocks)

  - Inputs: path to spans.jsonl (or Data payload), start_span (0-based), max_spans.
  - Output: per-span Data with ids {chapter_index, block_id, segment_id}, role, text_raw/text_norm, and pass-through meta.
  - Remove any “chunk” compatibility; enforce 0-based indexing.

- abm_dialogue_classifier.py → span-level

  - Input: span; Output: label + optional features; deterministic.

- abm_speaker_attribution.py → span-level with evidence/confidence

  - Input: classified span; Output: {speaker, confidence, evidence\[\], provenance} (dialogue only).

- abm_casting_director.py → character casting

  - Input: attributed span + voice_bank.json; Output: {voice_id, style_defaults, casting_provenance}.

- abm_utterance_jsonl_writer.py → generalize to spans writer

  - Write records-only JSONL plus sidecar meta; ensure schema matches the above.

Defer/replace after new stages land (then remove)

- abm_results_aggregator.py, abm_results_to_utterances.py (superseded by JSONL artifacts).
- abm_aggregated_jsonl_writer.py (merge into generalized writer).
- abm_two_agent_runner.py / abm_two_agent_runner_component.py
  - Replace with two runners:
    - Upstream runner: chapters → blocks.jsonl → spans.jsonl → spans_cls.jsonl → spans_cast.jsonl (optionally → spans_style.jsonl).
    - Downstream runner: spans_style.jsonl → audio → chapter mix (future).

## Orchestration & Artifacts

- Upstream orchestrator iterates deterministic steps, writes JSONL + meta per stage.
- Use content-addressed caches keyed by the deterministic hashes. Resume by reading the last complete artifact.
- Directory layout (example):
  - `data/clean/<book>/classified/chapters.json`
  - `output/<book>/ch<NN>/blocks.jsonl`
  - `output/<book>/ch<NN>/spans.jsonl`
  - `output/<book>/ch<NN>/spans_cls.jsonl`
  - `output/<book>/ch<NN>/spans_cast.jsonl`
  - `output/<book>/ch<NN>/spans_style.jsonl` (optional)
  - `output/<book>/ch<NN>/*.meta.json`

## Migration Plan (incremental)

1. Add Block Schema Validator; emit blocks.jsonl (+ meta). Fail fast on schema.
1. Add Mixed-Block Resolver; emit spans.jsonl with segment_id and role.
1. Refactor Dialogue Classifier & Speaker Attribution to span-level; emit spans_cls.jsonl with evidence/confidence.
1. Introduce Character Casting; emit spans_cast.jsonl with voice_id and style_defaults.
1. (Optional) Add Style Planner; emit spans_style.jsonl (StylePlan + optional default SSML).
1. Update upstream runner to stop at spans_cast.jsonl (or spans_style.jsonl) by default.
1. Remove Enhanced Chapter Loader; scrub “chunk” terminology in touched files.
1. Deprecate and then remove in-memory aggregators once tests migrate to JSONL artifacts.

## Success Criteria

- Deterministic, resumable upstream with JSONL artifacts at each stage.
- Strict 0-based internals, with chapter_number (1-based) preserved for reporting.
- Accurate mixed-block splitting and stable IDs across runs.
- Dialogue spans consistently attributed with confidence/evidence and deterministically cast.
- Clean separation at SSML/style; downstream can swap engines without upstream changes.

______________________________________________________________________

Owner: Upstream Text Intelligence (pre-SSML)
Status: Proposed
Scope: LangFlow components under src/abm/lf_components/audiobook and associated runners
