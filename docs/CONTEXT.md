# Auto‑Audiobook Maker – Architecture & Dev Machine Context

Last updated: 2025‑08‑11

## Executive Summary

Local‑first, reproducible pipeline to transform long PDFs into a mastered, multi‑voice audiobook. The system ingests, annotates, casts, renders, and masters chapters in parallel, prioritizing CPU for NLP and reserving GPU for TTS. It is orchestrated and observable with Dagster, with MLflow for experiment/config/artifact tracking. Idempotency is enforced via content hashes and cached per‑chapter artifacts in Postgres (JSONB) and the filesystem.

---

## Developer Machine & Runtime Constraints

- OS: Windows 11 + WSL2 (Ubuntu). Keep hot loops and project files strictly on the WSL ext4 filesystem.
- GPU: NVIDIA GeForce RTX 4070 (CUDA). Single‑GPU, shared with desktop; reserve TTS for GPU.
- CPU/RAM: AMD Ryzen 7 3700X (8‑core), 32 GB RAM.
- Storage: Samsung SSD 990 Pro 4TB. High IOPS; large working set OK.
- Containerization: Docker Desktop (WSL2 backend) with GPU support enabled.
- Tooling: Python 3.12, Ollama, LangChain/LangGraph, FFmpeg, AI dev tools.
- Models (local‑first defaults):
  - LLM Judge: Llama 3.1 8B Q4_K_M via Ollama.
  - Coref: Local Hugging Face coreference model (distil‑/base‑size) CPU.
  - Emotion/Prosody: Distil‑size classifier + rules (CPU).
  - TTS: XTTS v2 (CUDA) primary; Piper (CPU) fallback.

---

## High‑Level Architecture

Pipeline stages (per chapter):

1) Ingestion
   - Input: PDF(s)
   - Output: Clean chapter texts with stable IDs and content hashes.
   - Storage: Postgres (chapters table, JSONB payload) + files under `data/clean/`.

2) Annotation (LangGraph agents)
   - Segmentation → utterances
   - Coref resolution (HF local model)
   - Speaker attribution (heuristics + LLM judge via Ollama)
   - Emotion/prosody classification (classifier + rules)
   - QA Agent flags low confidence or inconsistencies
   - Output: per‑chapter JSONL with rich annotations under `data/annotations/` and in Postgres JSONB.

3) Casting & Voices
   - Build Character Bible; map speakers to XTTS v2/Coqui profiles.
   - Output: character profiles and TTS settings under `data/casting/` and Postgres tables.

4) Rendering
   - Transform annotated JSONL → SSML → TTS → stems → stitched chapter → mastered audiobook chapter.
   - EBU R128 loudness target; normalization and dynamics per chapter; final book assembly.
   - Output: stems under `data/stems/`, chapter WAV/FLAC/MP3 under `data/renders/`.

5) Orchestration & Observability
   - Dagster: jobs, sensors, schedules, retries, caching, lineage.
   - MLflow: params, metrics, artifacts, model/config versioning.

Concurrency model

- CPU workers: 4–6 for NLP stages; I/O bound tasks async.
- GPU workers: 1–2 for TTS; queue to avoid GPU thrash.
- Chapter parallelism dominant; serialize within chapter for speaker/voice consistency when needed.

Idempotency & caching

- Hash inputs (text SHA‑256 + params hash) to skip recompute.
- Store stage status per chapter with artifact URIs; resume on failure.

---

## Data Flow & Artifacts (per chapter)

- Ingestion: `data/clean/{book_id}/{chapter_id}.json` (text, structure, text_sha256)
- Annotation: `data/annotations/{book_id}/{chapter_id}.jsonl`
- SSML: `data/ssml/{book_id}/{chapter_id}.ssml`
- Stems: `data/stems/{book_id}/{chapter_id}/{utterance_idx}.wav`
- Chapter render: `data/renders/{book_id}/{chapter_id}.wav`
- Book master: `data/renders/{book_id}/book_master.wav`

---

## JSONL Annotation Record (canonical)

One JSON object per utterance (lines delimited):

```json
{
  "book_id": "...",
  "chapter_id": "...",
  "utterance_idx": 0,
  "text": "...",
  "start_char": 123,
  "end_char": 456,
  "speaker": "NARRATOR|CHARACTER_NAME|UNKNOWN",
  "speaker_confidence": 0.0,
  "coref_cluster_id": "c12",
  "emotion": "neutral|happy|sad|angry|fear|surprise|disgust|other",
  "prosody": { "pitch": "mid", "rate": "medium", "intensity": "normal" },
  "llm_judge": { "model": "llama3.1:8b-q4_k_m", "rationale": "...", "confidence": 0.0 },
  "qa_flags": ["low_confidence_speaker", "inconsistent_emotion"],
  "tts_profile_id": "xtts_v2:char_anna",
  "ssml": "<speak>...</speak>",
  "audio_stem_path": "data/stems/.../000.wav",
  "duration_s": 1.23,
  "hashes": { "text_sha256": "...", "params_sha256": "..." },
  "status": "new|annotated|rendered|staged|failed",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

## Database Model (Postgres, JSONB‑centric)

- books(id PK, title, author, meta JSONB)
- chapters(id PK, book_id FK, index INT, title, text_sha256, payload JSONB, status, created_at, updated_at)
- annotations(id PK, book_id, chapter_id, version, records JSONB, stats JSONB, text_sha256, params_sha256, status)
- characters(id PK, book_id, name, aliases JSONB, profile JSONB)
- tts_profiles(id PK, character_id FK, engine, settings JSONB)
- stems(id PK, book_id, chapter_id, utterance_idx, path, duration_s, tts_profile_id, hashes JSONB, status)
- renders(id PK, book_id, chapter_id, path, loudness_lufs, peak_dbfs, duration_s, hashes JSONB, status)
- jobs(id PK, type, book_id, chapter_id, stage, params JSONB, status, started_at, finished_at, logs_ptr)
- metrics(id PK, scope, key, value, timestamp)
- Optional: pgvector table for embeddings on utterances.

Indexes: (book_id, chapter_id), GIN on JSONB paths used in filters, BTREE on hashes.

---

## Component Responsibilities

- Ingestion service
  - PDF parsing, chapterization, normalization, hashing.
  - Write chapters to Postgres and `data/clean/`.
- Annotation service (LangGraph)
  - IMPLEMENTED: skeleton graph (`segment`, `coref`, `speakers`, `emotion`, `qa`).
  - Flags now stored directly in `State` (reliable across invocation); removed deprecated `config_schema` usage.
  - Added synchronous execution helper `run_annotation_for_chapter` with caching via (text_sha256, params_hash, graph_version).
  - Persists JSONL under `data/annotations/` and a DB row (records + stats).
  - Planned: real coref model, LLM speaker disambiguation, richer emotion classifier, QA expansions.
- Casting service
  - IMPLEMENTED (prototype): `derive_characters` extracts distinct speakers; `persist_characters` stores them.
  - Planned: merge aliases, frequency stats, voice selection metadata.
- Rendering service
  - IMPLEMENTED (prototype): SSML stub builder (`build_ssml`) + Piper TTS stub to write fake stem files.
  - Planned: real Piper / XTTS integration, stitching, loudness normalization (pyloudnorm), render persistence rows.
- API (FastAPI)
  - Endpoints: /ingest, /books, /books/{id}/chapters, /chapters/{book}/{chapter}/annotations (compute or fetch cached annotation).
  - Planned: character listing, SSML & audio artifact download.
- Orchestrator (Dagster)
  - Assets: `chapters_clean`, `chapter_annotations`, `chapter_renders` (prototype casting→ssml→stems pipeline).
  - Planned: per‑chapter partitions + sensors, failure retries, job queue integration.
- Tracking (MLflow)
  - (Planned) Log configs, metrics (segment counts, latency), artifacts.

---

## Current Implementation Snapshot (2025-08-11)

- DB schema + initial migration applied; repository helpers for books & chapters.
- Ingestion endpoint (`/ingest`) persists chapters + JSON artifacts (simple splitter heuristic + PDF extraction with multi-backend detection).
- PDF extraction module with layered backends (PyPDF2, optional pdfminer, pdftotext CLI) + tests (skip if no backend).
- Annotation graph skeleton implemented with placeholder logic & idempotent segmentation.
- Flags stored in `State` (`enable_coref`, `enable_emotion`, `enable_qa`, `max_segments`).
- Annotation execution + persistence (`run_annotation_for_chapter`) writing JSONL + DB row with caching.
- Casting prototype: derive & persist character records from annotation speakers.
- SSML prototype: basic `<voice>` wrapping via `build_ssml`.
- TTS prototype: Piper stub writing JSON metadata instead of audio for stems.
- Dagster assets chain: `chapters_clean` → `chapter_annotations` → `chapter_renders`.
- API annotation endpoint computes or returns cached annotations; supports force + flag overrides.
- Tests cover graph behavior and PDF extraction; (TODO) add tests for casting/SSML/TTS stubs & caching idempotency.
- Pending next steps:
  1. Partitioned Dagster assets (per chapter) + sensor & retries.
  2. Real TTS (Piper or XTTS) producing audio; stem stitching + simple WAV render table entries.
  3. SSML enhancements (prosody tags, breaks) + per character voice mapping strategy.
  4. Character enrichment (frequency stats, alias grouping) & selection UI/API.
  5. MLflow integration (params, latency metrics, artifacts).
  6. Enhanced PDF chapterization heuristics & normalization.
  7. Annotation caching tests & failure retry semantics.
  8. Structured logging + metrics emission.
  9. Audio mastering (loudness normalization) pipeline step.

---

## Observability & Quality

- Dagster UI for pipeline visualization and asset lineage.
- Logging: (Planned) structured JSON logs per service; correlation IDs (book_id, chapter_id).
- Metrics: (Planned) per stage latency, GPU/CPU utilization; loudness stats; cache hit rates.
- QA: automatic flags for low speaker confidence or emotion inconsistencies; surfaces review sets.
- Evals: small gold set for speaker attribution/emotion; regression gates in CI.

---

## Concurrency & Resource Policy

- NLP workers: 4–6 CPU workers; respect 32 GB memory via bounded queues.
- TTS workers: 1–2 GPU workers; batch SSML by character where safe; back‑pressure via DB job queue.
- I/O: asynchronous FS/DB where possible; avoid cross‑boundary mounts to `C:\` during hot loops.

---

## Docker Compose Topology (conceptual)

- db (Postgres)
  - Volume: `postgres_data:/var/lib/postgresql/data`
  - Env: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- orchestrator (LangGraph workers; CPU)
  - Depends on `db`
- tts (XTTS v2; CUDA)
  - Runtime: `--gpus all`
  - Volume: project `data/`
- api (FastAPI; CPU)
  - Exposes REST endpoints for job control/status
- dagster-webserver + dagster-daemon
  - Mount code and `data/` for asset lineage
- mlflow (optional)
  - Backend store to Postgres or local SQLite; artifact root to `data/mlruns`

Shared volumes/directories

- `data/` (artifacts)
- `logs/`
- `models/` (optional local cache for HF/TTS)

---

## File/Folder Layout (target)

- `src/` – Python packages (agents, services, api, ops)
- `src/agent/` – LangGraph graphs and nodes
- `src/api/` – FastAPI app
- `src/pipeline/` – ingestion, annotation, rendering modules
- `src/tts/` – XTTS/Piper integration, SSML utils
- `src/ops/` – Dagster jobs/assets, MLflow hooks
- `configs/` – YAML/TOML config profiles
- `data/` – clean, annotations, ssml, stems, renders, cache, mlruns
- `tests/` – unit/integration/e2e
- `docs/` – this context, design notes, evals

---

## Reproducibility & Idempotency

- Pin Python and system deps in Dockerfiles; lock Python deps via `pyproject.toml` + lockfile.
- Content‑addressed caching by (text_sha256, params_sha256, graph_version).
- Deterministic seeds for models where applicable.
- All artifacts named with stable IDs and hashes; status transitions recorded in DB.

---

## Risks & Mitigations

- Long PDF variability → robust chapterization; manual overrides.
- Speaker attribution errors → LLM judge with explanations; QA agent triage.
- GPU contention → fixed TTS worker pool; job queue with rate limiting.
- Audio mastering consistency → EBU R128 compliance checks; loudness gates.
- Storage growth → prune intermediates; configurable retention of stems.

---

## Glossary

- JSONL: JSON Lines; one JSON object per line.
- SSML: Speech Synthesis Markup Language used to control TTS.
- EBU R128: Loudness normalization standard for broadcast consistency.
