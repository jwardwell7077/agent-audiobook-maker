"""High level orchestrator to package rendered chapters into final formats."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable
from pathlib import Path

from abm.audio.book_config import load_book_meta
from abm.audio.packaging import export_mp3, export_opus, format_ts

__all__ = ["package_book", "main"]

logger = logging.getLogger(__name__)


def _discover_wavs(root: Path) -> list[Path]:
    """Return sorted chapter WAV files under ``root``."""

    return sorted(root.glob("ch_*.wav"))


def package_book(
    renders_dir: Path, meta_path: Path, out_dir: Path, formats: Iterable[str]
) -> list[Path]:
    """Package chapter WAVs into selected formats.

    Args:
        renders_dir: Directory containing ``ch_*.wav`` files.
        meta_path: Path to book metadata YAML.
        out_dir: Destination directory for packaged outputs.
        formats: Iterable of requested formats (e.g., ``{"mp3", "opus"}``).

    Returns:
        List of paths that were successfully written.
    """

    meta = load_book_meta(meta_path)
    wavs = _discover_wavs(renders_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for idx, wav in enumerate(wavs, start=1):
        title = f"Chapter {idx}"
        if "mp3" in formats:
            dest = out_dir / f"{wav.stem}.mp3"
            try:
                export_mp3(
                    wav,
                    dest,
                    title=title,
                    artist=meta.author,
                    album=meta.title,
                    track=idx,
                )
                produced.append(dest)
            except RuntimeError as exc:  # pragma: no cover - ffmpeg missing
                logger.warning("Skipping MP3 for %s: %s", wav.name, exc)
        if "opus" in formats:
            dest = out_dir / f"{wav.stem}.opus"
            try:
                export_opus(
                    wav,
                    dest,
                    title=title,
                    artist=meta.author,
                    album=meta.title,
                    track=idx,
                )
                produced.append(dest)
            except RuntimeError as exc:  # pragma: no cover - ffmpeg missing
                logger.warning("Skipping Opus for %s: %s", wav.name, exc)
        chap = out_dir / f"{wav.stem}.chapters.txt"
        chap.write_text(f"{format_ts(0.0)} {title}\n", encoding="utf-8")
        produced.append(chap)
    return produced


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for packaging chapters."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renders-dir", type=Path, required=True)
    parser.add_argument("--book-meta", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--formats", type=str, default="mp3,opus")
    args = parser.parse_args(argv)
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    produced = package_book(args.renders_dir, args.book_meta, args.out_dir, formats)
    logger.info("packaged %d files", len(produced))
