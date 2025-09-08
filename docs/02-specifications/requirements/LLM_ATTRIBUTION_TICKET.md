# Ticket: Implement LLM Attribution as a LangFlow Component

Status: Proposed
Owner: ABM Team
Branch: feature/llm-attribution-v1

## Summary

Implement the “LLM Attribution (open-world, local)” stage as a new LangFlow component that resolves dialogue spans left unknown or low-confidence by the heuristic pass, with a strict no-Unknown guarantee.

Reference spec: docs/02-specifications/components/LLM_ATTRIBUTION_SPEC.md

## Goals

- Add a new component ABMLLMAttribution that:
  - Selects target dialogue spans needing attribution.
  - Builds compact local context and calls a local LLM (Ollama default).
  - Validates JSON-only responses, normalizes speaker names, clamps confidence.
  - Applies deterministic caching and robust fallbacks to avoid “Unknown”.
- Provide JSONL IO for headless runs; expose outputs via LangFlow ports.

## Deliverables

- Component: `src/abm/lf_components/audiobook/abm_llm_attribution.py` (name may vary slightly per conventions).
- Backend adapter: `src/abm/attr/ollama_backend.py` (simple HTTP client w/ retries, timeouts).
- Orchestrator: `src/abm/attr/llm_attribution.py` (selection, prompt, validation, caching, fallbacks).
- CLI wrapper (optional, thin): `tools/llm_attr_cli.py` to run on artifacts.
- Unit + integration tests and sample fixtures.
- Minimal docs updates (README snippet, spec link).

## Acceptance Criteria

- No dialogue span remains with speaker "Unknown" or empty after this stage.
- Heuristic high-confidence spans (>= min_conf_for_skip, default 0.85) pass through untouched.
- Deterministic cache: identical payloads hit the same cache key; cache hit ratio reported in meta.
- Strict JSON validation; malformed responses trigger retries, then fallbacks; pipeline does not crash.
- Artifacts written when enabled:
  - `spans_attr_llm.jsonl` with updated attribution fields.
  - `spans_attr_llm.meta.json` with counters, config snapshot, cache stats, retry stats.
- Component configurable in LangFlow with inputs defined in spec.

## Non-Goals

- Building a canonical roster or enforcing cross-chapter consistency (defer to Finalizer).
- Remote/cloud LLMs (local Ollama only for v1).

## Interfaces

- Input: `spans_attr` (records as per heuristic output shape).
- Output: updated `spans_attr` and `meta` (both via LangFlow outputs and optional files).

## Config (defaults)

- model_name: "llama3.1:8b-instruct"
- base_url: <http://localhost:11434>
- temperature: 0.4
- context_radius: 4 spans
- max_json_retries: 2
- min_conf_for_skip: 0.85
- timeout_s: 30
- cache_dir: .cache/abm
- prompt_version: v1
- write_to_disk: false

## Caching

- SHA256 over normalized payload: dialogue text + context + prompt_version + model + component version.
- File layout: `.cache/abm/llm_attr/<shard>/<key>.json` with request, raw_text, parsed_json?, timestamp.

## Fallbacks

- continuity_prev within a short distance window.
- Otherwise best heuristic cue in local narration window.
- As last resort for dialogue: nearest consistent dialogue speaker in block; tag qa_flags.

## Artifacts

- Input: `output/{book_id}/ch{chapter:02d}/spans_attr.jsonl`
- Output: `output/{book_id}/ch{chapter:02d}/spans_attr_llm.jsonl`
- Meta: `output/{book_id}/ch{chapter:02d}/spans_attr_llm.meta.json`

## Tests

- Unit: cache key stability, selection logic, JSON validation, fallbacks.
- Integration: small chapter fixture; verify counts and no-Unknown guarantee.
- Backend mock: return canned JSON and malformed variants to exercise retries.

## Risks

- Hallucinated names: enforce presence in context or continuity; else fallback.
- Over-calling LLM: aggressive caching + min_conf_for_skip.
- Backend instability: retries, tolerant error handling, never crash.

## Rollout

- Phase 1: Implement with feature flag; keep off by default in flows.
- Phase 2: Enable in default pipeline after heuristic pass once validated on 1–2 books.
