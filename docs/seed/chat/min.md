# Chat SME Seed (MIN)

Primer: ABM turns PDFs into chapterized JSON and multi‑voice audio locally (Piper/XTTS/Kokoro). Staged pipeline ensures debuggable artifacts and reproducibility.

Get the seed pack
- Local (in this repo): ../../seed_pack/latest/index.json and ../../seed_pack/latest/chat_min.zip
- Remote (GitHub raw, replace <YOUR_GH_USER>):
	- https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest/index.json
	- https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/chat_min.zip

Pipeline (Mermaid)

flowchart TD
	A[PDF]-->B[pdf_to_raw_text]; B-->C[raw_to_welldone]; C-->D[welldone_to_json]; D-->E[classifier_cli]; E-->F[voicecasting]; F-->G[render_chapter]; G-->H[album_norm]; H-->I[package_book]

Modules (top 10)
- abm.annotate — Span segmentation, roster building, LLM refinement helpers and CLIs.
- abm.audio — Rendering pipeline, mastering, packaging, engine adapters and orchestration.
- abm.audit — Metrics, plots, and markdown/HTML reporting for annotation audits.
- abm.classifier — Lightweight section classifier utilities and CLI.
- abm.ingestion — PDF to intermediate formats to JSONL.
- abm.llm — OpenAI-compatible client and local service manager.
- abm.parse — Document cache for SpaCy/processing.
- abm.profiles — Character profiles, alias resolution, and casting helpers.
- abm.sidecar — BookNLP adapter helpers.
- abm.voice — Engines (kokoro, piper, xtts), casting, and chapter render CLI.

CLIs (sample)
- python -m abm.annotate.annotate_cli
- python -m abm.annotate.bnlp_refine
- python -m abm.annotate.llm_prep_cli
- python -m abm.annotate.llm_refine
- python -m abm.audio.render_book
- python -m abm.audio.render_chapter
- python -m abm.audio.synthesis_export
- python -m abm.audit.__main__
