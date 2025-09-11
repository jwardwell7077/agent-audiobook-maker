"""Generate Markdown review reports for annotated chapters."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass
class ReviewConfig:
    """Configuration for review report formatting."""

    max_text_len: int = 160
    include_chapter_headers: bool = True
    include_normalize_summary: bool = True
    show_method_breakdown: bool = True
    show_unknown_first: bool = True


class Reviewer:
    """Build a Markdown review report from annotated chapters."""

    def __init__(self, config: ReviewConfig | None = None) -> None:
        self.cfg = config or ReviewConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def make_markdown(self, chapters: list[dict[str, Any]]) -> str:
        """Return a Markdown report for human QA."""

        lines: list[str] = []

        flat: list[tuple[float, int, dict[str, Any]]] = [
            (float(s.get("confidence", 0.0)), int(ch.get("chapter_index", ci)), s)
            for ci, ch in enumerate(chapters)
            for s in ch.get("spans", [])
        ]

        if self.cfg.show_unknown_first:
            flat.sort(key=lambda row: (row[2].get("speaker") != "Unknown", row[0], row[1]))
        else:
            flat.sort(key=lambda row: (row[0], row[1]))

        if self.cfg.include_chapter_headers:
            per_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for _conf, ci, span in flat:
                per_chapter[ci].append(span)

            for ci in sorted(per_chapter.keys()):
                ch = chapters[ci] if ci < len(chapters) else None
                lines.extend(self._chapter_header(ch))
                lines.extend(self._chapter_summary_table(per_chapter[ci]))

        lines.append("")
        lines.append("## All spans (lowest confidence first)")
        lines.extend(self._spans_table(flat))

        if self.cfg.show_method_breakdown:
            lines.append("")
            lines.append("## Method breakdown")
            lines.extend(self._method_breakdown(chapters))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _chapter_header(self, ch: dict[str, Any] | None) -> list[str]:
        """Create a header for a single chapter including normalize summary."""

        if not ch:
            return []
        idx = ch.get("chapter_index", "?")
        title = ch.get("title", "")
        display = ch.get("display_title", title) or ""
        lines: list[str] = [f"\n# Chapter {idx}: {display}"]

        if self.cfg.include_normalize_summary:
            report = dict(ch.get("normalize_report") or {})
            counts = dict(report.get("counts") or {})
            details = " • ".join(
                f"{k}: {counts.get(k, 0)}" for k in ["SystemAngle", "SystemSquare", "SectionBreak", "Meta"]
            )
            is_heading = "yes" if report.get("is_heading") else "no"
            lines.append(f"*normalize:* heading: **{is_heading}** • {details}")

        return lines

    def _chapter_summary_table(self, spans: list[dict[str, Any]]) -> list[str]:
        """Per-chapter compact table showing the worst offenders first."""

        if not spans:
            return []

        rows = sorted(spans, key=lambda s: (s.get("speaker") != "Unknown", float(s.get("confidence", 0.0))))

        out: list[str] = [
            "",
            "| # | Type | Speaker | Conf | Method | Text |",
            "|-:|:--:|:--|--:|:--|:--|",
        ]

        for i, s in enumerate(rows, 1):
            text = (s.get("text") or "").replace("\n", " ")
            if len(text) > self.cfg.max_text_len:
                text = f"{text[: self.cfg.max_text_len - 3]}..."
            out.append(
                f"| {i} | {s.get('type')} | {s.get('speaker')} | "
                f"{float(s.get('confidence', 0.0)):.2f} | {s.get('method')} | {text} |"
            )
        return out

    def _spans_table(self, flat: list[tuple[float, int, dict[str, Any]]]) -> list[str]:
        """Global table of spans across chapters, sorted by confidence asc."""

        out: list[str] = [
            "",
            "| Ch | # | Type | Speaker | Conf | Method | Text |",
            "|-:|--:|:--:|:--|--:|:--|:--|",
        ]
        for _conf, ci, s in flat:
            text = (s.get("text") or "").replace("\n", " ")
            if len(text) > self.cfg.max_text_len:
                text = f"{text[: self.cfg.max_text_len - 3]}..."
            out.append(
                f"| {ci} | {s.get('id')} | {s.get('type')} | {s.get('speaker')} | "
                f"{float(s.get('confidence', 0.0)):.2f} | {s.get('method')} | {text} |"
            )
        return out

    def _method_breakdown(self, chapters: list[dict[str, Any]]) -> list[str]:
        """Create a breakdown of methods and average confidences."""

        methods: Counter[str] = Counter()
        confs: dict[str, list[float]] = defaultdict(list)

        for ch in chapters:
            for s in ch.get("spans", []):
                m = str(s.get("method", ""))
                c = float(s.get("confidence", 0.0))
                if m:
                    methods[m] += 1
                    confs[m].append(c)

        out: list[str] = ["", "| Method | Count | Avg Conf |", "|:--|--:|--:|"]
        for m, cnt in methods.most_common():
            avg = mean(confs[m]) if confs[m] else 0.0
            out.append(f"| {m} | {cnt} | {avg:.2f} |")
        return out


# ---------------------------------------------------------------------------
# Backwards-compatible functional wrapper
# ---------------------------------------------------------------------------


def make_review_markdown(chapters: list[dict[str, Any]]) -> str:
    """Functional wrapper used by :mod:`annotate_cli` to emit a report."""

    return Reviewer().make_markdown(chapters)

