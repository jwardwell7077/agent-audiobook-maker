# Config and environment

Environment variables
- Kokoro HTTP TTS
	- KOKORO_URL — Base URL of the Kokoro service (OpenAI-style /v1/audio/speech)
	- KOKORO_HTTP_POOL — Max HTTP connections to pool per host
	- KOKORO_TIMEOUT — Request timeout in seconds
- Piper
	- ABM_PIPER_BIN — Path to piper binary
	- ABM_PIPER_VOICES_DIR — Directory containing Piper voices
	- ABM_PIPER_DRYRUN — If set, skip actual synthesis for debugging
- XTTS
	- ABM_XTTS_MODEL — Model name or path
	- ABM_XTTS_DEVICE — Device string (e.g., cpu, cuda:0)
	- ABM_XTTS_DRYRUN — If set, skip actual synthesis
- LLM
	- OPENAI_API_KEY — Used by the OpenAI-compatible client
- Misc
	- ABM_DEBUG_PAUSES — If set, export detailed pause timing during render

Config files and patterns
- Rendering/manifests
	- book_manifest.json — Book-level metadata for packaging
	- ch_*.synth.json — Chapter synthesis manifests
	- synth_manifest.json — Aggregate synthesis manifest (export)
- Ingestion
	- _ingest_meta.json, _meta.json — Artifacts written during ingest
- Profiles and casting
	- casting_proposed.yaml — Proposed per-speaker casting
	- casting_summary.json — Casting stats/summary
	- voices-dir contents — Piper .onnx.json voice configs
- Adapters and engines
	- .onnx.json — Piper model config sidecars
	- .qc.json — QC report sidecars for renders

Notes
- Some tools emit sidecar JSON files (e.g., .qc.json) alongside audio artifacts.
- Paths shown here reflect the default layout under data/ and tmp/ used by scripts in this repo.
