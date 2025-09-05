# Spans‑First Flow with Deterministic Confidence

This flow demonstrates the upstream spans‑first pipeline with deterministic confidence and a viewer threshold.

- Template: `tools/spans_first_confidence.flow.json`
- Components:
  - Block Schema Validator → Mixed Block Resolver → Span Classifier → Span Attribution (use_deterministic_confidence=true) → Span Iterator (dialogue_only=true, min_confidence_pct=75)

## Run it in LangFlow

1. Start LangFlow with your workspace mounted (example):

```bash
python scripts/run_langflow.sh
```

1. Import the flow JSON (`tools/spans_first_confidence.flow.json`).

1. Provide `blocks_data` to the validator (from a loader node or a minimal payload), then run.

## Tuning

- Attribution confidence

  - Toggle: `use_deterministic_confidence` (default: true)
  - Baselines: `base_confidence` (dialogue), `narration_confidence` (narration)

- Iterator filtering

  - `dialogue_only` to only show dialogue spans
  - `min_confidence_pct` to hide low‑confidence dialogue (e.g., 75)

## Notes

- The scorer is deterministic and explainable. Evidence appears under `attribution.evidence.confidence`.
- Orchestrator also supports a `min_confidence_pct` for chapter‑level filtering if you use it instead of the raw chain.

## Example: search_radius_spans impact

- Scenario: A dialogue span lacks an explicit “said NAME” tag; the nearest proper noun appears two narration spans away.
  - `search_radius_spans = 2` → detection: `proper_noun_proximity`, confidence ≈ 0.62 (bounded and explainable)
  - `search_radius_spans = 6` → detection still possible, but you may pick up unrelated names if the window is too wide. Prefer small windows (3–4) unless text is sparse.
- Tip: If you increase the radius, keep `min_confidence_pct` slightly higher during review to avoid low-signal attributions surfacing in the UI.

See also: `SPEAKER_ATTRIBUTION_DETERMINISTIC.md` for attribution knobs, the pronoun blocklist, and orchestrator wiring.

## Try it: quick radius comparison (optional)

Run this locally to compare confidences with different `search_radius_spans` values on your existing `output/mvs/ch01/spans_cls.jsonl`.

```bash
python - <<'PY'
import json, sys
sys.path.insert(0, 'src')
from abm.lf_components.audiobook.abm_span_attribution import ABMSpanAttribution

def load_spans(path):
    spans=[]
    for line in open(path, 'r', encoding='utf-8'):
        line=line.strip()
        if not line: continue
        spans.append(json.loads(line))
    return spans

spans_cls = load_spans('output/mvs/ch01/spans_cls.jsonl')

def run(radius):
    comp = ABMSpanAttribution(
        spans_cls={'spans_cls': spans_cls},
        write_to_disk=False,
        use_deterministic_confidence=True,
        search_radius_spans=radius,
        narration_confidence=0.95,
        use_narration_confidence_evidence=False,
    )
    return comp.attribute_spans().data['spans_attr']

res2 = run(2)
res6 = run(6)

# Compare first 10 dialogue spans that have a confidence value
pairs = []
for a,b in zip(res2, res6):
    if (a.get('type') or a.get('role') or '').lower()!='dialogue':
        continue
    ca = (a.get('attribution') or {}).get('confidence')
    cb = (b.get('attribution') or {}).get('confidence')
    if ca is None or cb is None:
        continue
    pairs.append({
        'block_id': a.get('block_id'),
        'segment_id': a.get('segment_id'),
        'name_r2': a.get('character_name'),
        'name_r6': b.get('character_name'),
        'conf_r2': round(ca, 3),
        'conf_r6': round(cb, 3),
    })
    if len(pairs)>=10:
        break

print(json.dumps(pairs, indent=2))
PY
```
