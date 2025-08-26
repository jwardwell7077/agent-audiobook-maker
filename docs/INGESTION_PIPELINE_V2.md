# Ingestion Pipeline v2 (dev/prod modes)

This document describes the updated PDF ingestion pipeline and its new runtime modes. It reflects changes made on the `langflow-multi-implement` branch and is intended for integration into the broader documentation on a follow-up branch.

## Overview

The ingestion pipeline orchestrates PDF → raw text → well‑done text → JSONL. It is implemented in `abm.ingestion.ingest_pdf` and composes:

- `pdf_to_raw_text.RawPdfTextExtractor` — minimal, fidelity-first extraction per page
- `raw_to_welldone.RawToWellDone` — reflow and cleanup while preserving paragraph blocks
- `welldone_to_json.WellDoneToJSONL` — converts well‑done text into block-per-line JSONL + immutable meta

Key improvements made in this version:

- Two explicit modes with clear responsibilities:
  - dev: write all artifacts (raw, well_done.txt, ingest meta, JSONL + JSONL meta) and stub a DB insert
  - prod: write no artifacts; only stub a DB insert (DB not ready yet)
- Deprecated the `--emit-jsonl` flag semantics; JSONL is produced in dev mode, and avoided in prod
- Removed direct Postgres insertion (PgInserter) from the pipeline for now; added a stub `_stub_db_insert` with a TODO

## Runtime modes

- dev mode (default)
  - Writes all artifacts to disk:
    - `<out_dir>/<stem>_raw.txt`
    - `<out_dir>/<stem>_well_done.txt`
    - `<out_dir>/<stem>_ingest_meta.json`
    - `<out_dir>/<stem>_well_done.jsonl`
    - `<out_dir>/<stem>_well_done_meta.json`
  - Also calls a DB insert stub (prints a "[DB STUB]" message)

- prod mode
  - Writes no artifacts
  - Only calls a DB insert stub using in-memory data (prints a "[DB STUB]" message)

Note: Actual DB insertion will be implemented later when the database is ready.

## CLI usage

From the repository root:

- dev mode (writes artifacts + DB stub):

```bash
python src/abm/ingestion/ingest_pdf.py LordoftheFlies.pdf --mode dev --out-dir data/clean/mvs
```

- prod mode (no artifacts; DB stub only):

```bash
python src/abm/ingestion/ingest_pdf.py LordoftheFlies.pdf --mode prod --out-dir data/clean/mvs
```

Arguments and flags:

- `input` (positional): path to the input PDF
- `--out-dir`: where artifacts would be written (used by dev mode; also informs meta in prod)
- `--mode`: `dev` (default) or `prod`
- `--preserve-form-feeds`: keep form-feed separators between pages in raw
- `--no-reflow`, `--no-dehyphenate`, `--no-dedupe-spaces`, `--no-strip-trailing`: fine-grained well‑done controls
- `--emit-jsonl`: present for compatibility but deprecated; behavior controlled by `--mode`
- `--insert-pg`: currently accepted but not used (DB insert is stubbed)

## Outputs (dev mode)

- Raw text: `<stem>_raw.txt`
- Well‑done text: `<stem>_well_done.txt`
- Ingest meta: `<stem>_ingest_meta.json`
- JSONL: `<stem>_well_done.jsonl` (each line is one block; includes reference to ingest meta)
- JSONL meta: `<stem>_well_done_meta.json`

Output directory selection:

- If the input path contains `.../books/<book>/...`, the default output dir is `data/clean/<book>/`.
- Otherwise, defaults to `"<input_dir>/clean/"`.
- You can override with `--out-dir`.

## Processing details

- Raw extraction assembles per-page text with configurable options (newline, form-feed preservation, etc.).
- Well‑done processing reflows paragraphs and applies cleanup:
  - Reflow paragraphs, dehyphenate wraps, dedupe inline spaces, strip trailing spaces
  - Optional heuristics exist in `RawToWellDone` to improve TOC handling and heading splitting (available via code options; CLI flags may be added later)
- JSONL conversion produces a block-per-line dataset with a small companion meta file; it links to the ingest meta when available.

## What changed vs before

- Mode semantics changed:
  - Old: `--mode both|dev` with separate control for JSONL emission
  - New: `--mode dev|prod`; dev writes artifacts + DB stub, prod writes none + DB stub
- `--emit-jsonl` is now deprecated and effectively ignored: dev writes JSONL; prod does not write artifacts
- PgInserter (direct Postgres insertion) is removed from the pipeline; replaced with a stub `_stub_db_insert` and a TODO

## TODOs (to be addressed when DB is ready)

- Implement real Postgres insertion in place of `_stub_db_insert`
  - Reintroduce `PgInserter` (or a service) and wire in prod mode
  - Ensure robust error handling and idempotency
- Consider adding CLI flags to expose `split_headings` and other advanced well‑done heuristics
- Documentation integration: update doc indices and references to point here (see integration checklist)

## Quick validation

- Dev mode smoke test:
  - Expect files to exist: `_raw.txt`, `_well_done.txt`, `_ingest_meta.json`, `_well_done.jsonl`, `_well_done_meta.json`
  - Terminal prints a `[DB STUB]` line indicating a would-be insert with paths
- Prod mode smoke test:
  - Expect no files written
  - Terminal prints a `[DB STUB]` line indicating an in-memory insert

---

If any ambiguity arises during integration, prefer dev mode for local testing and artifact inspection. Prod mode is intended for future automated ingestion pipelines once real DB insertion is available.
