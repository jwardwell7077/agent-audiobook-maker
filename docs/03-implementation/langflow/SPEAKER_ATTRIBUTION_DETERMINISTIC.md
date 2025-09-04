# Deterministic Speaker Attribution: Controls and Behavior

Status: Active
Last updated: 2025-09-02

This note documents the current deterministic speaker attribution behavior and the knobs surfaced in both `ABMSpanAttribution` and the `ABMArtifactOrchestrator`.

## Components and Files

- Attribution component: `src/abm/lf_components/audiobook/abm_span_attribution.py`
- Orchestrator (for one-touch runs): `src/abm/lf_components/audiobook/abm_artifact_orchestrator.py`
- Deterministic scorer: `src/abm/helpers/deterministic_confidence.py`

## Inputs (Attribution)

- use_deterministic_confidence: bool (default: true)
  - Enables the deterministic, explainable confidence from `DeterministicConfidenceScorer` on dialogue spans with a detected speaker.
- search_radius_spans: number (default: 4)
  - Size of the local window over narration spans when inferring speakers (e.g., “Quinn said”). Larger windows consider more nearby narration; keep small to reduce drift.
- narration_confidence: number in \[0,1\] (default: 0.95)
  - Confidence to apply to narration spans when evidence is not computed.
- use_narration_confidence_evidence: bool (default: false)
  - When true, narration spans include confidence evidence; otherwise a fixed `narration_confidence` is used.

## Detection Methods and Rules

- Methods considered for dialogue spans:
  - dialogue_tag: Explicit tags like “..., Quinn said” in adjacent narration.
  - proper_noun_proximity: First proper noun in adjacent narration used as a proxy when no tag is present.
- Pronoun blocklist (active):
  - The following are never promoted to `character_name`: He, She, They, We, I, You, It, Him, Her, Them, Us, Me.
  - Rationale: Avoids false attributions such as character_name="He" when parsing dialogue tags or proximity.

## Confidence Scoring (Deterministic)

- Enabled via `use_deterministic_confidence`.
- Signals: dialogue_tag, proper_noun_proximity, continuity_prev_same (reserved), adjacent_narration_present.
- Mapping: logistic with clamp, default bounds \[0.35, 0.95\]. Evidence is emitted at `attribution.evidence.confidence`.
- Unknown or non-dialogue:
  - Falls back to base/unknown constants; narration can use `narration_confidence` or evidence if enabled.

## Orchestrator Wiring

`ABMArtifactOrchestrator` exposes and forwards these attribution knobs:

- use_deterministic_confidence
- search_radius_spans
- narration_confidence
- use_narration_confidence_evidence

It also supports downstream filtering (e.g., `min_confidence_pct`) when used with span iteration/output stages.

Continuity (opt-in) is forwarded as well:

- enable_continuity_prev: bool (default false)
- continuity_max_distance_spans: number (default 2)

Usage example (one-touch):

```python
ABMArtifactOrchestrator(
  blocks_data=...,
  use_deterministic_confidence=True,
  search_radius_spans=4,
  enable_continuity_prev=True,
  continuity_max_distance_spans=2,
)
```

## Outputs

- `spans_attr.jsonl`: Dialogue/narration spans with `character_name`, `attribution.confidence`, and `attribution.evidence` (when enabled).
- Meta sidecars include component configuration for auditability.

## Quick Usage (LangFlow)

- Inline chain: Add `ABMSpanAttribution` and set the inputs above directly.
- One-touch: Use `ABMArtifactOrchestrator` and adjust the same knobs at the orchestrator level; it forwards to attribution.
- Optional viewer filtering: Set `min_confidence_pct` on the iterator/orchestrator UI to hide low-confidence dialogue during inspection.

## Conservative continuity_prev (available, opt-in)

- When no speaker is detected from narration context, attributes to the previous dialogue speaker if within a small window (`continuity_max_distance_spans`) and within the same block.
- Default is disabled; enable via `enable_continuity_prev=true` and tune the span window.
- Deterministic confidence integrates continuity distance into scoring when enabled.
