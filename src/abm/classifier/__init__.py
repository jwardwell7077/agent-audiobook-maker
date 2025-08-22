"""Section Classifier package.

Contract-first: produces four artifacts:
- front_matter
- toc
- chapters_section
- back_matter
"""

from abm.classifier.section_classifier import classify_sections
from abm.classifier.types import (
    TOC,
    BackMatter,
    ChaptersSection,
    ClassifierInputs,
    ClassifierOutputs,
    FrontMatter,
)

__all__ = [
    "ClassifierInputs",
    "FrontMatter",
    "TOC",
    "ChaptersSection",
    "BackMatter",
    "ClassifierOutputs",
    "classify_sections",
]
