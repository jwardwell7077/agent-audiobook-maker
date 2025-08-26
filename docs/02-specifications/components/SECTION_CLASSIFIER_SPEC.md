# Section Classifier – Block-based Design Spec

Last updated: 2025-08-26

This version replaces the prior page-based design with a paragraph/block-first approach.

## Purpose

Given a plain-text book, split it into paragraph blocks (blank-line separated) and deterministically classify four regions: front matter, table of contents (TOC), chapters, and back matter. Emit four JSON artifacts using zero-based block indices as the source of truth.

## Input

- txt_path: UTF-8 text with Unix newlines ("\n").
- Block loading:
  - Split on blank-line boundaries using regex like `\n\s*\n+`.
  - Preserve inner whitespace and line breaks inside each block.
  - Drop empty/whitespace-only blocks.
  - Blocks are immutable; indexing is zero-based everywhere.
  - Spans are inclusive: `[start_block, end_block]`.

## Outputs (four files)

Default directory: `data/clean/<book>/classified` (overridable).

- toc.json
  - { entries: Array<{ chapter_index: number, title: string, start_block: number, end_block: number }> }
- chapters.json
  - { chapters: Array<{ chapter_index: number, title: string, start_block: number, end_block: number, paragraphs: string[] }> }
- front_matter.json
  - { span_blocks: [start:number, end:number] | [-1,-1] when empty, paragraphs: string[], warnings: string[] }
- back_matter.json
  - { span_blocks: [start:number, end:number] | [-1,-1] when empty, paragraphs: string[], warnings: string[] }

Field names and shapes must match the example artifacts (ex_toc.json, ex_chapters.json) and current code.

## TOC detection and use

- Detect a TOC heading via regex anchored at the start of a line (allow leading whitespace): `/^\s*(table of contents|contents)\b/i`.
- After the heading, look ahead up to 5 blocks for TOC-like chapter list lines. Characteristics:
  - Bullet is optional (•, -, *, or none).
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
