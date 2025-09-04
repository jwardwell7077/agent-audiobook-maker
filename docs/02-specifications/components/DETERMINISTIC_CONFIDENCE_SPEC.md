# Deterministic Confidence Scoring Specification

Status: Draft
Version: 1.0
Owner: ABM Upstream (Attribution)
Last updated: 2025-09-02

## 1. Purpose & Scope

Provide a deterministic, explainable confidence score in \[0,1\] for dialogue speaker attribution, using local cues and continuity. This score stabilizes upstream artifacts, supports UI filtering, and sets a baseline before any ML/LLM fallback.

Out of scope: ML-based speaker ID, cross-chapter coreference, and language-specific NLP beyond simple regex.

## 2. Requirements

R1. Deterministic: For identical inputs, outputs must be identical.
R2. Explainable: Output must include evidence: raw feature weights and parameters.
R3. Bounded: Confidence must be clamped to \[min_confidence, max_confidence\].
R4. Configurable: Weights and bounds must be configurable with safe defaults.
R5. Locality: Only local context (adjacent narration spans and immediate continuity) is used.
R6. Non-intrusive: If disabled, attribution falls back to base/unknown constants.
R7. Integration: Plug-in scoring for `ABMSpanAttribution`; no change to span IDs or schemas beyond attribution.evidence.
R8. Tests: Unit tests must cover primary signals and continuity behavior.

## 3. Interface Specification

Component: `DeterministicConfidenceScorer`

Inputs (to `score` method):

- dialogue_text: string (the dialogue span text, normalized)
- before_text: string|null (adjacent narration text before)
- after_text: string|null (adjacent narration text after)
- detected_method: string|null ("dialogue_tag" | "proper_noun_proximity" | null)
- detected_speaker: string|null (the speaker name inferred, if any)
- prev_dialogue_speaker: string|null (last attributed dialogue speaker within the block)

Outputs:

- confidence: float in \[min_confidence, max_confidence\]
- evidence: object with
  - confidence_method: "deterministic_v1"
  - raw_score: float (sum of feature weights)
  - features: { feature_name: weight }
  - params: { sigmoid_scale, min, max }
- method: "deterministic_v1"

Errors: none (function is total). In edge cases, missing inputs simply omit feature contributions.

## 4. Scoring Model

### 4.1 Features (binary presence → add weight)

- dialogue_tag (w_dialogue_tag): Explicit tag in adjacent narration (e.g., "...", Quinn said)
- proper_noun_proximity (w_proper_noun_proximity): First proper noun in adjacent narration used as proxy
- continuity_prev_same (w_continuity_prev_same): Previous dialogue speaker equals current detected speaker
- adjacent_narration_present (w_adjacent_narration_present): Either before or after narration exists

Weights default:

- w_dialogue_tag = 3.0
- w_proper_noun_proximity = 1.5
- w_continuity_prev_same = 0.75
- w_adjacent_narration_present = 0.25

Raw score = sum(weights for present features)

### 4.2 Logistic Mapping and Clamp

- logistic(x) = 1 / (1 + exp(-k·x)), with sigmoid_scale k = 0.6
- confidence = min + (max - min) * logistic(raw)
- Clamp to \[min_confidence, max_confidence\] to prevent extreme 0/1 and ensure stability
- Defaults: min=0.35, max=0.95

Rationale: The clamp ensures confidence exceeds unknown baseline when a speaker is found, but never reaches unjustified certainty.

## 5. Integration with ABMSpanAttribution

- New input: `use_deterministic_confidence: bool` (default true)
- On dialogue spans with a detected speaker:
  - Compute confidence via scorer
  - Merge evidence: `{ detection: <existing>, confidence: <scorer evidence> }`
  - Track `prev_dialogue_speaker` per (book_id, chapter_index, block_id)
- On unknown or non-dialogue spans:
  - Confidence uses existing constants (unknown/base) and evidence remains detection-only
- No changes to span_uid or structural keys; only `attribution` is enriched.

## 6. Data Schema Impact

Record fragment in `spans_attr.jsonl`:

```json
{
  "character_name": "Quinn",
  "attribution": {
    "confidence": 0.84,
    "method": "dialogue_tag",
    "evidence": {
      "detection": { "location": "after", "pattern": "..." },
      "confidence": {
        "confidence_method": "deterministic_v1",
        "raw_score": 4.25,
        "features": { "dialogue_tag": 3.0, "continuity_prev_same": 0.75, "adjacent_narration_present": 0.25 },
        "params": { "sigmoid_scale": 0.6, "min": 0.35, "max": 0.95 }
      }
    }
  }
}

```

Schema version: unchanged for now; fields are additive within `attribution.evidence`.

## 7. Error Handling

- No exceptions by design; missing or null inputs reduce feature signals to zero.
- Downstream can rely on bounds and presence of `confidence_method` when enabled.

## 8. Testing Criteria

Unit tests:

- Dialogue tag yields higher confidence than proximity alone
- Continuity increases or maintains confidence (no unreasonable drop)
- Evidence includes required keys and parameters

Integration tests:

- `ABMSpanAttribution` produces `attribution.evidence.confidence` when enabled
- Toggle off falls back to constant confidence

## 9. Configuration

Exposed via `DeterministicConfidenceConfig`:

- Weights: w_dialogue_tag, w_proper_noun_proximity, w_continuity_prev_same, w_adjacent_narration_present
- sigmoid_scale
- min_confidence, max_confidence

Future: allow override from component inputs or YAML config; persist chosen config in meta for audit.

## 10. Non‑Goals and Limits

- No NLP tokenization beyond simple regex for proper nouns
- No cross-block or cross-chapter continuity chains
- No multi-candidate scoring; assumes a single detected speaker per dialogue span

## 11. Migration & Rollout

- Default on (use_deterministic_confidence = true) for LangFlow attribution node
- Backward compatible: disabling restores prior behavior
- Monitor artifact diffs on sample chapters; document any baseline changes

## 12. Open Questions

- Should we expose a UI threshold to hide low-confidence dialogue by default?
- Add tie-break rules when multiple candidate names appear in adjacent narration?
- Persist config parameters into chapter-level meta?

## 13. Downstream Consumption (Filtering)

While scoring is upstream and deterministic, consumers may choose to filter dialogue by confidence. The LangFlow `ABMSpanIterator` supports an optional `min_confidence_pct` input (0–100). When set (>0), dialogue spans with `attribution.confidence` below the threshold are filtered out; non-dialogue spans are unaffected. This enables simple preview modes (e.g., show only ≥75% confident dialogue) without changing the artifacts.
