# Stage B: LLM Refinement (Roster-Constrained)

Status: Draft
Owner: ABM Team
Last updated: 2025-09-08

## Purpose & Scope

Stage B revisits spans tagged by Stage A and resolves low-confidence or
`Unknown` speakers using a local or remote LLM service. It operates in a
closed-world mode: answers must come from the roster supplied per
chapter. The component produces updated annotation JSON and an optional
review summary.

## Requirements

1. **Candidate selection** – Only spans with `type` in {`Dialogue`,
   `Thought`} and `confidence < min_conf_for_skip` or speaker
   `Unknown` are considered.
2. **Roster-constrained prompting** – Prompts include the chapter
   roster and must return a speaker name from that roster or
   `Unknown`.
3. **Majority vote** – Query the LLM `votes` times and pick the speaker
   with the highest reported confidence.
4. **Caching** – Persist decisions in SQLite keyed by prompt hash and
   model to avoid re-querying identical contexts.
5. **Acceptance policy** – Apply results only when confidence improves
   or speaker changes; enforce a minimum confidence floor for accepted
   speakers.
6. **Outputs** – Write `combined_refined.json` and optional
   `review_refined.md`. Cache file lives next to the JSON unless a
   path is supplied.
7. **Service management** – When `--manage-llm` is set, start the local
   Ollama service if it is down and stop it on completion.

## Interface Specification

### CLI

`python -m abm.annotate.llm_refine --help`

### Python

`refine_document(tagged_path, out_json, out_md, backend, cfg,
manage_service=False, cache_path=None)`

- `tagged_path` – Path to Stage A `combined.json`.
- `out_json` – Path for refined JSON.
- `out_md` – Optional review markdown path.
- `backend` – `LLMBackend` describing endpoint and model.
- `cfg` – `LLMRefineConfig` (thresholds, votes, token limits).
- `manage_service` – Start/stop local service (Ollama) automatically.
- `cache_path` – Optional SQLite file path.

## Data Flow

1. Read Stage A `combined.json`.
2. `LLMCandidatePreparer` extracts low-confidence spans and roster data.
3. For each candidate:
   - Build left/mid/right context window.
   - Check SQLite cache for existing decision.
   - If miss, query LLM via `OpenAICompatClient` `votes` times.
   - Persist highest-confidence answer in cache.
   - Apply to in-memory document when it improves confidence.
4. Write refined JSON and optional review markdown summarising unknown
   counts per chapter.

## Caching

- Cache key: SHA-256 of model name, roster keys, span type and
  text context.
- Stored value: JSON object `{speaker, confidence}`.
- Cache file default: `<out_json>.cache.sqlite`.

## Error Handling

- If the LLM endpoint is unreachable and `--manage-llm` is not set,
  the refinement aborts with an error.
- When `--manage-llm` is set, the service is started and readiness is
  polled for up to 45 seconds.
- Malformed JSON responses are treated as `speaker="Unknown"` with
  `confidence=0.0` and cached.
- Cache operations swallow parsing errors and proceed without raising.

## Testing Criteria

- Unit tests cover candidate extraction and refinement application.
- Integration test exercises majority vote and cache reuse.
- CLI `--help` runs without contacting an LLM backend.

## Dependencies

- Python 3.11+
- `requests` for HTTP calls
- SQLite (standard library)
- Local LLM service such as Ollama or any OpenAI-compatible endpoint

