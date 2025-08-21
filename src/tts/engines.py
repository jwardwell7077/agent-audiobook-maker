"""Text-to-speech (TTS) synthesis engines and helpers.

Features:
* Optional XTTS (Coqui) model loading (lazy & thread‑safe).
* Lightweight sine‑wave stub fallback.
* Stem synthesis with DB persistence.
* Chapter stitching with optional loudness normalisation (pyloudnorm).

Typing keeps numpy arrays as ``Any`` during incremental mypy adoption.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from collections.abc import Iterable, Mapping, Sized
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import soundfile as sf

try:  # pragma: no cover - optional heavy import
    # TODO(mypy): add proper Coqui TTS stubs or vendor minimal protocol.
    # For now we allow this untyped import and treat the model as Any.
    from TTS.api import TTS as CoquiTTS
except Exception:  # pragma: no cover  # noqa: BLE001
    CoquiTTS = None  # fallback when library missing

from db import get_session, models  # pylint: disable=import-error

_logger = logging.getLogger(__name__)
if not _logger.handlers:  # pragma: no cover (library import safety)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)

try:
    _loudness_target_lufs: float | None = float(os.getenv("LOUDNESS_TARGET_LUFS", "-16"))
except ValueError:  # pragma: no cover
    _loudness_target_lufs = None

_XTTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
_MODEL_STATE: dict[str, object | None] = {"xtts": None}
_model_lock = threading.Lock()


class SegmentLike(Protocol):
    """Protocol for simple objects having a ``text`` attribute.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """

    text: str  # noqa: D401


def _load_xtts() -> object | None:  # pragma: no cover - heavy path
    """Load the XTTS model if available, using a thread-safe singleton pattern.

    Args:
        None

    Returns:
        object | None: The loaded XTTS model instance, or None if unavailable.

    Raises:
        None
    """
    model = _MODEL_STATE["xtts"]
    if model is not None:
        return model
    if CoquiTTS is None:
        return None
    with _model_lock:
        if _MODEL_STATE["xtts"] is None:
            _MODEL_STATE["xtts"] = CoquiTTS(model_name=_XTTS_MODEL_NAME)
    return _MODEL_STATE["xtts"]


def _hash_text(text: str) -> str:
    """Hash text to a short SHA256-based string for file naming.

    Args:
        text (str): The input text to hash.

    Returns:
        str: The first 16 hex digits of the SHA256 hash.

    Raises:
        None
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def synthesize_text_xtts(
    text: str,
) -> tuple[object | None, int | None, str | None]:
    """Synthesize speech from text using the XTTS model if available.

    Args:
        text (str): The input text to synthesize.

    Returns:
        tuple[object | None, int | None, str | None]:
            (audio array or None, sample rate or None, error string or None)

    Raises:
        None
    """
    model = _load_xtts()
    if model is None:
        return None, None, "xtts_model_unavailable"
    try:
        audio = model.tts(text)  # type: ignore[attr-defined]
        synth = getattr(model, "synthesizer", None)
        sr = int(getattr(synth, "output_sample_rate", 22050))
        audio_arr = cast(Any, audio).astype(np.float32)
        return audio_arr, sr, None
    except Exception as e:  # pragma: no cover  # noqa: BLE001
        return None, None, f"xtts_error:{e}"


def synthesize_text_stub(text: str) -> tuple[object, int]:
    """Deterministic short sine tone used when real model unavailable.

    Args:
        text (str): The input text (used to determine duration).

    Returns:
        tuple[object, int]: (audio array, sample rate)

    Raises:
        None
    """
    sr = 16_000
    duration = min(0.3 + 0.01 * len(text), 2.0)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.1 * np.sin(2 * np.pi * 880 * t) * np.exp(-3 * t / duration)
    return audio.astype(np.float32), sr


def _segment_text(seg: Mapping[str, object] | SegmentLike | object) -> str:
    """Extract the text from a segment object or mapping.

    Args:
        seg (Mapping[str, object] | SegmentLike | object): The segment to extract text from.

    Returns:
        str: The extracted text, or empty string if not found.

    Raises:
        None
    """
    if isinstance(seg, Mapping):
        mapping = cast(Mapping[str, object], seg)
        return str(mapping.get("text", ""))
    return str(getattr(seg, "text", ""))


def synthesize_segments_to_stems(
    book_id: str,
    chapter_id: str,
    segments: Iterable[Mapping[str, object] | SegmentLike | object],
    out_dir: Path,
    prefer_xtts: bool = True,
) -> list[Path]:
    """Synthesize all segments to stem WAV files and persist to DB.

    Args:
        book_id (str): The book identifier.
        chapter_id (str): The chapter identifier.
        segments (Iterable[Mapping[str, object] | SegmentLike | object]): The segments to synthesize.
        out_dir (Path): Output directory for stem files.
        prefer_xtts (bool, optional): Prefer XTTS engine if available. Defaults to True.

    Returns:
        list[Path]: List of generated stem file paths.

    Raises:
        AssertionError: If audio or sample rate is None after synthesis.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stem_paths: list[Path] = []
    for i, seg in enumerate(segments):
        text = _segment_text(seg)
        hash_part = _hash_text(text)
        stem_path = out_dir / f"{i:05d}_{hash_part}.wav"
        audio: Any | None = None
        sr: int | None = None
        err: str | None = None
        if prefer_xtts:
            audio, sr, err = synthesize_text_xtts(text)
        if audio is None or sr is None:
            audio, sr = synthesize_text_stub(text)
        assert audio is not None and sr is not None
        cast(Any, sf).write(stem_path, audio, sr)
        stem_paths.append(stem_path)
        with get_session() as session:
            stem_id = f"{book_id}-{chapter_id}-{i:05d}"
            existing = session.get(models.Stem, stem_id)
            duration_s = (len(cast(Sized, audio)) / sr) if sr else None
            hashes: dict[str, object] = {"text": hash_part}
            if err is not None:
                hashes["engine_error"] = err
            if not existing:
                session.add(
                    models.Stem(
                        id=stem_id,
                        book_id=book_id,
                        chapter_id=f"{book_id}-{chapter_id}",
                        utterance_idx=i,
                        path=str(stem_path),
                        duration_s=duration_s,
                        tts_profile_id=None,
                        hashes=hashes,
                        status="synthesized",
                    )
                )
            else:
                existing.path = str(stem_path)
                existing.duration_s = duration_s
                existing.hashes = hashes
                existing.status = "synthesized"
    return stem_paths


def stitch_stems_to_render(
    stem_paths: list[Path],
    render_path: Path,
) -> dict[str, Any]:
    """Stitch stem WAV files into a single render, optionally normalizing loudness."""
    if not stem_paths:
        raise ValueError("no_stems_to_stitch")
    audios: list[Any] = []
    sr: int | None = None
    for p in stem_paths:
        data_np, file_sr = cast(tuple[Any, Any], cast(Any, sf).read(p))
        if sr is None:
            sr = int(file_sr)
        elif file_sr != sr:  # pragma: no cover
            raise ValueError("sample_rate_mismatch")
        audios.append(data_np.astype(np.float32))
    chapter_audio = np.concatenate(audios) if audios else np.zeros(1, dtype=np.float32)
    applied_gain_db: float | None = None
    loudness: float | None = None
    try:  # pragma: no cover - optional dependency
        import pyloudnorm as pyln

        if sr is None:
            raise RuntimeError("sample_rate_missing")
        meter: Any = pyln.Meter(sr)
        loudness = float(meter.integrated_loudness(chapter_audio))
        if _loudness_target_lufs is not None:
            gain_db = float(_loudness_target_lufs - loudness)
            gain_db = max(-24.0, min(24.0, gain_db))
            if abs(gain_db) > 0.1:
                chapter_audio = (chapter_audio * (10 ** (gain_db / 20))).astype(np.float32)
                applied_gain_db = gain_db
                loudness = float(meter.integrated_loudness(chapter_audio))
    except Exception as exc:  # noqa: BLE001
        _logger.debug("loudness_normalisation_failed error=%s", exc)
    peak_dbfs = float(20 * np.log10(np.max(np.abs(chapter_audio)) + 1e-9))
    assert sr is not None
    cast(Any, sf).write(render_path, chapter_audio, sr)
    return {
        "duration_s": len(chapter_audio) / sr if sr else None,
        "loudness_lufs": loudness,
        "peak_dbfs": peak_dbfs,
        "sample_rate": sr,
        "applied_gain_db": applied_gain_db,
    }


def synthesize_and_render_chapter(
    book_id: str,
    chapter_id: str,
    segments: Iterable[Mapping[str, Any] | SegmentLike | Any],
    data_root: Path = Path("data"),
    prefer_xtts: bool = True,
) -> dict[str, Any]:
    """Synthesize and render a chapter from segments, persisting all artifacts.

    Args:
        book_id (str): The book identifier.
        chapter_id (str): The chapter identifier.
        segments (Iterable[Mapping[str, Any] | SegmentLike | Any]): The segments to synthesize.
        data_root (Path, optional): Root directory for data. Defaults to Path("data").
        prefer_xtts (bool, optional): Prefer XTTS engine if available. Defaults to True.

    Returns:
        dict[str, Any]: Metadata about the render (duration, loudness, etc).

    Raises:
        AssertionError: If audio or sample rate is None after synthesis.
        ValueError: If no stems are provided or sample rates mismatch.
    """
    start = time.time()
    stems_dir = data_root / "stems" / book_id / chapter_id
    stem_paths = synthesize_segments_to_stems(
        book_id,
        chapter_id,
        segments,
        stems_dir,
        prefer_xtts=prefer_xtts,
    )
    render_dir = data_root / "renders" / book_id
    render_dir.mkdir(parents=True, exist_ok=True)
    render_path = render_dir / f"{chapter_id}.wav"
    render_meta = stitch_stems_to_render(stem_paths, render_path)
    elapsed = time.time() - start
    with get_session() as session:
        render_id = f"{book_id}-{chapter_id}-render"
        existing = session.get(models.Render, render_id)
        hashes: dict[str, object] = {}
        ag = render_meta.get("applied_gain_db")
        if ag is not None:
            hashes["applied_gain_db"] = ag
        if not existing:
            session.add(
                models.Render(
                    id=render_id,
                    book_id=book_id,
                    chapter_id=f"{book_id}-{chapter_id}",
                    path=str(render_path),
                    loudness_lufs=render_meta.get("loudness_lufs"),
                    peak_dbfs=render_meta.get("peak_dbfs"),
                    duration_s=render_meta.get("duration_s"),
                    hashes=hashes,
                    status="rendered",
                )
            )
        else:
            existing.path = str(render_path)
            existing.loudness_lufs = render_meta.get("loudness_lufs")
            existing.peak_dbfs = render_meta.get("peak_dbfs")
            existing.duration_s = render_meta.get("duration_s")
            # mypy: model attribute dynamic mapping
            existing.hashes = hashes
            existing.status = "rendered"
    render_meta.update(
        {
            "stem_count": len(stem_paths),
            "elapsed_s": elapsed,
            "render_path": str(render_path),
        }
    )
    _logger.info(
        "render_complete book=%s chap=%s stems=%s elapsed=%.3f loudness=%s",
        book_id,
        chapter_id,
        len(stem_paths),
        elapsed,
        render_meta.get("loudness_lufs"),
    )
    return render_meta


__all__ = ["synthesize_segments_to_stems", "synthesize_and_render_chapter"]
"""(End of module)"""
