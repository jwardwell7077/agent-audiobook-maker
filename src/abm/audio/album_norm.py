"""Album-level loudness normalization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import numpy as np
import soundfile as sf

__all__ = [
    "collect_chapter_stats",
    "compute_album_offset",
    "apply_album_gain",
    "write_album_manifest",
]


def collect_chapter_stats(manifest_path: Path) -> list[dict]:
    """Collect QC stats for each chapter listed in ``manifest_path``.

    Args:
        manifest_path: Path to ``book_manifest.json``.

    Returns:
        A list of merged manifest/QC dictionaries for each chapter.
    """

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    base_dir = Path(manifest.get("base_dir", manifest_path.parent))
    stats: list[dict] = []
    for ch in manifest.get("chapters", []):
        qc_path = base_dir / ch["qc_path"]
        with qc_path.open("r", encoding="utf-8") as f:
            qc = json.load(f)
        merged = dict(ch)
        merged.update(qc)
        stats.append(merged)
    return stats


def compute_album_offset(
    stats: list[dict], target_lufs: float = -18.0, trim_percent: float | None = None
) -> float:
    """Return the dB gain to apply so the median LUFS hits ``target_lufs``.

    Args:
        stats: List of chapter stat dictionaries.
        target_lufs: Desired integrated LUFS for the album.
        trim_percent: Fraction to trim from both ends before computing the median.

    Returns:
        The gain (in dB) to apply.
    """

    lufs_values = [s.get("integrated_lufs", target_lufs) for s in stats]
    if not lufs_values:
        return 0.0
    values = sorted(lufs_values)
    if trim_percent is not None and len(values) >= 5:
        trim = int(len(values) * trim_percent)
        if trim * 2 < len(values):
            values = values[trim : len(values) - trim]
    med = median(values)
    return float(target_lufs - med)


def apply_album_gain(
    wav_path: Path,
    out_path: Path,
    offset_db: float,
    *,
    peak_ceiling_dbfs: float = -1.2,
    pcm_subtype: str = "PCM_16",
) -> None:
    """Apply a uniform gain to ``wav_path`` and write ``out_path``.

    Args:
        wav_path: Source WAV file.
        out_path: Destination for the gain-adjusted audio.
        offset_db: Gain offset in dB to apply.
        peak_ceiling_dbfs: Maximum peak allowed (in dBFS).
        pcm_subtype: PCM subtype used when writing the output file.

    Notes:
        The audio is processed in ``float32`` while preserving channels and
        sample rate.  If the scaled audio would clip, it is reduced so the peak
        stays below ``peak_ceiling_dbfs``.

    Returns:
        None: This function does not return anything.

    Raises:
        OSError: If reading or writing ``wav_path`` fails.
    """

    data, sr = sf.read(wav_path, dtype="float32")
    gain = 10 ** (offset_db / 20)
    data = data * gain
    peak = float(np.max(np.abs(data)))
    limit = 10 ** (peak_ceiling_dbfs / 20)
    if peak > limit:
        data *= limit / peak
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, data, sr, subtype=pcm_subtype)


def write_album_manifest(manifest_path: Path, offset_db: float) -> None:
    """Write a small JSON file describing the applied album gain.

    Args:
        manifest_path: Destination path for the manifest JSON.
        offset_db: Gain offset that was applied (in dB).

    Returns:
        None: This function does not return anything.
    """

    manifest = {"album_gain_db": offset_db}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
