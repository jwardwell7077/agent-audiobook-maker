# TXT → Structured JSON – Design Spec

Last updated: 2025-08-25

Depends on: Simple TXT extracted from PDF and optionally the classified artifacts (chapters_section span) to scope per-chapter conversion.

## Purpose

Convert a plain-text chapter into a structured JSON representation that preserves paragraphs and intentional blank lines deterministically. This enables downstream dialogue segmentation and attribution with faithful context.

## Contract

- Input
	- txt_path or raw_text: UTF-8, Unix newlines ("\n").
	- options (optional):
		- preserve_lines: bool (default true) – if true, keep empty lines and merge them into the previous paragraph as a double newline marker.
		- normalize_eol: bool (default true) – normalize CRLF/CR to LF.
		- max_paragraph_len: int (optional) – soft wrap threshold (no reflow by default).
- Output (chapter_structured.json)
	- book_name, chapter_index, chapter_title
	- paragraphs: string[] – each entry is a paragraph; a blank line between paragraphs is represented by a double newline "\n\n" inside the previous paragraph when preserve_lines=true.
	- stats: { paragraph_count, char_count, word_count }
	- sha256: hex – hash of normalized input for determinism.
	- version, created_at

## Invariants

- Deterministic: identical input bytes → identical output JSON bytes (ordering, spacing preserved where configured).
- No AI/ML; pure string processing and normalization.
- Paragraph boundaries derived from blank-line separators and heuristic block detection (if upstream blocks supplied).

## Algorithm (default)

1. Read text and normalize line endings to LF if normalize_eol=true.
2. Split into lines.
3. Group lines into paragraphs:
	 - A blank line starts a new paragraph.
	 - If preserve_lines=true, retain explicit blank lines by appending "\n\n" to the preceding paragraph.
4. Trim trailing whitespace; do not collapse internal whitespace.
5. Compute stats and sha256.
6. Emit JSON.

## Error Modes

- FileNotFoundError: when txt_path missing.
- UnicodeDecodeError: invalid encoding – surface a clean error.

## Tests

- CRLF normalization: "\r\n" → "\n".
- Blank-line fidelity: single blank line preserved as double newline in previous paragraph.
- Paragraph grouping on consecutive blanks (multiple blanks collapse to a single paragraph boundary; extra blanks preserved via repeated "\n\n" when preserve_lines=true).
- Determinism: stable sha256 and JSON output for identical input.

## Integration

- When processing full books, scope to the chapters_section span from Section Classifier, then pass each chapter slice into this converter to populate paragraphs[].

