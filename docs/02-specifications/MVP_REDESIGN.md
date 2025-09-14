# MVP — Parler (Characters) + Piper (Narrator), Confidence ≥ 0.90

Scope

- Input: structured TOC PDF (private/local-only). One narrator, multiple distinct character voices.
- Process: spans-first classification → speaker attribution → casting → confidence QA → local LLM retry loop → TTS (route Piper/Parler) → combine per chapter.
- Execution: per-chapter, human-triggered via Make; no automatic cloud calls.

Models and runtime (RTX 4070)

- Narrator/system: Piper `en_US-lessac-high`, 22.05 kHz, fp16 CUDA (length_scale≈1.1, noise_scale≈0.33, noise_w≈0.8).
- Characters: Parler-TTS `parler-tts-mini-v1`; seeded style archetypes (young-energetic, middle-aged-neutral, elder-calm, gruff, playful, formal, sarcastic-dry, anxious-quick).
- Local LLM: Llama 3.1 8B Instruct (Q5_K_M), 8k context, temperature 0.3, top_p 0.9.
- Cloud LLM (mandatory review queue): ChatGPT5, only after user confirms estimated cost.

Confidence rubric and retry

- Span scores: speaker_id_conf, style_match_conf, type_conf; C_span = min(...).
- Thresholds: default 0.90 per span (TOML-configurable). self_conf_exit=0.90; max_passes=3; ctx_window=5; expand_step=5.
- If C_span < threshold: interim outputs may carry `speaker: null/"Unknown"` prior to retries. Run local LLM with chapter lookup context. After retries, replace Unknown with the best guess; if still < threshold, tag `MANDATORY_REVIEW_LLM`, add warning, and enqueue for optional cloud review.

Artifacts

- JSONL/meta per stage: `spans*.jsonl` + `*.meta.json`. Early stage files may contain `Unknown` for dialogue spans prior to LLM retries; final post-retry artifacts must not.
- Character bible: `data/clean/<book>/character_bible.json` + per-chapter snapshot.
- Per-span MP3 stems (22.05 kHz, 128 kbps, mono, -16 LUFS, -1 dBFS peak).
- Per-chapter MP3 (22.05 kHz, 192 kbps), normalized, brief crossfades for same-speaker seams.

Acceptance criteria

- English. 5 chapters rendered end-to-end.
- After local retries and any approved cloud assists, dialogue spans: median C_span ≥ 0.90, p90 ≥ 0.85; narration type_conf ≥ 0.90.
- No "Unknown" in final post-retry outputs; low-confidence spans marked `MANDATORY_REVIEW_LLM` with warnings.
- External QA: stratified sample manifest produced for ChatGPT5 assessment (cost shown before sending).

Run surface

- `make render_chapter CH=1` — process one chapter.
- `make qa_sample_external` — build QA sample JSONL; show cost estimate; prompt to send to ChatGPT5.

Configuration (TOML overrides defaults)

- `[confidence] threshold=0.90, max_passes=3, ctx_window=5, expand_step=5, self_conf_exit=0.90`
- `[tts.piper] voice="en_US-lessac-high", noise_scale=0.33, noise_w=0.8, length_scale=1.1`
- `[tts.parler] model="parler-tts-mini-v1"`
- `[audio] sr=22050, span_bitrate_kbps=128, chapter_bitrate_kbps=192, lufs=-16, peak_dbfs=-1.0`
- `[llm.local] model="llama3.1-8b-q5_k_m", temperature=0.3, top_p=0.9`
- `[llm.cloud] provider="openai", model="gpt-5", daily_budget_usd, per_run_cap_usd`
- `[paths] data_root="data", output_root="data"`
- `[casting] min_evidence_for_merge=2`

Notes

- Private content remains local; directories are `.gitignore`d. No copyrighted text/audio is committed.

## Diagram

See the spans-first MVP pipeline diagram:

- docs/04-diagrams/architecture/mvp_spans_first.mmd
