# New Piper Model Onboarding

This short checklist helps you install, audition, and integrate a new Piper voice/model.

## 1) Install the model
- Preferred: use our helper scripts to download to the standard voices dir
  - scripts/install_piper_voice.sh <voice-id>
  - Or place the .onnx and matching .json/.onnx.json under one of:
    - $ABM_PIPER_VOICES_DIR/<voice-id>/<voice-id>.onnx
    - ~/.local/share/piper/voices/<voice-id>/<voice-id>.onnx
    - /usr/local/share/piper/voices/<voice-id>/<voice-id>.onnx
    - /usr/share/piper/voices/<voice-id>/<voice-id>.onnx

## 2) Audition quickly
- Run the audition helper to generate a small pack of sample WAVs:
  - ./scripts/audition_piper_model.py <voice-id>
  - Or pass a direct model path: ./scripts/audition_piper_model.py /path/to/model.onnx
  - Outputs go to data/voices/auditions/<voice>-<timestamp>/
  - Set ABM_PIPER_BIN if piper is not on PATH

## 3) Update casting (optional)
- If you decide to use this model for a character, update your casting profile or the script builder that assigns engine/voice to spans.

## 4) Cache considerations
- Our Piper adapter embeds a version string (currently "piper-adapter-2") used by the TTS cache.
- Changing models/voices automatically changes the cache key because TTSTask.voice differs.
- If you modify the adapter CLI invocation or audio normalization, bump the adapter version to invalidate stale cache entries.

## 5) Smoke test a chapter
- Use scripts/render_book_from_annotations.py with a small chapters subset and your chosen voice assignments.
- Example flags you might tune: --workers, --engine-workers, --crossfade, --lufs, --peak.

## 6) Normalize and package
- Run scripts/album_normalize_and_package.py to produce album-normalized WAVs, MP3/Opus, and optionally M4B with chapter markers.

## 7) QC
- Run scripts/qc_grade.py to summarize ACX-style checks (LUFS/peak/noise approximations) and see pass/fail.

Tips:
- For CI or quick checks without Piper installed, use ABM_PIPER_DRYRUN=1; the adapter writes short silence WAVs so the pipeline can run.
- Keep data/ and large artifacts out of git; see .gitignore. Commit only code/docs/config changes.
