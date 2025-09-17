# Voice timing: pauses and padding

This guide explains how per‑segment pauses are handled in the Parler pipeline, how to post‑process plans to add contextual padding, and how to render and verify the result.

## What changed

- The chapter renderer `abm.voice.render_chapter` now honors per‑segment `pause_ms` values in the plan.
- You can also add a global extra pause via `--add-pause-ms` at render time.
- When a pause is present after a segment, the renderer inserts digital silence and disables crossfade for that join. When no pause is present, an equal‑power crossfade is used.
- Each clip gets a short micro‑fade in/out to avoid clicks.

Outputs include a WAV and a QC JSON with duration, LUFS, peak, and utterance metadata.

## Components and files

- Plan builder (inputs → plan JSON): `abm.voice.plan_from_annotations`
- Contextual pause post‑processor: `scripts/post_process_plan_padding.py`
- Renderer (plan → WAV + QC): `abm.voice.render_chapter`
- Crossfade/micro‑fade utilities: `src/abm/audio/concat.py`

## Quick start

1) Generate a plan (prefer Parler)

```bash
# From repo root
export PYTHONPATH=src
python -m abm.voice.plan_from_annotations \
  --in data/ann/mvs/combined_refined.json \
  --cast data/voices/mvs_parler_profiles.yaml \
  --out-dir data/ann/mvs/plans \
  --sr 48000 \
  --crossfade-ms 40 \
  --pause-narr 240 --pause-dialog 160 --pause-thought 220 \
  --prefer-engine parler --verbose
```

2) Add contextual padding (choose strength)

```bash
# Moderate padding example
python -m scripts.post_process_plan_padding \
  --in  data/ann/mvs/plans/ch_0001.json \
  --out data/ann/mvs/plans/ch_0001_padded.json

# Heavy padding example (larger bonuses, cap, and global add)
python -m scripts.post_process_plan_padding \
  --in  data/ann/mvs/plans/ch_0001.json \
  --out data/ann/mvs/plans/ch_0001_heavy.json \
  --scale 2.0 --cap-ms 800 \
  --hardstop-ms 320 --comma-ms 200 --speaker-ms 260 --kind-ms 220 --paragraph-ms 400 \
  --add-ms 220 --min-ms 0
```

Available flags (summary):
- `--hardstop-ms`, `--comma-ms`, `--speaker-ms`, `--kind-ms`, `--paragraph-ms`
- `--scale` multiplies computed bonuses
- `--add-ms` adds a uniform extra pause to all segments
- `--min-ms` enforces a minimum pause
- `--cap-ms` caps the final pause per segment

3) Render the chapter

```bash
# Baseline (no extra add at renderer level)
PYTHONPATH=src ABM_DEBUG_PAUSES=1 \
python -m abm.voice.render_chapter \
  --chapter-plan data/ann/mvs/plans/ch_0001_padded.json \
  --cache-dir   data/ann/mvs/tts_cache \
  --tmp-dir     data/tmp \
  --out-wav     data/renders/mvs/ch_0001.wav \
  --prefer-engine parler \
  --parler-model parler-tts/parler-tts-mini-v1 \
  --parler-seed 31337 \
  --force

# Heavy variant (additional renderer-level spacing)
PYTHONPATH=src ABM_DEBUG_PAUSES=1 \
python -m abm.voice.render_chapter \
  --chapter-plan data/ann/mvs/plans/ch_0001_heavy.json \
  --cache-dir   data/ann/mvs/tts_cache \
  --tmp-dir     data/tmp \
  --out-wav     data/renders/mvs/ch_0001_heavy.wav \
  --prefer-engine parler \
  --parler-model parler-tts/parler-tts-mini-v1 \
  --parler-seed 31337 \
  --add-pause-ms 120 \
  --force
```

Notes:
- Setting `ABM_DEBUG_PAUSES=1` prints a summary line like: `[render_chapter] segments=93 total_pause_ms=96220`.
- `--parler-seed` makes synthesis deterministic; seeds from the plan are still respected per segment when present.
- The renderer writes `<out-wav>` and `<out-wav>.qc.json` (duration, LUFS, peak, engines, utterances).

## Verifying duration

You can quickly check durations with `sox` or Python:

```bash
# sox
sox --i -D data/renders/mvs/ch_0001.wav
sox --i -D data/renders/mvs/ch_0001_heavy.wav
```

```bash
# Python
PYTHONPATH=src python - <<'PY'
import soundfile as sf
from abm.audio.qc import duration_s
import sys
p=sys.argv[1] if len(sys.argv)>1 else 'data/renders/mvs/ch_0001_heavy.wav'
y,sr=sf.read(p, dtype='float32')
print('duration_s', duration_s(y,sr))
PY
```

## How pauses and crossfades interact

- If `pause_ms` after a segment is greater than zero, that amount of digital silence is inserted and the join to the next segment is a butt‑join (no crossfade).
- If `pause_ms` is zero, an equal‑power crossfade is applied using `crossfade_ms` from the plan.
- Micro‑fades are applied to each clip to avoid clicks at boundaries.

## Caching and performance

- TTS outputs are cached by a content hash. For Parler, the cache key includes `description_sha` and `seed`.
- Changing text, voice, description, seed, or Parler model will invalidate the cache.
- Sample rate defaults to 48 kHz.

## Troubleshooting

- Duration didn’t change after increasing pauses:
  - Ensure you’re running the workspace renderer: `export PYTHONPATH=src`.
  - Use `--force` to overwrite outputs.
  - Set `ABM_DEBUG_PAUSES=1` to see total planned pauses at render time.
- “ModuleNotFoundError: abm”: ensure `PYTHONPATH=src` is set in your shell.
- GPU/CUDA noise on import is expected with some stacks; not required for correctness here.

## Related files

- `src/abm/voice/render_chapter.py` — plan-based renderer honoring `pause_ms`
- `scripts/post_process_plan_padding.py` — contextual padding CLI
- `src/abm/audio/concat.py` — equal‑power crossfade and micro‑fade helpers
- `src/abm/voice/plan_from_annotations.py` — plan creation with base pause defaults
