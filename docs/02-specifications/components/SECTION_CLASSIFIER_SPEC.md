# Section Classifier – Design Spec

Last updated: 2025-08-21

Source diagram: [../../04-diagrams/flows/section_classifier.mmd](../../04-diagrams/flows/section_classifier.mmd)

## Purpose

Identify front matter, TOC, body chapters region, and back matter in a novel PDF converted to simple TXT pages. Produce four separate JSON artifacts (one per section) and capture page-number markers while building a single continuous body of text (pages concatenated back-to-back, with page-number-only lines removed). If a line contains content plus a page number token, attempt to remove only the number and emit a warning.

## Contract (Step 1 – Classifier)

- Input: pages: List[{ page_idx: int, lines: str[] }]
- Continuous body text: join all page lines into a single text buffer, removing page-number-only lines. If a page number appears inline with other content, attempt to remove just the number token and emit a warning. Preserve line order and other content.
Output artifacts (four separate JSON files in `data/clean/<book>/<pdf_stem>/classified/`):
  - front_matter.json
  - { span: [start_char, end_char], text_sha256, warnings: string[], document_meta: { page_markers: Array<{ page_index: int, line_index_global: int, value: string }> } }
  - Schema: [docs/schemas/classifier/front_matter.schema.json](schemas/classifier/front_matter.schema.json)
  - Example: [docs/examples/classifier/front_matter.example.json](examples/classifier/front_matter.example.json)
  - toc.json
  - { span: [start_char, end_char], entries: Array<{ title: string, page: int, raw: string, line_in_toc: int }>, warnings: string[] }
  - Schema: [docs/schemas/classifier/toc.schema.json](schemas/classifier/toc.schema.json)
  - Example: [docs/examples/classifier/toc.example.json](examples/classifier/toc.example.json)
  - chapters_section.json
  - { span: [start_char, end_char], per_page_labels: Array<{ page_index: int, label: 'front'|'toc'|'body'|'back', confidence: number }>, warnings: string[] }
  - Schema: [docs/schemas/classifier/chapters_section.schema.json](schemas/classifier/chapters_section.schema.json)
  - Example: [docs/examples/classifier/chapters_section.example.json](examples/classifier/chapters_section.example.json)
  - back_matter.json
  - { span: [start_char, end_char], text_sha256, warnings: string[] }
  - Schema: [docs/schemas/classifier/back_matter.schema.json](schemas/classifier/back_matter.schema.json)
  - Example: [docs/examples/classifier/back_matter.example.json](examples/classifier/back_matter.example.json)

Notes

- page_markers capture page numbers detected and their location in the continuous text (global line index). Body text excludes page-number-only lines; mixed-content lines are cleaned if the page number token can be safely removed (warning recorded).

## Determinism

- All rules heuristic and order-stable.
- No network/ML calls.
- Results depend only on input text and fixed regex/thresholds.

## Pipeline (high level)

1. Preprocess

- Normalize whitespace; keep page_index; preserve line boundaries.
- Page numbers:
  - If an entire line is a page number (e.g., `12`, `Page 12`, roman numerals), remove the line from body and record a page_marker.
  - If a line contains content plus an apparent page number token, attempt to remove just the number token; record a page_marker and emit a warning.
  - If ambiguous, keep the line as-is; record a warning.

1. TOC Detection

- Signals:
  - Page contains keywords: /\\b(contents|table of contents)\\b/i
  - Dotted leaders ratio: lines matching /.{3,}\\s\*\\d+$/
  - Lines ending with page numbers: /\\d+$/
  - Ascending page numbers across entries
  - Entry density: many short lines
- Output: toc entries [{title,page}] and toc_pages.

1. Heading Detection (Body)

- Regexes:
  - Chapter: /^(chapter)\\s+(\\d+|[IVXLCDM]+)\\b/i
  - Numeric-only title: /^(\\d{1,3})$/
  - Roman numeral line: /^(?:[IVXLCDM]+)$/
  - Prologue/Epilogue: /\\b(prologue|epilogue)\\b/i
  - Part: /^(part)\\s+(\\d+|[IVXLCDM]+)\\b/i
- Heuristics:
  - UPPERCASE short line (\<= 32 chars) with high alpha ratio
  - Proximity to page top (first 10 lines)

1. Page Scoring + Labels

- front signals: /copyright|isbn|all rights reserved|dedication|foreword|preface|prologue/i
- back signals: /acknowledgments|about the author|reading group guide|afterword|notes|glossary|appendix|preview/i
- toc signals: from TOC detection
- body: default when chapter/part/prologue/epilogue/heading signals present
- Produce label and confidence per page; include signals for explainability.

1. Smoothing

- Enforce logical order: Front → TOC? → Body → Back using a tiny state machine.

1. Section Spans

- Compute spans for front_matter, toc, chapters_section, back_matter within the continuous text buffer.
- Persist four JSON files with spans and metadata as described above.

- If TOC present: anchor chapter starts to toc.page with ±1–2 page tolerance.
- Else: use heading pages as starts.
- Ends: next start_page − 1 (last chapter ends at last body page).
- Validate: mismatch between expected (TOC count) and detected; emit warnings.

## Output Schema Details

- TOC entries `title` must be treated as-is; normalization only for whitespace trim when comparing.
- When later used for title matching, titles must appear as the only entity on a line (anchor to line start/end), case- and space-insensitive.

## Integration

- Classifier outputs are stored as four separate JSON files under the classified folder for downstream chapterization.
- Volume Manifest and Chapter JSON remain unchanged in v1.0; they may reference classifier outputs via paths in future versions.

## Tests (minimal)

- Happy path: TOC present, numeric Chapter N headings; assert chapter count and page anchors.
- No TOC: detect headings; ensure front/back blocks identified.
- Roman numerals: detect CHAPTER IV style.
- Edge: epigraph page between header and first paragraph (should remain body; not a chapter start).

## Future (optional)

- Language-specific keyword lists.
- Learning thresholds per book (but keep deterministic).
- Per-chapter offset mapping (char offsets into concatenated text).

## Finite State Machine

Diagram: [../../04-diagrams/state-machines/section_classifier_fsm.mmd](../../04-diagrams/state-machines/section_classifier_fsm.mmd)

UML (component/service): [../../04-diagrams/uml/section_classifier_uml.mmd](../../04-diagrams/uml/section_classifier_uml.mmd)

States

- Front (Front Matter)
- TOC
- Body
- Back (Back Matter)
- End

Events (evaluated per page)

- E_front: front signals present (copyright, isbn, dedication, foreword, preface, prologue)
- E_toc: TOC signals ("Contents", dotted leaders, lines ending with numbers, entry density)
- E_heading: heading signals (Chapter/Part/Prologue/Epilogue regex, UPPERCASE short line, numeric-only, Roman numerals)
- E_back: back signals (acknowledgments, about the author, reading group guide, afterword, notes, glossary, appendix, preview)
- E_page_num_line: line is page-number-only; remove and record marker
- E_eof: end of pages

Guards

- G_toc_detected: we are on a TOC page or contiguous TOC continues
- G_anchor_match: page matches TOC anchor within ± tolerance
- G_after_last_chapter: expected chapters (from TOC) reached
- G_sustained_back: >= 2 consecutive back-signal pages

Transitions

- Front → TOC: E_toc
- Front → Body: E_heading OR (!E_toc AND !E_front)
- Front → Front: E_front AND !E_heading AND !E_toc
- TOC → TOC: G_toc_detected
- TOC → Body: E_heading OR !G_toc_detected
- Body → Body: NOT (E_back AND (G_after_last_chapter OR G_sustained_back))
- Body → Back: E_back AND (G_after_last_chapter OR G_sustained_back)
- Back → Back: NOT E_eof
- Back → End: E_eof
- Body → End: E_eof
- TOC → End: E_eof
- Front → End: E_eof
- Any → same: E_page_num_line (remove line, record marker; does not affect state)
