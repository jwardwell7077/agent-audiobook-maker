"""Helpers for packaging rendered audio into common formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import soundfile as sf

__all__ = [
    "export_mp3",
    "export_opus",
    "make_chaptered_m4b",
    "write_chapter_cue",
    "format_ts",
]


if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from pydub import AudioSegment


def _require_pydub() -> type[AudioSegment]:  # pragma: no cover - simple helper
    """Return :class:`~pydub.AudioSegment` or raise a helpful error."""

    try:
        from pydub import AudioSegment
    except Exception as exc:  # pragma: no cover - pydub missing
        raise RuntimeError("pydub/ffmpeg required for packaging") from exc
    return AudioSegment


def format_ts(seconds: float) -> str:
    """Return a zero-padded ``HH:MM:SS.mmm`` timestamp.

    Args:
        seconds: Time in seconds.

    Returns:
        A formatted timestamp string.
    """

    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    h = total_min // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def export_mp3(
    in_wav: Path,
    out_mp3: Path,
    *,
    title: str,
    artist: str,
    album: str,
    track: int,
) -> None:
    """Export ``in_wav`` as an MP3 with basic ID3 tags.

    Args:
        in_wav: Source WAV file.
        out_mp3: Destination MP3 path.
        title: Track title.
        artist: Artist name.
        album: Album/collection name.
        track: Track number within the album.

    Raises:
        RuntimeError: If :mod:`pydub`/FFmpeg is unavailable or export fails.
    """

    AudioSegment = _require_pydub()
    try:
        segment = AudioSegment.from_wav(str(in_wav))
        tags = {
            "title": title,
            "artist": artist,
            "album": album,
            "track": str(track),
            "tracknumber": str(track),
        }
        segment.export(out_mp3, format="mp3", tags=tags)
    except Exception as exc:  # pragma: no cover - ffmpeg error
        raise RuntimeError(
            f"ffmpeg failed to export {in_wav} -> {out_mp3} (codec mp3)"
        ) from exc


def export_opus(
    in_wav: Path,
    out_opus: Path,
    *,
    title: str,
    artist: str,
    album: str,
    track: int,
) -> None:
    """Export ``in_wav`` as an Opus file with basic tags.

    Args:
        in_wav: Source WAV file.
        out_opus: Destination Opus path.
        title: Track title.
        artist: Artist name.
        album: Album/collection name.
        track: Track number within the album.

    Raises:
        RuntimeError: If :mod:`pydub`/FFmpeg is unavailable or export fails.
    """

    AudioSegment = _require_pydub()
    try:
        segment = AudioSegment.from_wav(str(in_wav))
        tags = {
            "title": title,
            "artist": artist,
            "album": album,
            "track": str(track),
            "tracknumber": str(track),
        }
        segment.export(out_opus, format="opus", tags=tags)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            f"ffmpeg failed to export {in_wav} -> {out_opus} (codec opus)"
        ) from exc


def make_chaptered_m4b(
    chapter_wavs: list[Path],
    out_m4b: Path,
    chapter_titles: list[str],
    *,
    album: str,
    artist: str,
    cover_jpeg: Path | None = None,
) -> None:
    """Concatenate ``chapter_wavs`` into a single M4B-style file.

    Args:
        chapter_wavs: Ordered list of chapter WAV files.
        out_m4b: Destination M4B/M4A path.
        chapter_titles: Titles matching ``chapter_wavs``.
        album: Album name.
        artist: Artist/author name.
        cover_jpeg: Optional cover image to embed.

    Raises:
        ValueError: If ``chapter_wavs`` and ``chapter_titles`` lengths differ.
        FileNotFoundError: If ``cover_jpeg`` is provided but missing.
        RuntimeError: If :mod:`pydub`/FFmpeg is unavailable.

    Notes:
        This writes a sidecar ``.chapters.txt`` file describing chapter starts.
        TODO: replace with a mutagen-based implementation that embeds chapters
        and cover art directly in the container.
    """

    if len(chapter_wavs) != len(chapter_titles):
        raise ValueError("chapter_wavs and chapter_titles length mismatch")
    if cover_jpeg and not cover_jpeg.exists():
        raise FileNotFoundError(cover_jpeg)

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
        lines.append(f"{format_ts(start)}\t{title}")
        start += seg.duration_seconds
    cue_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_chapter_cue(
    chapter_wavs: list[Path], out_cue: Path, titles: list[str]
) -> None:
    """Write a cue sheet with basic chapter information.

    Args:
        chapter_wavs: Ordered list of chapter WAV files.
        out_cue: Destination cue sheet path.
        titles: Titles matching ``chapter_wavs``.

    Raises:
        ValueError: If ``chapter_wavs`` and ``titles`` lengths differ.
    """

    if len(chapter_wavs) != len(titles):
        raise ValueError("chapter_wavs and titles length mismatch")

    start = 0.0
    lines: list[str] = []
    for wav, title in zip(chapter_wavs, titles, strict=True):
        info = sf.info(str(wav))
        lines.append(f"{format_ts(start)}\t{title}")
        start += info.frames / info.samplerate
    out_cue.write_text("\n".join(lines) + "\n", encoding="utf-8")
