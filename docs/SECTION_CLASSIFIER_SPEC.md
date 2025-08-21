# Section Classifier – Design Spec

Last updated: 2025-08-21

Source diagram: [docs/diagrams/section_classifier.mmd](diagrams/section_classifier.mmd)

## Purpose

Identify front matter, TOC, body chapters, and back matter in a novel PDF converted to simple TXT pages. Provide deterministic chapter boundaries and a TOC when present.

## Contract

- Input: pages: List[{ page_idx: int, text: str }]
- Output:
  - toc: List[{ title: str, page: int }]
  - chapters: List[{ index: int, title?: str, start_page: int, end_page: int, start_offset?: int, end_offset?: int }]
  - sections: { front_matter_pages: int[], toc_pages: int[], back_matter_pages: int[] }
  - per_page_labels: List[{ page_idx: int, label: 'front'|'toc'|'body'|'back', confidence: float, signals: Record<string, any> }]
  - warnings: string[]

## Determinism

- All rules heuristic and order-stable.
- No network/ML calls.
- Results depend only on input text and fixed regex/thresholds.

## Pipeline (high level)

1. Preprocess

- Normalize whitespace; keep page_idx; preserve line boundaries.
- Optional header/footer strip if consistent (first/last N lines repeated across pages).

1. TOC Detection

- Signals:
  - Page contains keywords: /\b(contents|table of contents)\b/i
  - Dotted leaders ratio: lines matching /\.{3,}\s*\d+$/
  - Lines ending with page numbers: /\d+$/
  - Ascending page numbers across entries
  - Entry density: many short lines
- Output: toc entries [{title,page}] and toc_pages.

1. Heading Detection (Body)

- Regexes:
  - Chapter: /^(chapter)\s+(\d+|[IVXLCDM]+)\b/i
  - Numeric-only title: /^(\d{1,3})$/
  - Roman numeral line: /^(?:[IVXLCDM]+)$/
  - Prologue/Epilogue: /\b(prologue|epilogue)\b/i
  - Part: /^(part)\s+(\d+|[IVXLCDM]+)\b/i
- Heuristics:
  - UPPERCASE short line (<= 32 chars) with high alpha ratio
  - Proximity to page top (first 10 lines)

1. Page Scoring + Labels

- front signals: /copyright|isbn|all rights reserved|dedication|foreword|preface|prologue/i
- back signals: /acknowledgments|about the author|reading group guide|afterword|notes|glossary|appendix|preview/i
- toc signals: from TOC detection
- body: default when chapter/part/prologue/epilogue/heading signals present
- Produce label and confidence per page; include signals for explainability.

1. Smoothing

- Enforce logical order: Front → TOC? → Body → Back using a tiny state machine.

1. Chapter Boundaries

- If TOC present: anchor chapter starts to toc.page with ±1–2 page tolerance.
- Else: use heading pages as starts.
- Ends: next start_page − 1 (last chapter ends at last body page).
- Validate: mismatch between expected (TOC count) and detected; emit warnings.

## Output Schema Details

- toc entries titles are raw text (no normalization beyond trim).
- chapter.index is 0‑based.
- start_offset/end_offset may remain unset in KISS v1.

## Integration

- Add an optional `classifier` block to the Volume Manifest:

 ```jsonc
{
  "classifier": {
    "front_matter_pages": [0,1,2],
    "toc_pages": [3],
    "back_matter_pages": [210,211],
    "toc": [ { "title": "Chapter 1", "page": 7 }, ... ],
    "warnings": ["toc_count_mismatch: expected 12, found 11"]
  }
}
```

- Chapter JSON remains unchanged.

## Tests (minimal)

- Happy path: TOC present, numeric Chapter N headings; assert chapter count and page anchors.
- No TOC: detect headings; ensure front/back blocks identified.
- Roman numerals: detect CHAPTER IV style.
- Edge: epigraph page between header and first paragraph (should remain body; not a chapter start).

## Future (optional)

- Language-specific keyword lists.
- Learning thresholds per book (but keep deterministic).
- Per-chapter offset mapping (char offsets into concatenated text).
