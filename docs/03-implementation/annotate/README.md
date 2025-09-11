# Annotation Pipeline Modules

> **Purpose**: Technical overview and usage examples for the annotation utilities that convert normalized chapters into speaker-tagged spans with optional LLM refinement.

The `abm.annotate` package orchestrates the end-to-end annotation flow:

1. **Normalization** – sanitize and tag raw paragraphs.
2. **Segmentation** – carve the chapter text into structured spans.
3. **Roster Building** – collect character aliases and merge them into canonical rosters.
4. **Attribution** – assign speakers and confidence scores to dialogue and thought spans.
5. **LLM Refinement (optional)** – re‑evaluate low‑confidence spans with a local model.
6. **Review Generation** – emit Markdown reports for manual QA.
7. **CLI Runner** – glue everything together for batch processing.

Each component is modular and unit tested; they can be composed individually or used via the [`annotate_cli.py`](../../../src/abm/annotate/annotate_cli.py) entrypoint.

## 1. Chapter Normalization

```python
from abm.annotate.normalize import ChapterNormalizer, NormalizerConfig

normalizer = ChapterNormalizer(NormalizerConfig())
chapter_out = normalizer.normalize(chapter_dict)
```

Key features:

- Joins paragraphs with `\n\n`, trims trailing spaces, and optionally strips control characters.
- Tags each paragraph as `Heading`, `SystemAngle`, `SystemSquare`, `SectionBreak`, `Meta`, or `None`.
- Records inline system tokens with offsets (`<Skill>`, `[Yes]`).
- Emits a `normalize_report` summarizing counts and any heading removal.

See [`normalize.py`](../../../src/abm/annotate/normalize.py) for details.

## 2. Span Segmentation

```python
from abm.annotate.segment import Segmenter

segmenter = Segmenter()
spans = segmenter.segment(chapter_out)
```

Highlights:

- Overlays structural spans (system lines, meta lines, headings, section breaks).
- Uses a quote state machine to extract `Dialogue` and `Thought` spans while preserving offsets.
- Supports inline system tokens and configurable merging of adjacent narration.

See [`segment.py`](../../../src/abm/annotate/segment.py).

## 3. Roster Building

```python
from abm.annotate.roster import build_chapter_roster, merge_book_roster

chap_roster = build_chapter_roster(chapter_out["text"])
book_roster = merge_book_roster(book_roster, chap_roster)
```

Capabilities:

- Heuristics for angle-tagged user lines, vocatives, and title+name patterns.
- Optional spaCy `PERSON` NER and rapidfuzz alias merging.
- Produces `{canonical: [aliases...]}` mappings for chapters and books.

Module: [`roster.py`](../../../src/abm/annotate/roster.py).

## 4. Attribution Engine

```python
from abm.annotate.attribute import AttributeEngine

engine = AttributeEngine(mode="high")
speaker, method, conf = engine.attribute_span(full_text, (start, end), span_type, roster)
```

Responsibilities:

- Combines rule-based cues, spaCy dependencies, and optional coreference/LLM hooks.
- Returns `(speaker, method, confidence)` for a span.

Implementation: [`attribute.py`](../../../src/abm/annotate/attribute.py).

## 5. LLM Refinement (Optional)

### Candidate Preparation

```python
from abm.annotate.llm_prep import LLMCandidatePreparer

prep = LLMCandidatePreparer()
cands = prep.prepare(tagged_doc)
```

### Consensus Refinement

```python
from abm.annotate.llm_refine import LLMRefiner

ref = LLMRefiner()
ref.refine(Path("chapters_tagged.json"), Path("spans_for_llm.jsonl"), Path("chapters_tagged_refined.json"))
```

Features:

- Selects low-confidence dialogue/thought spans with context windows and roster info.
- Calls a local OpenAI-compatible endpoint with multiple prompt variants and caches results.
- Accepts only improvements that beat the baseline confidence by a configurable margin.

Modules: [`llm_prep.py`](../../../src/abm/annotate/llm_prep.py), [`llm_refine.py`](../../../src/abm/annotate/llm_refine.py).

## 6. Review Generation

```python
from abm.annotate.review import make_review_markdown

markdown = make_review_markdown(tagged_doc["chapters"])
```

Provides:

- Per-chapter tables of the lowest-confidence spans.
- Global span table and method-level breakdown for quick QA.

See [`review.py`](../../../src/abm/annotate/review.py).

## 7. CLI Runner

```bash
python -m abm.annotate.annotate_cli --in chapters.json --out-json chapters_tagged.json --out-md chapters_review.md
```

`AnnotateRunner` orchestrates normalization → segmentation → roster building → attribution and writes both JSON and review Markdown files.

Entry module: [`annotate_cli.py`](../../../src/abm/annotate/annotate_cli.py).

---

*Part of [Implementation](../README.md)*
