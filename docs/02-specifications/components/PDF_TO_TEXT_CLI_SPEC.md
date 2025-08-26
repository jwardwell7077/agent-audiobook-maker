# PDF → Text CLI — Design Spec (Deprecated)

Note: This CLI has been deprecated in favor of the unified ingestion pipeline v2. Use `python -m abm.ingestion.ingest_pdf <pdf> --out-dir <dir> [--mode dev]` instead. See docs/INGESTION_PIPELINE_V2.md.

Status: Deprecated
Owner: jon
Last updated: 2025-08-21

## Overview

Thin CLI wrapper around the extractor to keep business logic in the library and provide a simple, scriptable interface. The CLI must not introduce nondeterminism; it only parses args, calls the extractor, and handles exit codes.

## Command

- Module entrypoint: `python -m src.ingestion.pdf_to_text`
- Usage: `python -m src.ingestion.pdf_to_text <input.pdf> <output.txt> [--no-dedupe-whitespace] [--preserve-form-feeds] [--newline "\n|\r\n"] [--use-blocks/--no-use-blocks] [--insert-blank-line-between-blocks/--no-insert-blank-line-between-blocks] [--block-gap-threshold <int>]`

## Flags

- --no-dedupe-whitespace (default off): sets options.dedupe_whitespace = False
- --preserve-form-feeds (default off): sets options.preserve_form_feeds = True
- --newline (default "\n"): sets options.newline to given value (validated to "\n" or "\r\n")
- --use-blocks / --no-use-blocks (default on): toggle options.use_blocks
- --insert-blank-line-between-blocks / --no-insert-blank-line-between-blocks (default on): toggle options.insert_blank_line_between_blocks
- --block-gap-threshold `INT` (default 6): sets options.block_gap_threshold

## Contracts

Inputs

- input.pdf: existing PDF path
- output.txt: destination path (parent dir must exist)

Behavior

- Exit 0 on success, nonzero on error; stderr prints a short message
- Never modifies the input; overwrites output only on explicit path (no temp files left behind)

## Requirements

1. R-QUALITY-GATE: Passes quality gate.
2. R-THIN: No PDF parsing logic in CLI; all logic lives in `src.ingestion.pdf_to_text`.
3. R-ARGS: Invalid args produce clear usage and nonzero exit.

## Test Plan

- test_cli_happy: runs against a tiny local PDF, writes expected output file
- test_cli_invalid_path: returns nonzero and message
- test_cli_flags: toggles whitespace dedupe and form feed/newline options
- test_cli_block_flags: toggles block-aware extraction flags and threshold

## Out of Scope

- Progress bars, logging config, or batch processing (can be layered later)
