# Section Classifier Design Specification

## Overview

A block-based, paragraph-first classifier that segments books into chapters using a detected Table of Contents (TOC) and body chapter headings. The algorithm enforces strict matching and progressively loosens checks with explicit warnings. It aims for correctness-first (fail fast) while being resilient to common OCR and formatting artifacts.

## Inputs and Outputs

- Input: JSONL-only. The classifier SHALL accept only a JSONL file where each line is a JSON object with at least a `text: string` field (one paragraph/block per line). Body chapter heading blocks contain only the heading.
- Output artifacts:
  - toc: { entries: [{chapter_index, title, start_block, end_block}], warnings: [str] }
  - chapters: { chapters: \[{chapter_index, title, start_block, end_block, paragraphs: list[str]}\] }
  - front_matter: { span_blocks: [start,end] or [-1,-1], paragraphs: list[str], warnings: [str] }
  - back_matter: { span_blocks: [start,end] or [-1,-1], paragraphs: list[str], warnings: [str] }

All spans are inclusive and use zero-based block indices.

## Block Model

- Blocks are produced by upstream ingestion and persisted as JSONL: one JSON object per line with `text` (and typically `index`). Whitespace-only blocks are removed upstream.
- Body chapter headings are detected on a whole-block basis (no line-by-line matching inside a block).

## CLI Contract

- Invocation: `classifier_cli <input.jsonl> <output_dir>`
- The CLI MUST error out (non-zero exit) if:
  - the input path does not end with `.jsonl`, or
  - the file content is not line-delimited JSON objects with a `text` string field, or
  - zero valid blocks are found.
- The classifier does not split text; it consumes JSONL blocks as-is.

## TOC Detection

- Find the TOC heading by scanning block lines for a heading that matches:
  - "table of contents" or "contents" (case-insensitive).
- Sanity check: look ahead up to 5 blocks after the TOC heading and require at least two TOC-looking lines (to avoid false positives).

## TOC Item Parsing

- Parse starting at the TOC heading block, moving forward block-by-block.
- A TOC item line matches the pattern: optional bullet (•,-,\*) + ("chapter <digits>" | "prologue" | "epilogue") + optional punctuation + captured title.
- For each TOC item, extract:
  - title (str)
  - ordinal (int or None), if the line includes "chapter <digits>".

### Canonical Title Normalization (canon_title)

Used for dedupe and robust title equality:

- Unicode NFKD, drop combining marks (diacritics)
- Lowercase
- Remove punctuation/symbols (keep letters/digits/spaces)
- Collapse internal whitespace and trim

### Dedupe and Stop Rules

- Maintain seen_titles: Set[canon_title(title)] and seen_ordinals: Dict[int -> canon_title].
- Stop conditions (in priority order once ≥ 2 TOC items have been parsed):
  1. First whole-block body chapter heading encountered → stop TOC (do not consume this block).
  1. Duplicate TOC title encountered (canon equal) → stop TOC; do not consume this block. Warning: "TOC ended on duplicate title: '<title>' (block j)".
  1. Ordinal conflict: same chapter number appears with a different title canon → stop TOC; keep first. Warning: "ordinal conflict in TOC at block j: chapter n titles differ; keeping first".
  1. A non-TOC block appears after items were found → stop TOC.
- Dedupe during parsing:
  - If a duplicate title is seen before ≥ 2 items exist, skip it and warn: "duplicate TOC item skipped: '<title>' (block j)".
- toc_end is set to the last block that actually contained a TOC item (last_item_block), not the first non-item block.

## First Body Heading Block

A block is a body heading only if the entire block matches the anchored heading shape:

- Starts with "Chapter <digits>" or "Prologue/Epilogue"
- Optional punctuation and optional title
- No other content in the block

This rule prevents misclassifying TOC lines or narrative paragraphs as headings.

## Matching Passes (per TOC item)

The classifier searches forward from the previous match to preserve chapter order. It uses the following passes and stops at the first success:

1. Strict exact title match

   - Condition: block is a body heading AND heading_title.strip() == toc_title.strip() (case-sensitive exact after trim)
   - Warning: none

1. Normalized/canonical title match

   - Condition: block is a body heading AND canon_title(heading_title) == canon_title(toc_title)
   - Warning: "title normalized match used for TOC entry '<title>' matched at block i"

1. Ordinal fallback

   - Condition: block is a body heading with digits AND digits == toc ordinal
   - Warning: "ordinal fallback used for TOC entry '<title>' (chapter n) matched at block i"

Failure mode: If none of the passes match, raise an error: "Chapter heading not found for TOC entry: '<title>'".

## Warnings Taxonomy

- TOC parsing warnings:
  - duplicate TOC item skipped: '<title>' (block j)
  - TOC ended on duplicate title: '<title>' (block j)
  - ordinal conflict in TOC at block j: chapter n titles differ; keeping first
- Heading matching warnings (emitted per item):
  - title normalized match used for TOC entry '<title>' matched at block i
  - ordinal fallback used for TOC entry '<title>' (chapter n) matched at block i
- Front matter warning:
  - unclaimed blocks: [indices]

Warnings from heading matching are surfaced together with TOC warnings under toc.warnings; front/back keep their own warnings fields.

## Spans and Claiming

- TOC blocks: all blocks from toc_start to toc_end inclusive are claimed as TOC.
- Chapters: each chapter spans from its heading (start_block) to the block before the next chapter heading (end_block). All blocks in that span are claimed.
- Front matter: unclaimed blocks before first chapter (excluding TOC) → span + paragraphs + warnings.
- Back matter: unclaimed blocks after last chapter → span + paragraphs.

## Error Modes

- TOC heading not found → error.
- TOC heading found but fewer than 2 TOC-looking lines ahead → error.
- No TOC entries parsed → error.
- Chapter heading not found for a TOC entry (after all passes) → error.
- Duplicate chapter heading match at the same block index → error.

## Edge Cases and Guards

- Duplicate TOC items: deduped by canonical title; once ≥ 2 items exist, a duplicate ends TOC.
- Ordinal conflicts: stop TOC on conflict and keep the first title for that number.
- Monotonic progression: start_search moves to match_idx + 1 to maintain order.
- Body headings with missing titles: ordinal fallback will still work (with warning) if digits are present.
- Body headings using spelled-out or Roman numerals: not matched yet (see Future Work).

## Example (from mvs JSONL)

- index 12–15: "• Chapter 1: Just an old Book", "• Chapter 2: …", "• Chapter 3: …", "• Chapter 4: …"
- Body snippet:
  - index 712: "Chapter 1: Just an old Book" (body heading)
  - index 713+: narrative blocks

Behavior:

- TOC items parsed from 12–15; toc_end = 15.

- First body heading is 712 (whole-block match), so TOC parsing ends well before 712.

- Matching for Chapter 1 succeeds in Pass 1 (strict exact title). No warnings for this item.

- leniency flags (future): enable spelled-out/Roman numerals, fuzzy title matching thresholds. Default remains strict.

- logging/warnings aggregation: printable and/or return-embedded (current: toc.warnings, front/back warnings).

## Future Work (TODO)

- Recognize spelled-out and Roman numerals in body headings (e.g., "Chapter One", "Chapter I") and map to ordinals for fallback and matching.

- Optional fuzzy title similarity (e.g., ≥ 0.9) behind a feature flag, with clear warnings.

- Deterministic segmentation with strict contract and clear error modes.

- No double-inclusion of chapters due to TOC spillover or duplicates.

- Robust to punctuation, case, whitespace, and diacritics differences in titles.

# Section Classifier – Block-based Design Spec

This version replaces the prior page-based design with a paragraph/block-first approach.

## Purpose

Given a plain-text book, split it into paragraph blocks (blank-line separated) and deterministically classify four regions: front matter, table of contents (TOC), chapters, and back matter. Emit four JSON artifacts using zero-based block indices as the source of truth.

- txt_path: UTF-8 text with Unix newlines ("\\n").
- Block loading:
  - Split on blank-line boundaries using regex like `\n\s*\n+`.
  - Preserve inner whitespace and line breaks inside each block.
  - Drop empty/whitespace-only blocks.

Default directory: `data/clean/<book>/classified` (overridable).

- front_matter.json

  - { span_blocks: [start:number, end:number] | [-1,-1] when empty, paragraphs: string[], warnings: string[] }

- back_matter.json Field names and shapes must match the example artifacts (ex_toc.json, ex_chapters.json) and current code.

- Detect a TOC heading via regex anchored at the start of a line (allow leading whitespace): `/^\s*(table of contents|contents)\b/i`.

- After the heading, look ahead up to 5 blocks for TOC-like chapter list lines. Characteristics:

  - Bullet is optional (•, -, \*, or none).
  - Case-insensitive; arbitrary whitespace allowed.
  - Accept forms like: `Chapter 1: Title`, `1. Title`, `I. Title`, `Prologue`, `Epilogue`, optionally with dot leaders.

- If the lookahead doesn’t present at least two TOC-like lines → error and exit.

- Parse TOC entries (title and optional ordinal).

- Find the first body block whose heading matches the first TOC entry by title (preferred) or ordinal (fallback). Once found, the TOC region is from the heading block index to the block before this first chapter block.

## Chapter matching and spans

- For each TOC entry, locate its chapter heading block in the body:
  - Match by title primarily (case-insensitive, whitespace-tolerant, minimal normalization).
  - Fallback to matching by ordinal (`Chapter N`).
  - Accept `Prologue` and `Epilogue` as chapters.
  - Multiple chapter headings in one block → error and exit.
  - TOC entry whose heading isn’t found → error and exit.
- Each chapter is a contiguous, inclusive block range: `[start_block, end_block]`.
  - The heading block is paragraph index 0 in that chapter’s `paragraphs` array.
  - `end_block` is the block before the next chapter’s `start_block`; the last chapter ends at the last block.

## Front/back matter and unclaimed blocks

- Maintain a `claimed` boolean per block (TOC + chapters claim their spans).
- Front matter: all unclaimed blocks before the first chapter, excluding TOC blocks.
- Back matter: all unclaimed blocks after the last chapter.
- Before writing artifacts, if any unclaimed blocks remain, log a WARNING with their indices; at DEBUG, also log their contents.

## Determinism and constraints

- Pure regex/string heuristics; no network/ML.
- Order-stable and deterministic: same input produces identical outputs.
- Zero-based, inclusive spans in all outputs.

## Error modes

- No TOC heading or insufficient TOC-like items in lookahead → error.
- Multiple chapter headings in the same block → error.
- TOC entry whose heading cannot be located in the body → error.
- Overlapping or unsorted chapter spans (shouldn’t occur with the algorithm) → error.

## Tests (minimum)

- Happy path: TOC present with `Chapter N: Title`; all chapters matched; verify indices and paragraphs grouped correctly.
- Prologue/Epilogue variants.
- TOC present but a chapter title mismatch → raises with clear message.
- Multiple chapter headings in a single block → raises.

## Integration

- Downstream components consume `chapters.json` paragraphs and chapter indices directly; blocks remain the source of truth.
- Downstream can derive per-chapter JSON from JSONL blocks using chapter spans when needed.
