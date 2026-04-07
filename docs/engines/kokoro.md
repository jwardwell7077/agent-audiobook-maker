# Kokoro TTS pipeline — current workflow

This document captures the current state of the Kokoro section of the audio pipeline: how to generate Kokoro-compatible plans and render chapters using the Kokoro HTTP engine.

> Scope: documentation only. This does not change code. A broader redesign of voice plan generation is tracked separately.

---

## Prerequisites

- Kokoro server running (FastAPI, OpenAI-compatible speech endpoint)
	- Default URL used by the code: `http://127.0.0.1:8880` (can override with `KOKORO_URL`)
	- Endpoint expected: `POST /v1/audio/speech` returning either WAV bytes or JSON with base64 audio
- Environment variables (common):
	- `KOKORO_URL` — Base URL (e.g., `http://127.0.0.1:8889`)
	- `KOKORO_HTTP_POOL` — HTTP connection pool size (default 32; 64–128 for heavy parallelism)
	- `KOKORO_TIMEOUT` — Request timeout seconds (default 90)

Optional runtime notes:
- Rendering can be multi-threaded. The bulk renderer sets `--workers` and uses an internal per-engine worker map.
- Audio is decoded to float32 arrays; mastering and crossfades run after synthesis.

---

## Generate Kokoro plans

There are two supported paths.

### 1) Direct from annotations (preferred)

Use `scripts/make_kokoro_plans_from_annotations.py` to create chapter plans that already target `engine: "kokoro"` with a valid Kokoro `voice_id`.

- Inputs: annotation chapter JSONs (e.g., `data/ann/mvs/combined_refined.json`)
- Outputs: chapter plan files (e.g., `tmp/data/ann/mvs/plans/ch_0001.json`)
- Voice mapping helpers:
	- A project-local mapping file (e.g., `data/voices/kokoro_characters.json`) for character -> kokoro voice_id
	- Fallback heuristic for voice ids matching `^[ab][fm]_[a-z]+$` (e.g., `af_bella`, `am_michael`)

Example:

```bash
python scripts/make_kokoro_plans_from_annotations.py \
	--out-dir tmp/data/ann/mvs/plans
```

Resulting plan segments contain:
- `engine: "kokoro"`
- `voice_id: "af_*" | "am_*" | "bf_*" | "bm_*"` (Kokoro voice)
- Text, timing, and pause metadata as usual

### 2) Convert legacy plans

If you have legacy (e.g., Parler) plans, convert them to Kokoro-compatible form.

```bash
python scripts/convert_plans_to_kokoro.py \
	--out-dir tmp/data/ann/mvs/plans
```

This attempts to map existing character/voice references to a Kokoro `voice_id` using:
- A project-local mapping file (e.g., `data/voices/kokoro_characters.json`) with explicit character: voice_id lines
- Optional profiles override file (e.g., `data/voices/profiles.kokoro.yml`)
- Heuristic voice-id detection regex when explicit mapping is not available

---

## Render chapters with Kokoro

### A) Bulk rendering (recommended)

Use `scripts/bulk_render_kokoro.py` to render many chapters with resume, retries, and logging.

Environment (example):

```bash
export KOKORO_URL=http://127.0.0.1:8889
export KOKORO_HTTP_POOL=64
```

Run:

```bash
python -u scripts/bulk_render_kokoro.py \
	--resume \
	--workers 16 \
	--prefer-engine kokoro \
	--continue-on-error \
	--verbose
```

Behavior:
- Defaults per-engine workers: `{ "kokoro": 2 }` unless overridden
- Retries/backoff on transient HTTP errors
- Robust decode of WAV or JSON base64 responses
- Writes logs to `logs/render/` when run with nohup or a wrapper

### B) Single chapter (direct)

Use the existing chapter renderer with Kokoro preferences.

```bash
python -m abm.voice.render_chapter \
	--chapter-plan tmp/data/ann/mvs/plans/ch_0001.json \
	--cache-dir data/ann/mvs/tts_cache \
	--out-wav data/renders/mvs/ch_0001.wav \
	--engine-workers kokoro=2 \
	--prefer-engine kokoro \
	--status rich \
	--verbose
```

---

## Caching and determinism

- The TTS cache key includes engine, voice, text, and other synthesis parameters; changing these invalidates cache entries.
- Kokoro synthesis itself is deterministic for the same inputs (voice + text) at the engine layer; any upstream randomness should be controlled at plan generation time.

---

## Environment variables (reference)

- `KOKORO_URL` — Base URL for the Kokoro server; default `http://127.0.0.1:8880`
- `KOKORO_HTTP_POOL` — HTTP connection pool size; default `32`
- `KOKORO_TIMEOUT` — Request timeout in seconds; default `90`

---

## Troubleshooting

- Empty audio / decode failed
	- Check server health and logs. Ensure `/v1/audio/speech` is reachable.
	- Increase `KOKORO_TIMEOUT` for long inputs; reduce concurrency if server is saturated.
	- Validate that plans have `engine: "kokoro"` and non-empty `voice_id`.

- Silent/very short output
	- Inspect input text for excessive whitespace or placeholders.
	- Verify voice_id exists on the Kokoro server.

- Throughput is low
	- Increase `KOKORO_HTTP_POOL` (e.g., 64–128) and `--workers` cautiously.
	- Ensure the Kokoro server has GPU/CPU resources and batching enabled if applicable.

---

## Pipelines alignment (optional)

If your project has existing Parler-focused scripts or pipelines, add parallel Kokoro entries:

- `plan_kokoro`: generate plans into `tmp/data/ann/<book>/plans` using `scripts/make_kokoro_plans_from_annotations.py`
- `render_kokoro_ch1`: render `tmp/data/ann/<book>/plans/ch_0001.json` with `--prefer-engine kokoro` and `--engine-workers kokoro=2`

These are documentation suggestions only; adopt when ready to shift defaults or provide alternatives alongside Parler.
