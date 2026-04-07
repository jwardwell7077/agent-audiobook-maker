# CLI reference

This page lists the primary command-line entry points, grouped by area, with a short description. Flags below are intentionally minimal; consult --help in each command for full details.

Audio rendering
- Render a whole book: python -m abm.audio.render_book
	- Key flags: --scripts-dir, --out-dir, --engine-workers, --resume, --show-progress, --log-level
- Render a single chapter: python -m abm.audio.render_chapter
	- Key flags: --script, --profiles, --out-dir, --tmp-dir, --lufs, --peak, --crossfade-ms, --engine-workers, --workers, --save-master-wav, --save-mp3
- Export synthesis tasks (plans): python -m abm.audio.synthesis_export
	- Key flags: --tagged, --profiles, --only, --out-dir, --default-engine, --default-pause

Ingestion
- End-to-end PDF ingest pipeline: python -m abm.ingestion.ingest_pdf
	- Key flags: --out-dir, --mode, --preserve-form-feeds, --no-reflow, --no-dehyphenate, --no-dedupe-spaces, --no-strip-trailing, --insert-pg
- Extract raw text from PDF: python -m abm.ingestion.pdf_to_raw_text
	- Key flags: --newline, --preserve-form-feeds, --no-strip-trailing-spaces, --dedupe-inline-spaces, --fix-short-wraps, --artifact-compat
- Convert WellDone format to JSONL: python -m abm.ingestion.welldone_to_json
	- Key flags: --out-dir

Annotation and LLM refinement
- Multi-stage annotation runner: python -m abm.annotate.annotate_cli
	- Key flags: --in, --out-json, --out-md, --out-dir, --metrics-jsonl, --stages, --spacy-model, --coref/--no-coref, --mode, --llm
- Prepare LLM candidates: python -m abm.annotate.llm_prep_cli
	- Key flags: --in, --out, --conf-threshold
- Refine with LLM voting: python -m abm.annotate.llm_refine
	- Key flags: --tagged, --out-json, --out-md, --endpoint, --model, --manage-llm, --skip-threshold, --votes, --cache, --metrics-jsonl, --max-concurrency

Profiles and casting
- Build/validate profiles and propose voices: python -m abm.profiles.profiles_cli
	- Key flags: --profiles, --annotations, --prefer-engine, --out, --engine, --voices-dir, --n-top
- Resolve aliases from refined annotations: python -m abm.profiles.alias_cli
	- Key flags: --annotations, --profiles, --out-dir, --tau-auto, --tau-review, --use-llm, --model, --proposals
- Piper utilities
	- Catalog local voices: python -m abm.voice.piper_catalog (flags: --voices-dir, --json)
	- Cast sampling lines: python -m abm.voice.piper_casting (flags: --profiles, --annotations, --out, --engine, --max-chars)

Audit and QC
- Generate annotation evaluation reports: python -m abm.audit.cli
	- Key flags: --refined, --base, --metrics-jsonl, --chapters, --plots, --html, --out-dir, --title, --stdout-summary

More
- Use --help with any module for full flag descriptions: e.g., python -m abm.audio.render_chapter --help
