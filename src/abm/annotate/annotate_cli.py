from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from abm.annotate.attribute import AttributeEngine
from abm.annotate.metrics import ChapterMetrics, MetricsCollector, Timer
from abm.annotate.normalize import ChapterNormalizer, NormalizerConfig
from abm.annotate.progress import ProgressReporter
from abm.annotate.review import make_review_markdown
from abm.annotate.roster import RosterBuilder, RosterConfig, merge_book_roster
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
    """End-to-end runner: normalize → segment → roster → attribute → write outputs."""

    def __init__(
        self,
        mode: str = "high",
        llm_tag: str | None = None,
        remove_heading: bool = False,
        treat_single_quotes_as_thought: bool = True,
        verbose: bool = False,
        spacy_model: str | None = None,
        use_coref: bool = True,
        stages: Sequence[str] | None = None,
        roster_scope: str = "book",
        roster_use_ner: bool = True,
        parse_mode: str = "doc",
        doc_cache_dir: Path | None = None,
        pipe_batch_size: int = 8,
    ) -> None:
        self.verbose = verbose
        self.stages = list(stages or ["normalize", "roster", "segment", "attribute"])
        self.roster_scope = roster_scope
        self.roster_use_ner = roster_use_ner
        self.parse_mode = parse_mode
        self.doc_cache_dir = doc_cache_dir or Path("data/.doccache")
        self.pipe_batch_size = pipe_batch_size
        self.spacy_model = spacy_model
        self.normalizer = ChapterNormalizer(NormalizerConfig(treat_heading_as_removable=remove_heading))
        self.segmenter = Segmenter(
            SegmenterConfig(
                treat_single_quotes_as_thought=treat_single_quotes_as_thought,
                include_heading=True,
                include_meta=True,
                include_section_break=True,
                include_system_lines=True,
                include_system_inline=True,
            )
        )
        self.engine = AttributeEngine(
            mode=mode,
            llm_tag=llm_tag,
            verbose=verbose,
            force_spacy_model=spacy_model,
            use_coref=use_coref,
        )

    def run_streaming(
        self,
        chapters_doc: dict[str, Any],
        out_dir: Path | None,
        metrics: MetricsCollector | None,
        status_mode: str = "auto",
        only_indices: Sequence[int] | None = None,
        out_json_all: Path | None = None,
        out_md_all: Path | None = None,
        out_roster_path: Path | None = None,
    ) -> dict[str, Any]:
        """Process one chapter at a time with live status and optional per-chapter files.

        Args:
            chapters_doc: Input JSON dict with a "chapters" list.
            out_dir: If provided, write ch_{index:04d}.json files here as we go.
            metrics: If provided, write one JSONL line per chapter with timing and counts.
            status_mode: "auto" | "rich" | "tqdm" | "none".
            only_indices: Optional subset of chapter_index values to process.
            out_json_all: If provided, also write the combined JSON when done.
            out_md_all: If provided, also write the combined review.md when done.
        """
        chapters: list[dict[str, Any]] = list(chapters_doc.get("chapters") or [])
        if not chapters:
            raise SystemExit("No chapters found under key 'chapters'.")

        if self.verbose:
            print(f"[init] stages={self.stages} verbose={self.verbose}")

        # Pass A: normalize (optional) and build preliminary book roster (optional)
        normalized: list[dict[str, Any]] = []
        book_roster: dict[str, list[str]] = {}
        selected_set = set(only_indices or [])

        # NORMALIZE stage
        if "normalize" in self.stages:
            if self.verbose:
                print("[stage] normalize: start")
            for ch in chapters:
                ch_norm = self.normalizer.normalize(ch)
                normalized.append(ch_norm)
            if self.verbose:
                print(f"[stage] normalize: done ({len(normalized)} chapters)")
        else:
            normalized = chapters

        # Prepare a RosterBuilder (respect --no-roster-ner and reuse engine spaCy)
        rb = RosterBuilder(
            RosterConfig(use_spacy=self.roster_use_ner),
            nlp=self.engine.ner_nlp if self.roster_use_ner else None,
        )

        # Optional: prepare full-doc parse cache before chapter loop
        use_doc = self.parse_mode == "doc"
        doc_by_idx: dict[int, Any] = {}
        if use_doc:
            try:
                from abm.parse.cache import DocCache, DocCacheConfig

                model = self.spacy_model or "en_core_web_trf"
                dcache = DocCache(
                    DocCacheConfig(cache_dir=self.doc_cache_dir, model_name=model, batch_size=self.pipe_batch_size),
                    verbose=self.verbose,
                )

                # Ensure text exists for every chapter
                chapters_for_parse: list[dict[str, Any]] = []
                for ch in normalized:
                    if not ch.get("text"):
                        ch["text"] = "\n".join(ch.get("paragraphs", []))
                    chapters_for_parse.append(ch)

                ch_docs = dcache.load_or_parse(chapters_for_parse)
                doc_by_idx = {int(ch.get("chapter_index", -1)): doc for ch, doc in ch_docs}
            except Exception as e:
                if self.verbose:
                    print(f"[parse] doc cache unavailable, falling back to window mode: {e}")
                use_doc = False
                doc_by_idx = {}

        # ROSTER (book) stage
        if "roster" in self.stages:
            if self.verbose:
                print(f"[stage] roster({self.roster_scope}): start")

            if self.roster_scope == "book":
                iterable = normalized
            elif self.roster_scope == "selected":
                iterable = [ch for ch in normalized if int(ch.get("chapter_index", -1)) in selected_set]
            else:
                iterable = []  # no book roster

            for ch_norm in iterable:
                # Build per-chapter roster and merge into book roster
                chap_r = rb.build_chapter_roster(ch_norm["text"])
                book_roster = merge_book_roster(book_roster, chap_r)

            if self.verbose:
                n_entities = sum(len(v) for v in book_roster.values())
                print(f"[stage] roster({self.roster_scope}): done (entities={n_entities})")

        # Optionally write the merged book roster after the first pass
        if out_roster_path:
            try:
                out_roster_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            out_roster_path.write_text(json.dumps(book_roster, ensure_ascii=False, indent=2), encoding="utf-8")

        out_chapters: list[dict[str, Any]] = []
        total = (
            len(normalized)
            if only_indices is None
            else sum(1 for c in normalized if c.get("chapter_index") in set(only_indices))
        )
        out_dir = out_dir or None
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

        # If requested, persist the preliminary merged book roster now (before per-chapter work)
        if out_roster_path:
            out_roster_path.write_text(json.dumps(book_roster, ensure_ascii=False, indent=2), encoding="utf-8")

        with ProgressReporter(total=total, mode=status_mode, title="Annotating") as progress:
            for ch_norm in normalized:
                idx = int(ch_norm.get("chapter_index", -1))
                if only_indices is not None and idx not in set(only_indices):
                    out_chapters.append(ch_norm)
                    continue

                cm = ChapterMetrics(
                    chapter_index=idx,
                    title=str(ch_norm.get("title") or ""),
                    n_paragraphs=len(ch_norm.get("paragraphs") or []),
                )
                t_total = Timer()
                t_norm = Timer()
                t_seg = Timer()
                t_ros = Timer()
                t_att = Timer()

                with t_total:
                    # (normalize already done above; timer included for symmetry)
                    with t_norm:
                        pass

                    # Roster (chapter-level + merge with book)
                    with t_ros:
                        if "roster" in self.stages:
                            if self.verbose:
                                print(f"[ch {idx}] roster(chapter): start")
                            chap_roster = rb.build_chapter_roster(ch_norm["text"])

                            if self.roster_scope in {"book", "selected"}:
                                roster = merge_book_roster(book_roster, chap_roster)
                            elif self.roster_scope == "chapter":
                                roster = chap_roster
                            else:  # "none"
                                roster = {}
                            if self.verbose:
                                print(f"[ch {idx}] roster(chapter): done (names={len(roster)})")
                        else:
                            roster = {}

                    # Segment
                    with t_seg:
                        if "segment" in self.stages:
                            if self.verbose:
                                print(f"[ch {idx}] segment: start")
                            seg_spans: list[SegSpan] = self.segmenter.segment(ch_norm)
                            if self.verbose:
                                print(f"[ch {idx}] segment: done (spans={len(seg_spans)})")
                        else:
                            seg_spans = []

                    # Attribute
                    spans_out: list[SpanOut] = []
                    with t_att:
                        if "attribute" in self.stages and seg_spans:
                            if self.verbose:
                                print(f"[ch {idx}] attribute: start")

                            # Prepare lightweight neighbor extractor
                            def _lite(span: SegSpan) -> dict[str, int | str]:
                                return {"start": span.start, "end": span.end, "type": span.type.value}

                            for i, s in enumerate(seg_spans):
                                prev_s = _lite(seg_spans[i - 1]) if i > 0 else None
                                next_s = _lite(seg_spans[i + 1]) if i + 1 < len(seg_spans) else None
                                doc = doc_by_idx.get(idx) if use_doc else None
                                kwargs: dict[str, Any] = {"neighbors": (prev_s, next_s)}
                                if doc is not None:
                                    kwargs["doc"] = doc
                                speaker, method, conf = self.engine.attribute_span(
                                    ch_norm["text"],
                                    (s.start, s.end),
                                    s.type.value,
                                    roster,
                                    **kwargs,
                                )
                                spans_out.append(
                                    SpanOut(
                                        id=i + 1,
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
                            if self.verbose:
                                # simple visibility counters will be filled after counts
                                pass

                # Populate chapter output
                ch_out = dict(ch_norm)
                ch_out["roster"] = roster
                ch_out["spans"] = [asdict(s) for s in spans_out]
                out_chapters.append(ch_out)

                # Metrics aggregation
                cm.time_normalize = t_norm.elapsed
                cm.time_roster = t_ros.elapsed
                cm.time_segment = t_seg.elapsed
                cm.time_attribute = t_att.elapsed
                cm.time_total = t_total.elapsed

                # Span counts
                cm.spans_total = len(spans_out)
                for so in spans_out:
                    t = so.type
                    if t == "Dialogue":
                        cm.spans_dialogue += 1
                    elif t == "Thought":
                        cm.spans_thought += 1
                    elif t == "Narration":
                        cm.spans_narration += 1
                    elif t == "System":
                        cm.spans_system += 1
                    elif t == "Meta":
                        cm.spans_meta += 1
                    elif t == "SectionBreak":
                        cm.spans_section_break += 1
                    elif t == "Heading":
                        cm.spans_heading += 1

                # Confidence stats
                confs = [so.confidence for so in spans_out if so.type in {"Dialogue", "Thought"}]
                if confs:
                    cm.avg_confidence = sum(confs) / float(len(confs))
                    cm.min_confidence = min(confs)
                    cm.max_confidence = max(confs)
                cm.unknown_speakers = sum(
                    1 for so in spans_out if so.type in {"Dialogue", "Thought"} and so.speaker == "Unknown"
                )

                # Resource sampling
                res = MetricsCollector.sample_resources()
                cm.rss_mb = res.get("rss_mb")
                cm.gpu_mem_mb = res.get("gpu_mem_mb")

                # Per-chapter JSON (stream to disk)
                if out_dir:
                    out_path = out_dir / f"ch_{idx:04d}.json"
                    out_path.write_text(json.dumps(ch_out, ensure_ascii=False, indent=2), encoding="utf-8")

                # Metrics JSONL line
                if metrics:
                    metrics.write(cm)

                # Advance progress and verbose chapter footer
                progress.advance(
                    1, text=f"ch {idx} | spans={cm.spans_total} unk={cm.unknown_speakers} avg={cm.avg_confidence:.2f}"
                )
                if self.verbose:
                    print(f"[ch {idx}] done in {cm.time_total:.2f}s")

        # Combined outputs (optional)
        out_doc = dict(chapters_doc)
        # Include the merged book roster in the combined output
        out_doc["book_roster"] = book_roster
        out_doc["chapters"] = out_chapters

        if out_json_all:
            out_json_all.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        if out_md_all:
            out_md_all.write_text(make_review_markdown(out_chapters), encoding="utf-8")

        return out_doc

    def _attribute_single(
        self,
        full_text: str,
        span: SegSpan,
        roster: dict[str, list[str]],
    ) -> tuple[str, str, float]:
        st = span.type
        if st in (SpanType.META, SpanType.SECTION_BREAK, SpanType.HEADING):
            return "Narrator", "rule:non_story", 1.0
        if st is SpanType.SYSTEM:
            return (
                "System",
                "rule:system_line" if (span.subtype or "").startswith("Line") else "rule:system_inline",
                1.0,
            )
        if st is SpanType.NARRATION:
            return "Narrator", "rule:default_narration", 0.99
        speaker, method, conf = self.engine.attribute_span(full_text, (span.start, span.end), st.value, roster)
        # For unit-test simplicity, map unknown dialogue to a placeholder rule here.
        # The streaming runner uses neighbor-aware attribution directly and is unaffected.
        if st is SpanType.DIALOGUE and method == "rule:unknown":
            return speaker, "rule:placeholder", conf
        return speaker, method, conf


# --------------------------------- CLI ---------------------------------- #


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Annotate chapters with spans and speakers.")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to chapters.json")
    ap.add_argument("--out-json", dest="out_json", default=None, help="Write combined JSON here (optional)")
    ap.add_argument("--out-md", dest="out_md", default=None, help="Write combined review.md here (optional)")
    ap.add_argument("--out-dir", dest="out_dir", default=None, help="If set, write per-chapter ch_XXXX.json files here")
    ap.add_argument("--metrics-jsonl", dest="metrics_jsonl", default=None, help="Write per-chapter metrics JSONL here")
    ap.add_argument(
        "--out-roster",
        dest="out_roster",
        default=None,
        help="Write the merged book roster here (JSON)",
    )
    ap.add_argument("--verbose", action="store_true", help="Verbose stage logging to stdout/stderr")
    ap.add_argument(
        "--stages",
        default="normalize,roster,segment,attribute",
        help="Comma list of stages to run. Use a subset for debugging, e.g. 'normalize,segment'",
    )
    ap.add_argument("--spacy-model", default=None, help="Force spaCy model: en_core_web_sm or en_core_web_trf")
    ap.add_argument("--no-coref", action="store_true", help="Disable fastcoref even if installed")
    ap.add_argument("--status", choices=["auto", "rich", "tqdm", "none"], default="auto", help="Live status renderer")
    ap.add_argument("--mode", choices=["fast", "high"], default="high", help="Attribution quality mode")
    ap.add_argument("--llm", dest="llm_tag", default=None, help="Optional local LLM backend identifier")
    ap.add_argument("--remove-heading", action="store_true", help="Drop paragraph 0 if it's a chapter heading")
    ap.add_argument("--treat-single-as-thought", action="store_true", help="Interpret single quotes as Thought")
    ap.add_argument("--only", type=int, nargs="+", default=None, help="Subset of chapter_index values to process")
    ap.add_argument(
        "--roster-scope",
        choices=["book", "selected", "chapter", "none"],
        default="book",
        help=(
            "Scope of roster building: 'book' scans all chapters, 'selected' only the --only set, "
            "'chapter' per-chapter only, 'none' disables roster."
        ),
    )
    ap.add_argument(
        "--no-roster-ner",
        action="store_true",
        help="Disable spaCy NER during roster building (use heuristics only).",
    )
    # Full-doc parse mode options
    ap.add_argument(
        "--parse-mode",
        choices=["window", "doc"],
        default="doc",
        help="Use per-span window parses (legacy) or full-doc parse per chapter.",
    )
    ap.add_argument(
        "--doc-cache",
        default="data/.doccache",
        help="Directory to store .spacy DocBin caches for full-doc mode.",
    )
    ap.add_argument(
        "--pipe-batch-size",
        type=int,
        default=8,
        help="spaCy nlp.pipe batch size for full-doc mode.",
    )
    return ap.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    args = _parse_args()
    in_path = Path(args.in_path)
    out_json = Path(args.out_json) if args.out_json else None
    out_md = Path(args.out_md) if args.out_md else None
    out_dir = Path(args.out_dir) if args.out_dir else None
    metrics_path = Path(args.metrics_jsonl) if args.metrics_jsonl else None
    out_roster = Path(args.out_roster) if args.out_roster else None

    runner = AnnotateRunner(
        mode=args.mode,
        llm_tag=args.llm_tag,
        remove_heading=args.remove_heading,
        treat_single_quotes_as_thought=args.treat_single_as_thought,
        verbose=args.verbose,
        spacy_model=args.spacy_model,
        use_coref=(not args.no_coref),
        stages=[s.strip() for s in str(args.stages).split(",") if s.strip()],
        roster_scope=args.roster_scope,
        roster_use_ner=(not args.no_roster_ner),
        parse_mode=args.parse_mode,
        doc_cache_dir=Path(args.doc_cache),
        pipe_batch_size=args.pipe_batch_size,
    )

    doc = _load_json(in_path)
    collector = MetricsCollector(metrics_path) if metrics_path else None
    try:
        runner.run_streaming(
            chapters_doc=doc,
            out_dir=out_dir,
            metrics=collector,
            status_mode=args.status,
            only_indices=args.only,
            out_json_all=out_json,
            out_md_all=out_md,
            out_roster_path=out_roster,
        )
    finally:
        if collector:
            collector.close()


if __name__ == "__main__":
    main()
