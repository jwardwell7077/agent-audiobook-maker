# TXT → JSON (Raw) Spec

Goal: Convert normalized TXT into a deterministic JSON Lines (JSONL) representation capturing pages and paragraphs for downstream classification.

## Scope (KISS)

- Pages are delimited by form feed characters (\f). If absent, treat entire file as a single page.
- Paragraphs are blocks of non-empty lines separated by one or more blank lines. Keep intra-paragraph single newlines.
- Whitespace normalization: strip trailing spaces, collapse runs of spaces to a single space within lines, preserve single newlines inside a paragraph.

## Inputs

- txt_path: path to UTF-8 text file produced by PdfToTextExtractor
- out_path: path to JSONL file to write
- options:
  - preserve_form_feeds: bool (default True) – when True, \f splits pages; when False, treat as literal and single page
  - newline: "\n" or "\r\n" – newline to consider when post-normalizing paragraph joins

## Outputs (JSONL)

- One JSON object per paragraph with fields:
  - page: int (1-based)
  - para_index: int (0-based within page)
  - text: string (paragraph text; internal newlines may appear if source lines did not split paragraph)
- Optional synthetic page boundary records are not written; the page number on each paragraph encodes page membership deterministically.

## Error Modes

- Missing txt_path → FileNotFoundError
- Non-UTF8 → UnicodeDecodeError
- Invalid newline option → ValueError

## Determinism

- Given the same input file, options, and newline, output JSONL will be byte-identical across runs.

## Test Plan

- Happy path: synthetic TXT with two pages and several paragraphs → assert paragraph count, ordering, and page numbers.
- No form feeds: entire file treated as page 1.
- Invalid newline raises ValueError.
- Determinism: two runs produce identical bytes.
