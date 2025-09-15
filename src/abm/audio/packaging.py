"""Helpers for packaging rendered audio into common formats."""

from __future__ import annotations

import importlib.util
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

__all__ = [
    "export_mp3",
    "export_opus",
    "make_chaptered_m4b",
    "write_chapter_cue",
    "format_ts",
]


if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from pydub import AudioSegment


logger = logging.getLogger(__name__)


def _require_pydub() -> type[AudioSegment]:  # pragma: no cover - simple helper
    """Return :class:`~pydub.AudioSegment` or raise a helpful error."""

    try:
        from pydub import AudioSegment
    except Exception as exc:  # pragma: no cover - pydub missing
        raise RuntimeError("pydub/ffmpeg required for packaging") from exc
    return AudioSegment


def _have_ffmpeg() -> bool:
    """Return ``True`` if :command:`ffmpeg` is available on ``PATH``."""

    return shutil.which("ffmpeg") is not None


def _write_ffmetadata_chapters(chapters: list[tuple[float, float, str]], out_path: Path) -> None:
    """Write an ``FFMETADATA1`` file with chapter entries.

    Args:
        chapters: Sequence of ``(start_s, end_s, title)`` tuples.
        out_path: Destination metadata file path.
    """

    lines = [";FFMETADATA1"]
    for start, end, title in chapters:
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={int(start * 1000)}",
                f"END={int(end * 1000)}",
                f"title={title.replace(chr(10), ' ')}",
            ]
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mux_m4b_with_chapters(input_m4a: Path, ffmeta: Path, out_m4b: Path) -> None:
    """Mux ``input_m4a`` with chapter metadata into ``out_m4b``.

    Args:
        input_m4a: Source M4A file.
        ffmeta: Path to ``FFMETADATA1`` file produced by
            :func:`_write_ffmetadata_chapters`.
        out_m4b: Destination M4B path.

    Raises:
        RuntimeError: If ``ffmpeg`` fails.
    """

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_m4a),
        "-i",
        str(ffmeta),
        "-map_metadata",
        "0",
        "-map_chapters",
        "1",
        "-codec",
        "copy",
        str(out_m4b),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-10:])
        raise RuntimeError(f"ffmpeg chapter mux failed: {tail}")


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

    Returns:
        None: This function does not return anything.

    Raises:
        RuntimeError: If neither :mod:`pydub` nor ``ffmpeg`` is available or
            if the export command fails.
    """

    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    spec = importlib.util.find_spec("pydub")

    if spec and ffmpeg:
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
            return
        except Exception as exc:  # pragma: no cover - ffmpeg error
            raise RuntimeError(f"ffmpeg failed to export {in_wav} -> {out_mp3} (codec mp3)") from exc

    if ffmpeg:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(in_wav),
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "2",
            "-metadata",
            f"title={title}",
            "-metadata",
            f"artist={artist}",
            "-metadata",
            f"album={album}",
            "-metadata",
            f"track={track}",
            "-metadata",
            f"tracknumber={track}",
            str(out_mp3),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join(proc.stderr.splitlines()[-10:])
            raise RuntimeError(f"ffmpeg failed to export {in_wav} -> {out_mp3}: {tail}")
        return

    raise RuntimeError("pydub/ffmpeg required for packaging")


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

    Returns:
        None: This function does not return anything.

    Raises:
        RuntimeError: If neither :mod:`pydub` nor ``ffmpeg`` is available or
            if the export command fails.
    """

    out_opus.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    spec = importlib.util.find_spec("pydub")

    if spec and ffmpeg:
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
            return
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"ffmpeg failed to export {in_wav} -> {out_opus} (codec opus)") from exc

    if ffmpeg:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(in_wav),
            "-c:a",
            "libopus",
            "-b:a",
            "96k",
            "-metadata",
            f"title={title}",
            "-metadata",
            f"artist={artist}",
            "-metadata",
            f"album={album}",
            "-metadata",
            f"track={track}",
            "-metadata",
            f"tracknumber={track}",
            str(out_opus),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join(proc.stderr.splitlines()[-10:])
            raise RuntimeError(f"ffmpeg failed to export {in_wav} -> {out_opus}: {tail}")
        return

    raise RuntimeError("pydub/ffmpeg required for packaging")


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

    Returns:
        None: This function does not return anything.

    Raises:
        ValueError: If ``chapter_wavs`` and ``chapter_titles`` lengths differ.
        FileNotFoundError: If ``cover_jpeg`` is provided but missing.
        RuntimeError: If :mod:`pydub`/FFmpeg is unavailable.

    Notes:
        If :command:`ffmpeg` is unavailable, this falls back to writing a
        sidecar ``.chapters.txt`` and produces an ``.m4b`` without embedded
        chapter atoms.
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

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_m4a = Path(tmpdir) / "temp.m4a"
        # Note: pydub does not support embedding cover images when exporting MP4/M4A.
        # We'll add cover art afterwards using mutagen if available.
        joined.export(
            tmp_m4a,
            format="mp4",
            tags=tags,
        )

        if cover_jpeg:
            try:
                from mutagen.mp4 import MP4, MP4Cover

                audio = MP4(str(tmp_m4a))
                audio["covr"] = [MP4Cover(cover_jpeg.read_bytes(), imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()
            except Exception:  # pragma: no cover - mutagen missing
                logger.warning("mutagen not available; cover art not embedded")

        durations = [seg.duration_seconds for seg in segments]
        chapters: list[tuple[float, float, str]] = []
        start = 0.0
        for dur, title in zip(durations, chapter_titles, strict=True):
            end = start + dur
            chapters.append((start, end, title))
            start = end

        if _have_ffmpeg():
            ffmeta = Path(tmpdir) / "chapters.txt"
            _write_ffmetadata_chapters(chapters, ffmeta)
            _mux_m4b_with_chapters(tmp_m4a, ffmeta, out_m4b)
        else:  # pragma: no cover - depends on environment
            logger.warning("ffmpeg not found; writing sidecar chapters")
            shutil.move(tmp_m4a, out_m4b)
            write_chapter_cue(chapter_wavs, out_m4b.with_suffix(".chapters.txt"), chapter_titles)


def write_chapter_cue(chapter_wavs: list[Path], out_cue: Path, titles: list[str]) -> None:
    """Write a cue sheet with basic chapter information.

    Args:
        chapter_wavs: Ordered list of chapter WAV files.
        out_cue: Destination cue sheet path.
        titles: Titles matching ``chapter_wavs``.

    Returns:
        None: This function does not return anything.

    Raises:
        ValueError: If ``chapter_wavs`` and ``titles`` lengths differ.
    """

    if len(chapter_wavs) != len(titles):
        raise ValueError("chapter_wavs and titles length mismatch")

    import soundfile as sf  # local import to keep module import-safe

    start = 0.0
    lines: list[str] = []
    for wav, title in zip(chapter_wavs, titles, strict=True):
        info = sf.info(str(wav))
        lines.append(f"{format_ts(start)}\t{title}")
        start += info.frames / info.samplerate
    out_cue.write_text("\n".join(lines) + "\n", encoding="utf-8")
