"""Command line interface for :mod:`abm.audit`."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from .metrics_eval import compute_basic_metrics, load_doc
from .vote_metrics import parse_metrics_jsonl
from .speaker_confusion import compute_confusion
from . import plots
from .report_md import render_markdown
from .report_html import md_to_html


def _first_glob(pattern: str) -> Path | None:
    paths = sorted(Path().glob(pattern))
    return paths[0] if paths else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refined", type=Path, default=None)
    ap.add_argument("--base", type=Path, default=None)
    ap.add_argument("--metrics-jsonl", type=Path, default=None)
    ap.add_argument("--chapters", type=int, default=25)
    ap.add_argument("--plots", action="store_true")
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--prefix", default=f"overnight_eval_{date.today():%Y-%m-%d}")
    ap.add_argument("--out-dir", type=Path, default=Path("reports"))
    ap.add_argument("--title", default="Evaluation Report")
    ap.add_argument("--stdout-summary", action="store_true")
    args = ap.parse_args(argv)

    if args.refined is None:
        args.refined = _first_glob("data/ann/*/combined_refined.json")
    if args.base is None:
        args.base = _first_glob("data/ann/*/combined.json")
    if args.metrics_jsonl is None:
        args.metrics_jsonl = _first_glob("data/ann/*/llm_metrics.jsonl")
    if args.refined is None:
        raise SystemExit("refined annotations not found")

    refined_doc = load_doc(args.refined)
    base_doc = load_doc(args.base) if args.base and args.base.exists() else None
    summary = compute_basic_metrics(refined_doc, base_doc, args.chapters)

    vote = None
    if args.metrics_jsonl and args.metrics_jsonl.exists():
        vote = parse_metrics_jsonl(args.metrics_jsonl)

    conf = None
    if base_doc is not None:
        conf = compute_confusion(base_doc, refined_doc)

    out_dir = args.out_dir
    prefix = args.prefix
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{prefix}.md"
    assets_dir = out_dir / prefix
    assets_dir.mkdir(parents=True, exist_ok=True)

    if args.plots:
        plots.plot_top_speakers(Counter(dict(summary["top_speakers"])), assets_dir / "top_speakers.png")
        plots.plot_unknown_by_chapter(summary["chapters"], assets_dir / "unknown_by_chapter.png")
        if vote:
            plots.plot_vote_margin_hist(vote["vote_margins"], assets_dir / "vote_margin_hist.png")

    render_markdown(summary, vote, conf, md_path, assets_dir.relative_to(out_dir), args.title)
    if args.html:
        md_to_html(md_path, out_dir / f"{prefix}.html")

    json_path = out_dir / f"{prefix}.json"
    json_path.write_text(json.dumps({"summary": summary, "vote": vote, "confusion": conf}, indent=2))

    if args.stdout_summary:
        line = f"Unknown {summary['unknown_rate']*100:.1f}%"
        if vote:
            line += f" | cache {vote['cache_hit_rate']*100:.1f}% | median {vote['median_margin'] or 0:.2f}"
        print(line)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
