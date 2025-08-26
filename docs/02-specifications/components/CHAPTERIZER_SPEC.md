# Chapterizer – Design Spec (Deprecated)

Note: The Chapterizer component has been removed. Chapter structure is now derived from the Section Classifier outputs (toc.json, chapters_section.json). This spec remains for historical reference.

Last updated: 2025-08-21

Depends on: Section Classifier outputs (four JSON files) and continuous body text.

## Purpose

Use the TOC entries to locate chapter starts in the chapters section of the continuous body text and slice into per-chapter spans deterministically. Titles must match as the only entity on a line (anchored ^ and $), case- and space-insensitive.

## Contract (Step 2 – Chapterizer)

- Inputs
  - body_text: continuous text (page numbers removed)
  - chapters_section span: [start_char, end_char]
  - toc entries: [{ title, page, raw }]
- Matching rules
  - Primary: match full TOC `title` as the only entity on a line (anchor ^ and $), case-insensitive, whitespace-normalized.
  - If >5 matches for any single title, abort (likely header/footer artifact). Record duplicate_title_matches and warning.
  - If 0 matches for a title, attempt numeric fallback patterns per title index (e.g., "Chapter 1", "Ch 1", roman numerals). Warn when fallback used.
  - If >40% titles unmatched overall, abort as unreliable TOC.
- Output (chapters.json)
  - chapters: [{ index, title, start_char, end_char, body_text }]
  - unmatched_titles: [string]
  - duplicate_title_matches: [{ title, count }]
  - warnings: [string]
  - version, created_at

## Algorithm

1. Extract the chapters slice from body_text using span.
1. Build regex for each title: ^\s*\<title\>\s*$ (escaped), case-insensitive.
1. Locate all matches; enforce thresholds (>5 → abort; 2 → warn; expected 1).
1. If no match, generate fallback patterns for that index and retry.
1. Sort unique match positions; build spans [start_i, start_{i+1}).
1. Assemble chapter list; track unmatched and duplicates; emit warnings.

## FSM (Chapterizer)

Source: docs/diagrams/chapterizer_fsm.mmd

States: Init → ScanTitles → ValidateMatches → SliceChapters → Done | Abort

Events:

- E_title_match(title, n)
- E_duplicate(title, n>5)
- E_many_unmatched(ratio>0.4)
- E_done

Transitions:

- Init → ScanTitles
- ScanTitles → ValidateMatches (when all titles scanned)
- ValidateMatches → Abort: E_duplicate OR E_many_unmatched
- ValidateMatches → SliceChapters (otherwise)
- SliceChapters → Done

## Tests

- Happy path: titles match once each; correct slices.
- Duplicate header/footer: one title matches >5 times → abort.
- Fallback numeric pattern used → warn, still slice.
- No matches at all → abort.

## Integration

- Source of truth upstream: the Section Classifier emits `chapters_section.json` alongside other classified artifacts. The Chapterizer must operate on the `chapters_section` span within the continuous `body_text` and produce a deterministic `chapters.json`.
- Downstream: each `chapters[i].body_text` is fed into TXT→Structured to generate `paragraphs[]` while preserving explicit blank lines.
