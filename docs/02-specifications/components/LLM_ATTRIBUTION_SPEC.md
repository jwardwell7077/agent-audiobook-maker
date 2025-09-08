# LLM Attribution (Open-World, Local)

Status: Draft (for review)
Owner: ABM Team
Last updated: 2025-09-08

## Overview

LLM Attribution is a second-pass speaker attribution stage that resolves dialogue spans that the heuristic stage could not confidently attribute. It operates in an open-world fashion (no pre-baked roster), runs locally (default backend: Ollama), and guarantees no "Unknown" speakers in its outputs by applying conservative fallbacks when the LLM cannot decide with high confidence.

This component consumes the outputs of the heuristic stage (spans_attr) and produces updated spans with speaker, confidence, method, and evidence, plus a meta summary. It may also enrich narration confidence if configured, but its primary job is to resolve dialogue speakers.

## Scope and Goals

- Resolve speaker for dialogue spans marked unknown or low-confidence by the heuristic pass.
- Enforce strict outputs: no "Unknown" speakers after this stage.
- Keep everything local by default; allow pluggable LLM backend (Ollama first).
- Deterministic caching by prompt payload to reduce re-compute/cost and make results reproducible.
- Artifact IO via JSONL to support headless runs and downstream tools.

Non-goals:

- Not responsible for full conversation consistency across chapters (that belongs to Finalizer/Normalization).
- Not responsible for building a canonical character roster (but can hint probable names).

## Contracts

Inputs

- spans_attr.jsonl or in-memory payload from the heuristic component containing an array of records with keys such as: book_id, chapter_index, block_id, segment_id, text_norm/text_raw, type/role, attribution { speaker?, confidence, method, evidence }.
- Config knobs: model name, temperature, context radius (spans or characters), max retries, cache directory, min confidence to skip LLM (if heuristic already high), timeouts.

Outputs

- spans_attr_llm.jsonl (updated): same records with attribution replaced/filled where needed. Every dialogue span must have a non-empty speaker string.
- meta.json (optional): counts, method histogram, retry stats, cache hits/misses, errors (if any), config snapshot.
- In LangFlow, outputs also provided via Data ports for chaining.

Error modes

- LLM returns non-JSON or malformed JSON: retry with stricter extractor rules up to N times; if still failing, apply conservative fallback (continuity_prev or heuristic evidence), mark qa_flags in evidence.
- Backend unavailable: if cache has entry, use it; else mark fallback path and continue (never crash the pipeline by default).

## Data Shapes

Input record (abbreviated):

- {..., type: "dialogue"|"narration", text_norm: str, attribution: { speaker?: str|null, confidence: float, method: str, evidence: dict }, ...}

Output record (dialogue):

- attribution: { speaker: str, confidence: float, method: "llm|llm_fallback|continuity_prev|heuristic_passthrough", evidence: { prompt_version, backend, cache_key, llm: { raw_text?, parsed_json? }, rationale?, qa_flags?: [..] } }

Note: method should include a clear prefix when the LLM was used, e.g., "llm_dialogue_tag", "llm_proximity", or "llm_fallback".

## Decision Logic

1. Span selection

- Target only dialogue spans where: attribution.speaker is null/empty OR attribution.method == "unknown" OR attribution.confidence < min_conf_for_skip.
- Optionally allow re-attribute_all mode for experiments.

1. Context construction

- Use context_radius around the target span within the same block: gather up to N narration spans before/after and the last known dialogue speaker in the block.
- Provide a compact context to stay within model limits. Include:
  - The dialogue text
  - Nearby narration snippets (normalized)
  - Any detected speaker cues from the heuristic (patterns, proper nouns)
  - The previous dialogue speaker in the block (if any)

1. Prompting

- Single-shot JSON-only prompt. The LLM must return a single JSON object with fields: { speaker: string, confidence: 0..1, rationale: string }. No "Unknown" allowed.
- If the LLM proposes a non-name (e.g., pronoun or generic), post-validate and either map to previous speaker (continuity_prev) or lowest-confidence fallback.
- Temperature default moderate (e.g., 0.4) to reduce hallucination and promote deterministic output.

1. Validation & post-processing

- Parse and validate JSON strictly. If malformed, retry up to max_json_retries with minor extraction rules.
- Enforce speaker normalization rules (trim, title-case; blocklisted pronouns ignored).
- Ensure confidence is clamped to [0,1]. If below a minimum threshold after validation, tag qa_flags and optionally blend with deterministic confidence scorer if desired.

1. Fallbacks (no-Unknown guarantee)

- continuity_prev within a short distance window (<= 2 spans) when available.
- Otherwise, choose best heuristic cue from narration window (dialogue tags, proper nouns) with a conservative confidence.
- As a last resort, attribute to "Narrator" only if the span is actually narration; for dialogue spans, pick the nearest consistent dialogue speaker in block (even if weak), and tag qa_flags.

## Backend Interface

- Backend callable signature: (payload: dict[str, Any]) -> dict[str, Any]
  - payload contains: dialogue_text, context_snippets, prev_dialogue_speaker, prompt_version, model/config snapshot.
  - returns raw LLM text. The attributor extracts/validates JSON.
- Default backend: Ollama
  - base_url: <http://localhost:11434>
  - model: e.g., mistral:instruct, llama3.1:8b-instruct
  - timeouts: 30s default; 3 retries on transport errors (separate from JSON retries)

## Caching

- Deterministic, content-addressed via SHA256 of normalized payload (dialogue text + context + prompt_version + model name + component version).
- Cache structure: cache_dir/llm_attr/{key[0:2]}/{key}.json containing { request_payload, raw_text, parsed_json?, timestamp }.
- On hit, skip backend call and reuse.

## Configuration (defaults)

- context_radius: 4 spans
- max_json_retries: 2
- temperature: 0.4
- min_conf_for_skip: 0.85 (if heuristic is already high, passthrough)
- cache_dir: .cache/abm
- model_name: "llama3.1:8b-instruct"
- prompt_version: "v1"
- timeout_s: 30
- write_to_disk: false

## Artifacts

- Input (typical): output/{book_id}/ch{chapter:02d}/spans_attr.jsonl
- Output: output/{book_id}/ch{chapter:02d}/spans_attr_llm.jsonl
- Meta: output/{book_id}/ch{chapter:02d}/spans_attr_llm.meta.json
- Cache: .cache/abm/llm_attr/<sharded_key>.json

## LangFlow Component Design

Name: ABMLLMAttribution

- Inputs:

  - DataInput spans_attr (required)
  - StrInput model_name (default: llama3.1:8b-instruct)
  - StrInput base_url (default: <http://localhost:11434>)
  - FloatInput temperature (0.4)
  - FloatInput min_conf_for_skip (0.85)
  - FloatInput context_radius (4)
  - IntInput max_json_retries (2)
  - StrInput prompt_version ("v1")
  - BoolInput write_to_disk (false)
  - StrInput output_dir (optional; derive if empty)
  - StrInput cache_dir (".cache/abm")
  - FloatInput timeout_s (30)
  - BoolInput re_attribute_all (false)

- Outputs:

  - Output spans_attr_llm (Data: { spans_attr: [...] })
  - Output meta (Data)

Implementation note: There is no existing component that calls an LLM for attribution. We will implement a new component, reusing patterns from `ABMSpanAttribution` for grouping and IO, and introducing a small backend adapter for Ollama.

## Prompt (v1, sketch)

System: You are a careful literary analyst. When given a dialogue line and nearby narration, identify the most likely speaker name that appears in the narration context or can be inferred from continuity. Return only JSON.

User content (fields):

- dialogue_text: "..."
- narration_before: ["...", "..."]
- narration_after: ["...", "..."]
- prev_dialogue_speaker: "Name" | null
- rules: "Do not return Unknown. Choose the most plausible proper name."

Expected assistant response (exactly one JSON object):
{ "speaker": "Name", "confidence": 0.0-1.0, "rationale": "..." }

## Testing

- Unit tests for: cache key stability, JSON validation, fallback coverage, selection of target spans, pass-through behavior when min_conf_for_skip.
- Integration test with a small chapter fixture to verify artifact paths, counts, and no-Unknown guarantee.
- Mock backend returning canned JSON and malformed variants to exercise retries.

## Performance

- Parallelization optional by block or by span; start with sequential per block to keep cache locality and deterministic logs.
- Expect O(N) over spans, with small constant factors per LLM call; cache should eliminate repeats.

## Risks & Mitigations

- Hallucinated names: enforce that names must appear in local context or match recent dialogue continuity; otherwise lower confidence and fallback.
- Over-calling LLM: use min_conf_for_skip and cache aggressively.
- Backend instability: tolerate failures with cache and fallback; never crash the pipeline.

## Rollout

- Phase 1: Implement component + CLI wrapper, default off in flows.
- Phase 2: Add to the default pipeline after heuristic attribution.
- Phase 3: Tune prompt and thresholds on 1–2 books, lock prompt_version.

---

## Open Questions

- Should we keep a global per-chapter roster inferred by the LLM to stabilize names? Proposed: out of scope here; defer to Finalizer.
- Should we blend confidence with deterministic scorer? Proposed: no for v1; store LLM confidence and evidence separately.
