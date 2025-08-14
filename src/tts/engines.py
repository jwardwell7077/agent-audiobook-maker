"""TTS engines and synthesis helpers (primary implementation).

Previously located at src.pipeline.tts.engines; migrated here.
Provides XTTS (Coqui) primary synthesis with a Piper-like stub fallback,
functions to synthesize stems, stitch them, and persist DB rows.
"""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Iterable, List, Optional

import numpy as np
import soundfile as sf

try:  # pragma: no cover - heavy import
    from TTS.api import TTS as CoquiTTS  # type: ignore
    # pylint: disable=import-error,invalid-name
except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
    CoquiTTS = None  # type: ignore  # pylint: disable=invalid-name

from db import get_session, models  # pylint: disable=import-error

_xtts_model = None  # pylint: disable=invalid-name
_model_lock = threading.Lock()
_XTTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


def _load_xtts() -> Any | None:  # pragma: no cover - heavy
    """Lazily load (singleton) XTTS model if available."""
    global _xtts_model  # pylint: disable=global-statement
    if _xtts_model is not None:
        return _xtts_model
    if CoquiTTS is None:
        return None
    with _model_lock:
        if _xtts_model is None:
            _xtts_model = CoquiTTS(model_name=_XTTS_MODEL_NAME)  # type: ignore
    return _xtts_model


def _hash_text(text: str) -> str:
    """Return short hash fragment for text for stable stem filenames."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def synthesize_text_xtts(
    text: str,
) -> tuple[Optional[np.ndarray], Optional[int], Optional[str]]:
    """Synthesize text with XTTS returning (audio, sample_rate, error)."""
    model = _load_xtts()
    if model is None:
        return None, None, "xtts_model_unavailable"
    try:
        audio = model.tts(text)  # type: ignore
        sr = getattr(
            getattr(model, "synthesizer", None),
            "output_sample_rate",
            22050,
        )
        return (
            audio.astype(np.float32),
            int(sr),
            None,
        )  # type: ignore[arg-type]
    except Exception as e:  # noqa: BLE001
        # pylint: disable=broad-exception-caught
        return None, None, f"xtts_error:{e}"  # pragma: no cover


def synthesize_text_piper_stub(text: str) -> tuple[np.ndarray, int]:
    """Produce short audible placeholder waveform (Piper fallback stub)."""
    sr = 16000
    duration = min(0.3 + 0.01 * len(text), 2.0)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.1 * np.sin(2 * np.pi * 880 * t) * np.exp(-3 * t / duration)
    return audio.astype(np.float32), sr


def synthesize_segments_to_stems(
    book_id: str,
    chapter_id: str,
    segments: Iterable[dict | Any],
    out_dir: Path,
    prefer_xtts: bool = True,
) -> list[Path]:  # pylint: disable=too-many-locals
    """Synthesize each segment to an individual stem WAV file.

    Falls back to stub synthesis if XTTS unavailable. Persists/updates Stem
    rows.
    Returns list of created stem Paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stem_paths: list[Path] = []
    for i, seg in enumerate(segments):
        if isinstance(seg, dict):
            text = seg.get("text", "")
        else:
            text = getattr(seg, "text", "")
        hash_part = _hash_text(text)
        stem_path = out_dir / f"{i:05d}_{hash_part}.wav"
        audio: Optional[np.ndarray] = None
        sr: Optional[int] = None
        error: Optional[str] = None
        if prefer_xtts:
            audio, sr, error = synthesize_text_xtts(text)
        if audio is None or sr is None:
            audio, sr = synthesize_text_piper_stub(text)
        sf.write(stem_path, audio, sr)  # type: ignore[arg-type]
        stem_paths.append(stem_path)
        with get_session() as session:
            stem_id = f"{book_id}-{chapter_id}-{i:05d}"
            existing = session.get(models.Stem, stem_id)
            duration_s = len(audio) / sr if audio is not None and sr else None
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
                        hashes={"text": hash_part, "engine_error": error},
                        status="synthesized",
                    )
                )
            else:
                existing.path = str(stem_path)
                existing.duration_s = duration_s
                existing.hashes = {"text": hash_part, "engine_error": error}
                existing.status = "synthesized"
    return stem_paths


def stitch_stems_to_render(
    stem_paths: List[Path],
    render_path: Path,
) -> dict:
    """Concatenate stem WAVs into a single WAV, computing loudness/peak."""
    if not stem_paths:
        raise ValueError("no_stems_to_stitch")
    audios: List[np.ndarray] = []
    sr: Optional[int] = None
    for p in stem_paths:
        data, file_sr = sf.read(p)
        if sr is None:
            sr = file_sr
        elif file_sr != sr:
            raise ValueError("sample_rate_mismatch")  # pragma: no cover
        audios.append(data.astype(np.float32))
    if audios:
        chapter_audio = np.concatenate(audios)
    else:  # pragma: no cover
        chapter_audio = np.zeros(1, dtype=np.float32)
    try:  # pragma: no cover - loudness calc heavy
        import pyloudnorm as pyln  # pylint: disable=import-outside-toplevel
        meter = pyln.Meter(sr)  # type: ignore[arg-type]
        loudness = float(meter.integrated_loudness(chapter_audio))
    except Exception:  # pylint: disable=broad-exception-caught
        loudness = None
    peak = float(20 * np.log10(np.max(np.abs(chapter_audio)) + 1e-9))
    sf.write(render_path, chapter_audio, sr)  # type: ignore[arg-type]
    duration_s = len(chapter_audio) / sr if sr else None
    return {
        "duration_s": duration_s,
        "loudness_lufs": loudness,
        "peak_dbfs": peak,
        "sample_rate": sr,
    }


def synthesize_and_render_chapter(
    book_id: str,
    chapter_id: str,
    segments: Iterable[dict | Any],
    data_root: Path = Path("data"),
    prefer_xtts: bool = True,
) -> dict:
    """Full chapter render: stems synthesis + stitching + DB Render row."""
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
                    hashes=None,
                    status="rendered",
                )
            )
        else:
            existing.path = str(render_path)
            existing.loudness_lufs = render_meta.get("loudness_lufs")
            existing.peak_dbfs = render_meta.get("peak_dbfs")
            existing.duration_s = render_meta.get("duration_s")
            existing.status = "rendered"
    render_meta.update(
        {
            "stem_count": len(stem_paths),
            "elapsed_s": elapsed,
            "render_path": str(render_path),
        }
    )
    return render_meta


__all__ = [
    "synthesize_segments_to_stems",
    "synthesize_and_render_chapter",
]
