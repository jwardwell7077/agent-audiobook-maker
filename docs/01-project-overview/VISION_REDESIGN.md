# Vision — Spans-First Audiobook Maker (Parler + Piper)

Purpose

- Build a local-first, deterministic audiobook pipeline where casting and confidence come before TTS. Characters are distinct and consistent; narration is clear and neutral. Quality is measured, recoverable, and improvable.

Guiding principles

- Spans-first: classify, attribute, and cast spans before any SSML/render seams.
- Deterministic artifacts: JSON/JSONL with sidecar meta; stable IDs; reproducible runs.
- Human-in-the-loop: per-chapter, human-triggered processing with clear warnings and costs before any cloud calls.
- Quality gates: confidence >= thresholds; retry loops are bounded and observable.
- Local-first: Piper + Parler on GPU; local LLM for retries; cloud only when explicitly confirmed.

Narration and dialogue

- Narrator + AI-system: Piper (en_US-lessac-high, 22.05 kHz, fp16 on RTX 4070). Neutral clarity.
- Characters/dialogue: Parler-TTS (mini v1). Per-character style prompts (emotion, age, pace, tone, accent, energy). Distinguishably different voices appropriate to character.

Confidence and recovery

- Span-level scores: speaker_id_conf, style_match_conf, type_conf. Aggregate C_span = min(...).
- Default threshold: 0.90 per span; configurable via TOML.
- Retry loop: if below threshold, run local LLM (Llama 3.1 8B Q5_K_M) with growing context window. If still below, LLM picks best guess; tag MANDATORY_REVIEW_LLM; warn; enqueue for cloud review.
- Cloud review: ChatGPT5 best-guess + rationale only after user approves an estimated cost. Never auto-send.

Casting and the Character Bible

- Living knowledge base built during processing:
  - characters[name]: aliases, style_prompt, voice_route="parler", voice_id?, examples [span_ids], first_seen_chapter, confidence_stats
  - chapter_index[chapter]: list of character mentions
  - evidence[span_id]: text, local_scores, llm_rationale?, cloud_rationale?
- Policy: no "unknown" at output time — use best guess; low-confidence spans flagged MANDATORY_REVIEW_LLM with warnings.
- Persistence: global `data/clean/{book}/character_bible.json` and per-chapter snapshot under the chapter artifacts.

Agents (CrewAI)

- IngestionAgent -> SpanClassifierAgent -> SpeakerAttributionAgent -> CastingAgent -> StylePlannerAgent ->
  ConfidenceQAAgent -> LLMReprocessAgent -> TTSOrchestratorAgent (route Piper/Parler) -> AudioCombinerAgent -> ScoreSamplerAgent.
- State persisted as JSON/JSONL; resumable; human-triggered per chapter.

Artifacts (high level)

- spans.jsonl -> spans_cls.jsonl -> spans_attr.jsonl -> spans_cast.jsonl -> spans_style.jsonl (optional) + *.meta.json
- Per-span MP3 stems: `data/stems/{book}/{chapter}/{speaker}/{span_id}.mp3`
- Per-chapter MP3 render: `data/renders/{book}/{chapter}.mp3`
- Character bible: global + chapter snapshots.

Roadmap (post-MVP)

- WAV stems and mastering; SSML planning; better style transfer; multilingual; DB persistence + LangGraph/DAG; evaluation dashboards.

## Audience & Differentiators

Who this is for

- Primary: Fiction authors and small publishers who want local, repeatable audiobook production.
- Secondary: Developers and researchers exploring spans-first, deterministic multi-agent systems.

Why this approach

- Local-first: privacy by default; no content leaves the machine without explicit approval.
- Deterministic & reproducible: content-addressed artifacts; stable IDs; easy regression testing.
- Spans-first multi-agent: specialized agents (classification → attribution → casting) before any TTS, improving consistency and QA.

## Success criteria (initial)

- Per-span confidence ≥ 0.90 (configurable); low-confidence spans tagged MANDATORY_REVIEW_LLM with clear warnings.
- Per-chapter runs complete without manual retries using local-only paths by default (bounded local LLM retries allowed).
- Clearly distinct character voices (Parler-TTS) and clear, neutral narration (Piper); consistent across a chapter.
- Reproducible outputs: identical hashes for identical inputs and params; deterministic JSON/JSONL + meta artifacts.
