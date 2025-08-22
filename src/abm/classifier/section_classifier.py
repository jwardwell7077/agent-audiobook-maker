"""Minimal, deterministic Section Classifier stub.

This provides a contract-satisfying function `classify_sections` that
constructs placeholder artifacts with empty/warning-only content. It lets
us wire up APIs and tests before heuristics are implemented.

See docs/SECTION_CLASSIFIER_SPEC.md for details.
"""

from __future__ import annotations

from hashlib import sha256

from abm.classifier.types import (
    TOC,
    BackMatter,
    ChaptersSection,
    ClassifierInputs,
    ClassifierOutputs,
    DocumentMeta,
    FrontMatter,
    Page,
    PerPageLabel,
)


def _concat_pages(pages: list[Page]) -> list[str]:
    """Concatenate page lines into a continuous list of lines.

    Page-number-only removal is not handled here in the stub; that logic will
    be implemented in a future slice. For now, we return all lines.
    """
    all_lines: list[str] = []
    for p in pages:
        all_lines.extend(p.lines)
    return all_lines


def classify_sections(inputs: ClassifierInputs) -> ClassifierOutputs:
    """Classify book sections and return four artifacts.

        This stub returns deterministic, minimal artifacts:
        - span values cover the entire concatenated text (0..N chars) based on
            joined lines.
    - text_sha256 is computed from the joined text for front/back placeholders.
    - toc contains no entries.
    - per_page_labels marks all pages as "body" with confidence 0.0.
    - warnings explain that this is a stub.
    """

    pages = inputs.get("pages", [])
    all_lines = _concat_pages(pages)
    joined = "\n".join(all_lines)
    text_hash = sha256(joined.encode("utf-8")).hexdigest()

    span = [0, len(joined)]

    document_meta: DocumentMeta = {"page_markers": []}

    front: FrontMatter = {
        "span": span,
        "text_sha256": text_hash,
        "warnings": [
            "stub: page-number-only removal not applied; using raw text",
        ],
        "document_meta": document_meta,
    }

    toc: TOC = {
        "span": span,
        "entries": [],
        "warnings": ["stub: no toc entries"],
    }

    per_page: list[PerPageLabel] = [
        {"page_index": p.page_index, "label": "body", "confidence": 0.0}
        for p in pages
    ]
    chapters_section: ChaptersSection = {
        "span": span,
        "per_page_labels": per_page,
        "warnings": ["stub: all pages labeled body with 0.0 confidence"],
    }

    back: BackMatter = {
        "span": span,
        "text_sha256": text_hash,
        "warnings": ["stub: identical to front for placeholder"],
    }

    return {
        "front_matter": front,
        "toc": toc,
        "chapters_section": chapters_section,
        "back_matter": back,
    }
