"""Command-line interface for chapter annotation.

This CLI normalizes chapters, segments them into spans, builds simple speaker
rosters, runs attribution, and writes output artifacts for review. The
implementation is intentionally lightweight and relies on placeholder
components for attribution and roster building.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from abm.annotate.attribute import AttributeEngine
from abm.annotate.normalize import ChapterNormalizer, NormalizerConfig
from abm.annotate.review import make_review_markdown
from abm.annotate.roster import build_chapter_roster, merge_book_roster
from abm.annotate.segment import Segmenter, SegmenterConfig, SpanType
from abm.annotate.segment import Span as SegSpan


@dataclass
class SpanOut:
    """Serializable span object enriched with attribution fields."""

    id: int
    type: str
    speaker: str
    start: int
    end: int
    text: str
    method: str
    confidence: float
    para_index: int
    subtype: str | None = None
    notes: str | None = None


class AnnotateRunner:
    """End-to-end runner tying together normalization, segmentation, and attribution."""

    def __init__(
        self,
        mode: str = "high",
        llm_tag: str | None = None,
        remove_heading: bool = False,
        treat_single_quotes_as_thought: bool = True,
    ) -> None:
        """Initialize the runner and its components."""
        self.normalizer = ChapterNormalizer(
            NormalizerConfig(treat_heading_as_removable=remove_heading)
        )
        self.segmenter = Segmenter(
            SegmenterConfig(treat_single_quotes_as_thought=treat_single_quotes_as_thought)
        )
        self.engine = AttributeEngine(mode=mode, llm_tag=llm_tag)

    def run(
        self,
        chapters_doc: dict[str, Any],
        only_indices: Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Process all chapters in a ``chapters.json`` style document."""
        chapters: list[dict[str, Any]] = list(chapters_doc.get("chapters") or [])
        if not chapters:
            raise SystemExit("No chapters found under key 'chapters'.")

        normalized: list[dict[str, Any]] = []
        book_roster: dict[str, list[str]] = {}
        for ch in chapters:
            ch_norm = self.normalizer.normalize(ch)
            normalized.append(ch_norm)
            book_roster = merge_book_roster(
                book_roster,
                build_chapter_roster(ch_norm["text"], nlp=self.engine.ner_nlp),
            )

        out_chapters: list[dict[str, Any]] = []
        for ch_norm in normalized:
            idx = ch_norm.get("chapter_index")
            if only_indices is not None and idx not in set(only_indices):
                out_chapters.append(ch_norm)
                continue

            chap_roster = build_chapter_roster(ch_norm["text"], nlp=self.engine.ner_nlp)
            roster = merge_book_roster(book_roster, chap_roster)

            seg_spans: list[SegSpan] = self.segmenter.segment(ch_norm)

            spans_out: list[SpanOut] = []
            for i, s in enumerate(seg_spans, start=1):
                speaker, method, conf = self._attribute_single(ch_norm["text"], s, roster)
                spans_out.append(
                    SpanOut(
                        id=i,
                        type=s.type.value,
                        speaker=speaker,
                        start=s.start,
                        end=s.end,
                        text=s.text,
                        method=method,
                        confidence=conf,
                        para_index=s.para_index,
                        subtype=s.subtype,
                        notes=s.notes,
                    )
                )

            ch_out = dict(ch_norm)
            ch_out["roster"] = roster
            ch_out["spans"] = [asdict(s) for s in spans_out]
            out_chapters.append(ch_out)

        out_doc = dict(chapters_doc)
        out_doc["chapters"] = out_chapters
        return out_doc

    def _attribute_single(
        self,
        full_text: str,
        span: SegSpan,
        roster: dict[str, list[str]],
    ) -> tuple[str, str, float]:
        """Attribute a single segmented span."""

        st = span.type
        if st in (SpanType.META, SpanType.SECTION_BREAK, SpanType.HEADING):
            return "Narrator", "rule:non_story", 1.0
        if st is SpanType.SYSTEM:
            rule = "rule:system_line" if (span.subtype or "").startswith("Line") else "rule:system_inline"
            return "System", rule, 1.0
        if st is SpanType.NARRATION:
            return "Narrator", "rule:default_narration", 0.99

        return self.engine.attribute_span(
            full_text,
            (span.start, span.end),
            st.value,
            roster,
        )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    ap = argparse.ArgumentParser(description="Annotate chapters with spans and speakers.")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to chapters.json")
    ap.add_argument("--out-json", dest="out_json", default="chapters_tagged.json", help="Output JSON path")
    ap.add_argument("--out-md", dest="out_md", default="chapters_review.md", help="Review Markdown path")
    ap.add_argument("--mode", choices=["fast", "high"], default="high", help="Attribution quality mode")
    ap.add_argument("--llm", dest="llm_tag", default=None, help="Optional local LLM backend identifier")
    ap.add_argument(
        "--remove-heading",
        action="store_true",
        help="Drop paragraph 0 when it is a chapter heading.",
    )
    ap.add_argument(
        "--treat-single-as-thought",
        action="store_true",
        help="Interpret single-quoted spans ('…') as Thought.",
    )
    ap.add_argument(
        "--only",
        type=int,
        nargs="+",
        default=None,
        help="Subset of chapter_index values to process.",
    )
    return ap.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file into a dictionary."""

    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    """Write a dictionary to a JSON file."""

    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_review(path: Path, chapters: list[dict[str, Any]]) -> None:
    """Write a Markdown review file."""

    md = make_review_markdown(chapters)
    path.write_text(md, encoding="utf-8")


def main() -> None:
    """CLI entrypoint."""

    args = _parse_args()
    in_path = Path(args.in_path)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)

    runner = AnnotateRunner(
        mode=args.mode,
        llm_tag=args.llm_tag,
        remove_heading=args.remove_heading,
        treat_single_quotes_as_thought=args.treat_single_as_thought,
    )

    doc = _load_json(in_path)
    out_doc = runner.run(doc, only_indices=args.only)

    _save_json(out_json, out_doc)
    _save_review(out_md, out_doc["chapters"])
    print(f"Wrote {out_json} and {out_md}")


if __name__ == "__main__":
    main()
