"""Annotation utilities for processing chapters.

This subpackage provides helpers for normalizing chapter text, segmenting it
into labeled spans, and running attribution utilities.
"""

from abm.annotate.annotate_cli import AnnotateRunner
from abm.annotate.attribute import AttributeEngine
from abm.annotate.llm_prep import (
    LLMCandidate,
    LLMCandidateConfig,
    LLMCandidatePreparer,
)
from abm.annotate.llm_refine import LLMRefineConfig, LLMRefiner
from abm.annotate.normalize import (
    ChapterNormalizer,
    InlineTag,
    LineTag,
    NormalizerConfig,
    NormalizeReport,
    normalize_chapter_text,
)
from abm.annotate.review import ReviewConfig, Reviewer, make_review_markdown
from abm.annotate.roster import (
    RosterBuilder,
    RosterConfig,
    build_chapter_roster,
    merge_book_roster,
)
from abm.annotate.segment import Segmenter, SegmenterConfig, Span, SpanType, segment_spans

__all__ = [
    "AttributeEngine",
    "ChapterNormalizer",
    "InlineTag",
    "LineTag",
    "NormalizerConfig",
    "NormalizeReport",
    "AnnotateRunner",
    "build_chapter_roster",
    "merge_book_roster",
    "make_review_markdown",
    "RosterBuilder",
    "RosterConfig",
    "Reviewer",
    "ReviewConfig",
    "normalize_chapter_text",
    "Segmenter",
    "SegmenterConfig",
    "Span",
    "SpanType",
    "segment_spans",
    "LLMCandidate",
    "LLMCandidateConfig",
    "LLMCandidatePreparer",
    "LLMRefineConfig",
    "LLMRefiner",
]
