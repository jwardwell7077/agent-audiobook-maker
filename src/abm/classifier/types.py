"""Type definitions for the Section Classifier.

These are minimal runtime types to document inputs/outputs for the
contract-first API. They mirror the docs in
`docs/SECTION_CLASSIFIER_SPEC.md` and JSON Schemas in
`docs/schemas/classifier/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict


class PageMarker(TypedDict):
    """Location of a detected page number in the continuous text buffer."""

    page_index: int
    line_index_global: int
    value: str


class DocumentMeta(TypedDict):
    """Document-level metadata captured by the classifier."""

    page_markers: list[PageMarker]


class TOCEntry(TypedDict):
    """A single Table of Contents entry."""

    title: str
    page: int
    raw: str
    line_in_toc: int


class PerPageLabel(TypedDict):
    """Label assigned to a page with a confidence score."""

    page_index: int
    label: Literal["front", "toc", "body", "back"]
    confidence: float


class FrontMatter(TypedDict):
    """Front matter section artifact."""

    span: list[int]
    text_sha256: str
    warnings: list[str]
    document_meta: DocumentMeta


class TOC(TypedDict):
    """Table of Contents artifact."""

    span: list[int]
    entries: list[TOCEntry]
    warnings: list[str]


class ChaptersSection(TypedDict):
    """Body chapters region labeling artifact."""

    span: list[int]
    per_page_labels: list[PerPageLabel]
    warnings: list[str]


class BackMatter(TypedDict):
    """Back matter section artifact."""

    span: list[int]
    text_sha256: str
    warnings: list[str]


class ClassifierOutputs(TypedDict):
    """Group of all four classifier artifacts."""

    front_matter: FrontMatter
    toc: TOC
    chapters_section: ChaptersSection
    back_matter: BackMatter


@dataclass(slots=True)
class Page:
    """A single input page providing its index and text lines."""

    page_index: int
    lines: list[str]


class ClassifierInputs(TypedDict):
    """Inputs required by the section classifier."""

    pages: list[Page]
