# Spans Attribution Contract (spans_attr)

Status: Active (branch snapshot-2025-08-31-wip)

This document defines the contract for `spans_attr` produced by the attribution pipeline. The authoritative JSON Schema is in `spans_attr.schema.json`.

- Schema file: `docs/02-specifications/data-schemas/spans_attr.schema.json`
- Producer components:
  - `src/abm/lf_components/audiobook/abm_span_attribution.py`
  - Orchestrator: `src/abm/lf_components/audiobook/abm_artifact_orchestrator.py`

## Bundle shape

Top-level bundle returned by components and written to disk:

```json
{
  "spans_attr": [ { /* SpanAttributionRecord */ } ]
}
```

## SpanAttributionRecord (summary)

- Required core fields:
  - book_id, chapter_index, chapter_number, block_id, segment_id
  - type: "dialogue" | "narration"
  - character_name: string ("Narrator" for narration; never "Unknown"  choose best candidate and add QA flag when low confidence)
  - attribution: { confidence: number, method: string, evidence: object }
  - provenance: { rules: string, version: string }
- Optional fields:
  - span_uid, role, text_norm, character_id

See the JSON Schema for exact types and allowed values.

## attribution field

- confidence: 0.0–1.0
- method: one of
  - dialogue_tag (explicit pattern like "... , Quinn said")
  - proper_noun_proximity (nearest proper noun in adjacent narration)
  - continuity_prev (opt-in fallback: previous dialogue speaker within a short window)
  - unknown (no speaker detected)  internal marker only; still emit best-guess speaker and add `MANDATORY_REVIEW_LLM`
- evidence: object with optional sub-objects
  - detection: { location, pattern, method, excerpt, distance }
  - confidence: scorer-specific details when deterministic scoring is enabled

## Producer knobs (stable)

Available on `ABMSpanAttribution` and forwarded by `ABMArtifactOrchestrator`:

- use_deterministic_confidence: bool (default true)
- search_radius_spans: number (default 4)
- narration_confidence: number (default 0.95) or use_narration_confidence_evidence: bool
- enable_continuity_prev: bool (default false)
- continuity_max_distance_spans: number (default 2)

## Backward compatibility

- A compatibility shim exists for deterministic confidence imports at `src/abm/lf_components/audiobook/deterministic_confidence.py` while code migrates to `abm.helpers.deterministic_confidence`.
- Pronoun blocklist prevents false speaker names (e.g., "He", "She").

## Example

```json
{
  "book_id": "bk",
  "chapter_index": 0,
  "chapter_number": 1,
  "block_id": 10,
  "segment_id": 3,
  "type": "dialogue",
  "text_norm": "\"Hello.\"",
  "character_name": "Quinn",
  "character_id": "quinn",
  "attribution": {
    "confidence": 0.86,
    "method": "dialogue_tag",
    "evidence": {
      "detection": {"location": "before", "pattern": "... said", "distance": 1},
      "confidence": {"signals": ["dialogue_tag"], "distance": 1}
    }
  },
  "provenance": {"rules": "adjacent_narration_tag_or_proper_noun", "version": "1.0"}
}
```
