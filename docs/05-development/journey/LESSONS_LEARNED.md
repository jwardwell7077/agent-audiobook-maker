# Lessons Learned Diary

This document captures evolving insights during development of the audiobook ingestion MVP (initially single‑book focused; now generalized with a synthetic public sample).

## 2025-08-13

### Text Extraction Fidelity

- Initial extraction relied on `pypdf`, which collapsed spacing for glyph-positioned text -> produced concatenated tokens (e.g., `Quinncontinued`), breaking readability and downstream parsing assumptions.
- Introducing a PyMuPDF (`fitz`) backend and prioritizing it improved raw text fidelity (proper spaces and TOC detection gained: toc_count=45).
- Word-level reconstruction via `page.get_text('words')` with y-grouping further stabilized spacing across lines versus naive `get_text('text')` fallback.

### Structured TOC Parsing

- Parser originally required a space between `Chapter` and number (`Chapter\s+1`). Real extraction showed forms like `Chapter1` (no space). Adjusting regex to `Chapter\s*` enabled recognition without over-matching.
- Ensuring robust parsing required accommodating bullet characters (`•`) and optional punctuation.

### False Root Cause vs Actual Root Cause

- Initial suspicion: regex failure. Actual issue: upstream text normalization loss of spaces. Avoid premature regex modifications until verifying raw extraction output.

### Post-Processing

- Added optional hyphenation fix (env `INGEST_HYPHEN_FIX`) to stitch words broken across line wraps with trailing hyphen patterns (`word-\nnext`).

### Backend Control

- Added env `INGEST_FORCE_PYMUPDF=1` to force high-fidelity backend for consistency during MVP; useful for deterministic test runs.

### Performance Observations

- PyMuPDF extraction outperformed PyPDF in total time on sample (≈2.6s vs >10s) while producing higher character count (more whitespace retained) — underscores that removed whitespace is *not* a performance optimization but data loss.

### Testing Strategy

- Integration tests using synthetic minimal PDFs masked real-world spacing issues. Incorporating a canonical sample PDF early provides a realistic signal for layout robustness.

### Future Hardening Ideas

- Sentence boundary recovery after glyph-positioned text that lacks punctuation spacing.
- Configurable heuristics for merging overly fragmented lines.
- Detect and report unusually high average token length as a spacing loss signal.

______________________________________________________________________

(Add new dated sections as further insights emerge.)

## 2025-08-14

### Deterministic Extraction & Snapshot Update

- Problem: Purge regression test revealed non-deterministic chapter hashes (initially chapter 00020, later 00021) across successive ingests of the same PDF.
- Root Cause: Minor floating-point jitter in PyMuPDF word y-coordinates influenced heuristic line grouping; plus a missing-space artifact after specific patterns (`Blood type: OQuinn`).
- Actions:
  - Added deterministic sorting (round y, include original word index as tie-breaker).
  - Replaced incremental line grouping with y-quantization binning for stable grouping regardless of iteration order.
  - Added targeted post-processing rule to re-insert space in `Blood type` pattern collisions.
  - Captured new canonical hashes after two consistent ingest cycles (verified zero mismatches across cycles) and updated snapshot fixture.

### Testing Enhancements

- Expanded purge regression test to emit a preview snippet when a hash mismatch occurs, accelerating root cause analysis without storing full canonical text.
- Adjusted minimal purge index test expectations to reflect realistic structured parser behavior on synthetic fallback PDFs (some samples yield a single chapter due to confidence heuristics).

### Key Lesson

Deterministic text derivation is prerequisite for meaningful content-addressable artifacts (hashes). Seemingly benign floating-point ordering differences can invalidate snapshot tests; enforce deterministic ordering before snapshotting.

### Future Considerations

- Provide a utility script to regenerate hashes and diff against current snapshot (guardrails for intentional vs accidental changes).
- Optionally store a compressed canonical text bundle for deeper diffing beyond the first 20-line preview.

## 2025-08-24

### Mermaid Diagram Reliability on GitHub

- Issue: Multiple GitHub render failures — “Parse error” and “No diagram type detected”. Root causes:
  - `.mmd` files wrapped in ```mermaid fences; GitHub and tools expect raw Mermaid in standalone `.mmd` files.
  - Labels with parentheses, e.g., `PyMuPDF (fitz)`, can break the parser unless quoted.
  - Using flowchart dotted link syntax (`-.->`) inside `classDiagram` (UML) blocks; correct dependency arrow is `..>`.
  - Duplicate `classDiagram` directives and stray custom fence headers like `mermaid.radar`.
- Fixes:
  - Removed code fences from `.mmd` files; kept only raw Mermaid DSL.
  - Quoted or simplified labels with punctuation; preferred `"PyMuPDF / fitz"`.
  - Replaced `-.->` with `..>` in class diagrams; kept proper UML arrows elsewhere.
  - Ensured only one directive per diagram and used standard `mermaid` fences when embedding in `.md`.
- Lessons:
  - Keep `.mmd` raw; only `.md` uses ```mermaid fences.
  - Quote labels containing parentheses or special chars.
  - Use diagram-appropriate relations; UML arrows differ from flowchart links.
  - Add a quick validation step or preview before commit to avoid doc regressions.
- Checklist we now follow (also added to HOW_TO_DOCUMENT.md):
  - No fences in `.mmd` files; first line is `flowchart ...` or `classDiagram`.
  - No duplicate directives.
  - Quote/simplify labels with punctuation.
  - For class diagrams, use `..>`, `..|>`, `<|--`, `o--`, `*--`, `-->`/`--`.
