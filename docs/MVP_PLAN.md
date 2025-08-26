# MVP Plan – Ingestion v2, JSONL-first Classifier, and Casting Roles

Date: 2025-08-26
Branch: langflow-multi-implement

This document captures the MVP scope, current implementation state, and the missing-but-required roles (Casting Director, Casting Assistant). It also provides precise contracts, data shapes, and a checklist to get to a demonstrable end-to-end path.

## 1) Current State (authoritative summary)

- Ingestion v2 (src/abm/ingestion/ingest_pdf.py)
  - dev (default): writes artifacts + DB insert stub
  - Outputs: {stem}_raw.txt, {stem}_well_done.txt, {stem}_ingest_meta.json, {stem}_well_done.jsonl, {stem}_well_done_meta.json
    - Prints: "[DB STUB] Would insert …"
  - prod: writes no artifacts; DB insert stub only (in-memory)
  - PgInserter removed from pipeline (replaced with `_stub_db_insert` + TODO)
  - JSONL is the canonical handoff for downstream

- Raw → Well-done (src/abm/ingestion/raw_to_welldone.py)
  - Paragraph-first normalization: reflow, dehyphenate, dedupe spaces, strip trailing
  - TOC bullet splitting heuristic; optional heading splitting in code options

- Well-done → JSONL (src/abm/ingestion/welldone_to_json.py)
  - One JSON record per block: { index, text, … }, plus a meta sidecar linking ingest meta

- Classifier (JSONL-first)
  - CLI: src/abm/classifier/classifier_cli.py (sources: .jsonl, .txt, "postgres" stub; --meta optional; --verbose)
  - Core: src/abm/classifier/section_classifier.py
    - Deterministic, block-based
    - TOC detection (lookahead bounded), chapter mapping multi-pass:
      1) exact normalized title
      2) ordinal fallback (decimal/Roman, Prologue/Epilogue)
      3) relaxed prefix/fuzzy (small Levenshtein)
    - Optional single-char separators with whitespace (e.g., ":", "-", "–", ".") for both TOC and headings
    - Single heading per block; monotonic order; zero-based, inclusive spans
  - Verified on MVS JSONL; LotF intentionally not used

- LangFlow components (present)
  - lf_components/ and abm/lf_components/ modules include: chapter_selector, chapter_volume_loader, payload_logger, segment_dialogue_narration, utterance_filter, utterance_jsonl_writer (plus README)

- Docs (added/updated)
  - docs/INGESTION_PIPELINE_V2.md – New ingestion v2 guide
  - docs/INGESTION_V2_INTEGRATION_CHECKLIST.md – Steps to integrate across docs

## 2) Documentation search for Casting roles

Searched for: "casting director", "casting assistant".

- Findings: No dedicated specs found for these named roles. Existing docs reference "Casting (character bible)", voice casting data, and character database, but not explicit role specs.
- Related artifacts: CHARACTER_DATA_COLLECTOR_SPEC.md (data collection for future casting), two-agent systems that build voice profiles.

Conclusion: We should define Casting Director and Casting Assistant roles now.

## 3) Role Definitions (contracts)

### Casting Assistant

Purpose: Build and maintain character profiles from text (dialogue/narration) to inform voice casting.

Inputs:

- JSONL blocks or chapter JSON (chapters.json) with paragraphs
- Dialogue/narration segmentation (from `segment_dialogue_narration` or equivalent)
- Optional speaker attribution hints (if available)

Outputs:

- CharacterProfile records persisted (stub for DB now):
  - character_id (string), aliases (string[])
  - evidence (array of snippets with chapter/block refs)
  - voice_casting_data: { suggested_voice_type, gender_hint?, age_hint?, traits[] }
  - provenance: { book, chapter_index, block_index, timestamp }

API (Python minimal):

- build_profiles(blocks|chapters) -> List[CharacterProfile]
- update_profile(character_id, evidence) -> CharacterProfile
- export_profiles(output_dir|postgres_stub) -> path|None

Error modes:

- Ambiguous speaker: file under UNKNOWN, flag for review
- Conflicting traits: store both and mark conflict

### Casting Director

Purpose: Use CharacterProfiles to assign voices (TTS providers/voices), ensuring consistency and coverage.

Inputs:

- CharacterProfile list (from Assistant)
- Provider catalog (e.g., ElevenLabs, Azure TTS) – metadata only (stub)
- Project constraints: allowed voices, budget tiers, narration/dialect rules

Outputs:

- CastingPlan:
  - narrator_voice: VoiceSpec
  - character_voices: Map<CharacterID, VoiceSpec>
  - rules: { fallback, conflict_resolution, retry_policies }
  - export: JSON for downstream SSML/TTS pipeline

API (Python minimal):

- propose_casting(profiles, constraints) -> CastingPlan
- validate_casting(plan) -> List[issues]
- export_casting(plan, output_dir|postgres_stub) -> path|None

Error modes:

- No available voices for requested traits -> suggest nearest
- Overlapping exclusive voices -> produce conflict list and fallback

Data shapes:

- VoiceSpec: { provider, voice_id, name, gender?, age?, style_tags[] }
- Constraints: { narrator_policy, per-character overrides, blacklists }

## 4) MVP Scope (what we will demo)

- Ingestion v2 dev mode → JSONL + meta (MVS only)
- Classifier → chapters.json, toc.json, front/back
- Casting Assistant (MVP):
  - Parse chapters.json to collect candidate characters (heuristics: quoted speech attribution + simple tags like "said NAME")
  - Build minimal CharacterProfiles (evidence: first 3 quotes per character)
  - Export JSON: data/clean/{book}/casting/character_profiles.json
- Casting Director (MVP):
  - Map CharacterProfiles to placeholder VoiceSpec from a tiny mock catalog
  - Export JSON: data/clean/{book}/casting/casting_plan.json

All DB interactions remain stubbed with TODOs.

## 5) Interfaces and Files

- Inputs (dev mode):
  - data/clean/mvs/*_well_done.jsonl
  - data/clean/mvs/classified/(chapters.json, toc.json, …)
- Outputs:
  - data/clean/mvs/casting/character_profiles.json
  - data/clean/mvs/casting/casting_plan.json

## 6) Testing (pytest)

- Fixtures: small synthetic chapters.json + snippets simulating dialogue blocks
- Assistant tests:
  - Extract speakers from quoted lines with "said NAME" patterns
  - Build profiles with evidence and traits placeholder
  - Handle ambiguous/unattributed lines
- Director tests:
  - Build plan from 2-3 profiles using a mock catalog
  - Validate plan (no duplicate voice for distinct main characters)
  - Export plan JSON shape assertion

## 7) Open TODOs / Stubs

- Replace ingestion DB stub with real Postgres insert when DB ready
- Replace classifier Postgres import stub with real query by meta/document id
- Expose advanced well-done options via CLI if needed (split_headings)
- Add provider catalog integration when we choose TTS vendor(s)

## 8) Checklist to MVP

- [ ] Confirm ingestion dev mode produces JSONL + meta for MVS
- [ ] Run classifier on MVS JSONL → chapters/toc/front/back
- [ ] Implement Casting Assistant (MVP) with export JSON
- [ ] Implement Casting Director (MVP) with export JSON
- [ ] Add pytest for assistant and director (unit-level)
- [ ] Document roles in docs/ (this file plus links from docs/README.md)
- [ ] CLI wiring (optional): tiny scripts to run assistant/director on outputs
- [ ] Verify artifacts under data/clean/mvs/casting/*
- [ ] Prepare demo notes: inputs, commands, outputs

## 9) Non-goals (MVP)

- Real DB writes/reads
- ML speaker attribution beyond heuristics
- Provider API calls for TTS; we stick to static catalogs

---

This plan keeps the MVP deterministic and local: JSONL → chapters → simple profiles → mock casting plan. It’s aligned with the current ingestion v2 and JSONL-first classifier and sets the stage for database-backed and provider-integrated phases.
