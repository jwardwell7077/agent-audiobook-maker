"""Optional plotting helpers for :mod:`abm.audit`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

try:  # pragma: no cover - optional dependency
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - matplotlib may be missing
    plt = None  # type: ignore


def _maybe_save(fig, out_png: Path) -> None:
    if plt is None:
        return
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)


def plot_top_speakers(counter: Counter[str], out_png: Path) -> None:
    if plt is None:
        return
    items = counter.most_common(10)
    if not items:
        return
    labels, counts = zip(*items)
    fig, ax = plt.subplots()
    ax.bar(labels, counts)
    ax.set_ylabel("Spans")
    ax.set_title("Top speakers")
    ax.tick_params(axis="x", rotation=45)
    _maybe_save(fig, out_png)


def plot_unknown_by_chapter(rows, out_png: Path) -> None:
    if plt is None:
        return
    if not rows:
        return
    labels = [r["title"] for r in rows]
    vals = [r["unknown_rate"] * 100 for r in rows]
    fig, ax = plt.subplots()
    ax.bar(range(len(labels)), vals)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90)
    ax.set_ylabel("Unknown %")
    ax.set_title("Unknown by chapter")
    _maybe_save(fig, out_png)


def plot_vote_margin_hist(margins, out_png: Path) -> None:
    if plt is None or not margins:
        return
    fig, ax = plt.subplots()
    ax.hist(margins, bins=20)
    ax.set_xlabel("Vote margin")
    ax.set_ylabel("Count")
    ax.set_title("Vote margin distribution")
    _maybe_save(fig, out_png)
