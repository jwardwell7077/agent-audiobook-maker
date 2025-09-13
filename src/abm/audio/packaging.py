"""Helpers for packaging rendered audio into common formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

__all__ = [
    "export_mp3",
    "export_opus",
    "make_chaptered_m4b",
    "write_chapter_cue",
]


if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from pydub import AudioSegment


def _require_pydub() -> AudioSegment:  # pragma: no cover - simple helper
    try:
        from pydub import AudioSegment
    except Exception as exc:  # pragma: no cover - pydub missing
        raise RuntimeError("pydub/ffmpeg required for packaging") from exc
    return AudioSegment


def export_mp3(
    in_wav: Path,
    out_mp3: Path,
    *,
    title: str,
    artist: str,
    album: str,
    track: int,
) -> None:
    """Export ``in_wav`` as an MP3 with basic ID3 tags."""

    AudioSegment = _require_pydub()
    try:
        segment = AudioSegment.from_wav(str(in_wav))
        tags = {
            "title": title,
            "artist": artist,
            "album": album,
            "track": str(track),
        }
        segment.export(out_mp3, format="mp3", tags=tags)
    except Exception as exc:  # pragma: no cover - ffmpeg error
        raise RuntimeError("ffmpeg failed to export MP3") from exc


def export_opus(
    in_wav: Path,
    out_opus: Path,
    *,
    title: str,
    artist: str,
    album: str,
    track: int,
) -> None:
    """Export ``in_wav`` as an Opus file with basic tags."""

    AudioSegment = _require_pydub()
    try:
        segment = AudioSegment.from_wav(str(in_wav))
        tags = {
            "title": title,
            "artist": artist,
            "album": album,
            "track": str(track),
        }
        segment.export(out_opus, format="opus", tags=tags)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("ffmpeg failed to export Opus") from exc


def make_chaptered_m4b(
    chapter_wavs: list[Path],
    out_m4b: Path,
    chapter_titles: list[str],
    *,
    album: str,
    artist: str,
    cover_jpeg: Path | None = None,
) -> None:
    """Concatenate ``chapter_wavs`` into a single M4B style file.

    This implementation is intentionally lightweight: chapters are concatenated
    using :mod:`pydub` and a sidecar ``chapters.txt`` file is written describing
    chapter start times and titles.
    """

    if len(chapter_wavs) != len(chapter_titles):
        raise ValueError("chapter_wavs and chapter_titles length mismatch")

    AudioSegment = _require_pydub()

    segments = [AudioSegment.from_wav(str(p)) for p in chapter_wavs]
    joined = sum(segments[1:], segments[0]) if segments else AudioSegment.silent(1)
    tags = {"album": album, "artist": artist}
    out_m4b.parent.mkdir(parents=True, exist_ok=True)
    joined.export(
        out_m4b, format="mp4", tags=tags, cover=str(cover_jpeg) if cover_jpeg else None
    )

    # Write simple sidecar with chapter start times
    cue_path = out_m4b.with_suffix(".chapters.txt")
    start = 0.0
    lines: list[str] = []
    for seg, title in zip(segments, chapter_titles, strict=True):
        lines.append(f"{start:.3f}\t{title}")
        start += seg.duration_seconds
    cue_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_chapter_cue(
    chapter_wavs: list[Path], out_cue: Path, titles: list[str]
) -> None:
    """Write a cue sheet with basic chapter information."""

    if len(chapter_wavs) != len(titles):
        raise ValueError("chapter_wavs and titles length mismatch")
    import soundfile as sf

    start = 0.0
    lines: list[str] = []
    for wav, title in zip(chapter_wavs, titles, strict=True):
        info = sf.info(str(wav))
        lines.append(f"{start:.3f}\t{title}")
        start += info.frames / info.samplerate
    out_cue.write_text("\n".join(lines) + "\n", encoding="utf-8")
