# Classifier Changes vs fa99ab7723ba793f0a98534fab2b207d0abc0022

Summary of key changes that affect behavior:

- CLI contract:
  - Rejects `.txt`; accepts only `.json` (with top-level `{ "blocks": list[str] }`) or `.jsonl` (objects with `text`).
  - Reads blocks in-memory and calls `classify_sections({"blocks": [...]})`.
- Algorithm:
  - TOC detection simplified: anchored heading (“contents”/“table of contents”), require ≥2 items within next 5 blocks.
  - TOC item regex simplified; removed dotted leader/page-number fallback.
  - Heading match: title-first loose startswith on normalized text; ordinal fallback; error if multiple headings in one block.
  - Dropped diacritic/punctuation canonicalization and line-based progression.
- Outputs:
  - `chapter_number` added (1-based) to `toc.entries[]` and `chapters.chapters[]`.
  - toc warnings and toc_span removed; unclaimed warning consolidated under `front_matter`.

Impact:

- Inputs must be structured; pipelines feeding `.txt` will fail.
- TOC/heading matching is stricter; some books that matched before may need schema-friendly TOC formatting in JSONL.

Options to relax (if needed):

- Extend `_TOC_ITEM_RE` to accept dotted leaders/page numbers.
- Reintroduce canonicalization for robust title matching.
- Fallback body heading scan when TOC not detected.
