# MVP Specification

MVP is defined in the redesign pack:

- `docs/02-specifications/MVP_REDESIGN.md` — scope, acceptance, models, confidence rubric, artifacts, run surface, config.
- `docs/01-project-overview/VISION_REDESIGN.md` — principles, engines, agent lineup, artifacts, roadmap.

Key points:

- Narrator (Piper en_US-lessac-high), Characters (Parler-TTS mini v1) on RTX 4070.
- Confidence per span with threshold 0.90; bounded local LLM retry loop; no “unknown”.
- Low-confidence spans tagged `MANDATORY_REVIEW_LLM`; cloud ChatGPT5 only after user approves cost.
- Artifacts: spans_* JSONL/meta; per-span MP3 stems; per-chapter MP3; character bible (global + chapter snapshots).

Use `make render_chapter CH=1` to run a chapter (once targets are wired on this branch).
