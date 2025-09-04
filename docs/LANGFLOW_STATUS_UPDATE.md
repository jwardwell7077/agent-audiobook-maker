# LangFlow Status Update (2025-08-30)

Ingestion and classification status (2025-08-30)

- WellDone -> JSONL ingestion: Verified working. JSONL now includes line_count, char_count, word_count, start_line, end_line per block.
- TOC parsing and chapter classification: Restored and validated. Now allows repeated chapter names; TOC entries = 700, chapters = 700 for MVS dataset.
- Artifacts are written by default under tmp/ for dev runs; production path remains under data/clean/mvs/ (git-ignored).

Next focus: Langflow wiring using the stable JSONL classifier outputs.
