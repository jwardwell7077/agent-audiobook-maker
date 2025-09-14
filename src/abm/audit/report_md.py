"""Render Markdown audit reports."""

from __future__ import annotations

from pathlib import Path

from .metrics_eval import EvalSummary
from .vote_metrics import VoteStats
from .speaker_confusion import ConfusionSummary


def render_markdown(
    summary: EvalSummary,
    vote: VoteStats | None,
    conf: ConfusionSummary | None,
    out_md: Path,
    assets_prefix_dir: Path | None = None,
    title: str = "Evaluation Report",
) -> None:
    lines: list[str] = [f"# {title}", ""]
    lines.append(f"Generated at: {summary['generated_at']}")
    lines.append("")
    lines.append("## Overview")
    lines.append(
        f"Unknown {summary['unknown_count']}/{summary['total_dialog_thought']} "
        f"({summary['unknown_rate']*100:.1f}%)"
    )
    lines.append("")
    lines.append("### Top speakers")
    lines.append("| Speaker | Count |")
    lines.append("| --- | ---: |")
    for spk, cnt in summary["top_speakers"]:
        lines.append(f"| {spk} | {cnt} |")
    lines.append("")
    lines.append("### Worst chapters")
    lines.append("| Chapter | Unknown/Total | Rate |")
    lines.append("| --- | --- | ---: |")
    for row in summary["worst_chapters"]:
        lines.append(
            f"| {row['title']} | {row['unknown']}/{row['total']} | {row['unknown_rate']*100:.1f}% |"
        )
    lines.append("")

    if assets_prefix_dir:
        lines.append("### Plots")
        for name in [
            "top_speakers.png",
            "unknown_by_chapter.png",
            "vote_margin_hist.png",
        ]:
            path = assets_prefix_dir / name
            if path.exists():
                lines.append(f"![{name}]({path.as_posix()})")
        lines.append("")

    if vote:
        lines.append("## Voting metrics")
        lines.append(
            f"Cache hits: {vote['cache_hits']} / {vote['cache_hits'] + vote['cache_misses']} "
            f"({vote['cache_hit_rate']*100:.1f}%)"
        )
        if vote.get("median_margin") is not None:
            lines.append(f"Median margin: {vote['median_margin']:.2f}")
        if vote.get("weak_cases"):
            lines.append("")
            lines.append("### Weak cases")
            lines.append("| Chapter | Span | Margin | Winner |")
            lines.append("| --- | ---: | ---: | --- |")
            for w in vote["weak_cases"]:
                lines.append(
                    f"| {w.get('title') or w.get('chapter')} | {w.get('span_index')} | "
                    f"{w['margin']:.2f} | {w['winner']} |"
                )
            lines.append("")

    if conf:
        lines.append("## Speaker confusion")
        rate = conf["changes"] / conf["total_compared"] if conf["total_compared"] else 0.0
        lines.append(
            f"Changes: {conf['changes']} / {conf['total_compared']} ({rate*100:.1f}%)"
        )
        if conf["top_pairs"]:
            lines.append("| From | To | Count |")
            lines.append("| --- | --- | ---: |")
            for p in conf["top_pairs"]:
                lines.append(f"| {p['from_speaker']} | {p['to_speaker']} | {p['count']} |")
            lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
