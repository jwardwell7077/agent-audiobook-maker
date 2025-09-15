#!/usr/bin/env python3
"""Album normalize rendered chapters and package deliverables.

This script:
- Reads the book manifest at <renders-dir>/manifests/book_manifest.json
- Computes a single album gain to align median LUFS to the target
- Writes normalized WAVs to <out-dir>/chapters_norm
- Exports MP3/Opus to <out-dir>/(mp3|opus)
- Optionally builds a chaptered M4B using pydub/ffmpeg

Usage:
  python -m scripts.album_normalize_and_package \
    --renders-dir data/renders/mvs_piper_book \
    --book-meta data/book.yaml \
    --out-dir data/packaged/mvs_piper_book \
    --target-lufs -18 \
    --formats mp3,opus \
    --make-m4b

Notes:
- Requires numpy and soundfile for normalization.
- Packaging to MP3/Opus requires ffmpeg; M4B also requires pydub.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

from abm.audio.album_norm import apply_album_gain, compute_album_offset, write_album_manifest
from abm.audio.book_config import load_book_meta
from abm.audio.packaging import export_mp3, export_opus, make_chaptered_m4b

logger = logging.getLogger(__name__)


def _read_manifest(renders_dir: Path) -> dict[str, Any]:
    manifest_path = renders_dir / "manifests" / "book_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data


def _slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "book"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--renders-dir", type=Path, required=True)
    ap.add_argument("--book-meta", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--target-lufs", type=float, default=-18.0)
    ap.add_argument("--trim-percent", type=float, default=None)
    ap.add_argument("--formats", type=str, default="mp3,opus")
    ap.add_argument("--make-m4b", action="store_true")
    ap.add_argument("--log-level", type=str, default="INFO")
    args = ap.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    # Load manifest and meta
    manifest = _read_manifest(args.renders_dir)
    meta = load_book_meta(args.book_meta)
    base_dir = Path(manifest.get("base_dir", args.renders_dir))

    # Compute album gain: resolve QC paths relative to renders root
    stats: list[dict[str, Any]] = []
    for ch in manifest.get("chapters", []):
        qc_rel = Path(ch["qc_path"])  # typically "qc/ch_XXX.qc.json"
        qc_path = args.renders_dir / qc_rel
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        merged = dict(ch)
        merged.update(qc)
        stats.append(merged)
    offset_db = compute_album_offset(stats, target_lufs=args.target_lufs, trim_percent=args.trim_percent)
    logger.info("album offset: %+0.2f dB (target %.1f LUFS)", offset_db, args.target_lufs)

    # Prepare output directories
    out_norm_dir = args.out_dir / "chapters_norm"
    out_mp3_dir = args.out_dir / "mp3"
    out_opus_dir = args.out_dir / "opus"
    out_m4b_dir = args.out_dir / "m4b"
    for d in (out_norm_dir, out_mp3_dir, out_opus_dir, args.out_dir / "manifests"):
        d.mkdir(parents=True, exist_ok=True)

    # Apply gain per chapter
    normalized_wavs: list[Path] = []
    titles: list[str] = []
    for ch in manifest.get("chapters", []):
        wav_rel = Path(ch["wav_path"])  # relative to base_dir
        src_wav = base_dir / wav_rel
        dest_wav = out_norm_dir / wav_rel.name
        titles.append(ch.get("title") or f"Chapter {ch.get('index')}")
        apply_album_gain(src_wav, dest_wav, offset_db)
        normalized_wavs.append(dest_wav)

    # Write album normalization manifest
    write_album_manifest(args.out_dir / "manifests" / "album_norm.json", offset_db)

    # Package per-chapter formats
    want = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    for idx, wav in enumerate(normalized_wavs, start=1):
        title = titles[idx - 1]
        if "mp3" in want:
            try:
                export_mp3(
                    wav,
                    out_mp3_dir / f"{wav.stem}.mp3",
                    title=title,
                    artist=meta.author,
                    album=meta.title,
                    track=idx,
                )
            except RuntimeError as exc:
                logger.warning("Skipping MP3 for %s: %s", wav.name, exc)
        if "opus" in want:
            try:
                export_opus(
                    wav,
                    out_opus_dir / f"{wav.stem}.opus",
                    title=title,
                    artist=meta.author,
                    album=meta.title,
                    track=idx,
                )
            except RuntimeError as exc:
                logger.warning("Skipping Opus for %s: %s", wav.name, exc)

    # Optional M4B (single file with chapter markers)
    if args.make_m4b and normalized_wavs:
        out_m4b_dir.mkdir(parents=True, exist_ok=True)
        m4b_name = f"{_slugify(meta.author)}-{_slugify(meta.title)}.m4b"
        try:
            make_chaptered_m4b(
                normalized_wavs,
                out_m4b_dir / m4b_name,
                titles,
                album=meta.title,
                artist=meta.author,
                cover_jpeg=meta.cover,
            )
        except RuntimeError as exc:
            logger.warning("M4B packaging skipped: %s", exc)

    logger.info("Normalization and packaging complete: %d chapters processed", len(normalized_wavs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
