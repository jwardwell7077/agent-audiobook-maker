"""Concurrency-aware TTS rendering with caching and progress bars."""

from __future__ import annotations

import hashlib
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from abm.audio.text_normalizer import TextNormalizer
from abm.audio.tts_base import TTSAdapter, TTSTask

__all__ = ["TTSManager"]


class TTSManager:
    """Render ``TTSTask`` objects with optional caching and concurrency.

    The manager deduplicates synthesis requests using a content-addressable
    cache. Audio is rendered concurrently via a thread pool and progress can be
    displayed using ``tqdm`` if available. Cached files are stored as::

        cache/<engine>/<sha[:2]>/<sha>.wav

    where ``sha`` is a SHA-256 fingerprint over engine name, adapter and
    normalizer versions, normalized text, voice, style, profile id, references
    and engine-specific parameters.

    Attributes:
        adapter: Concrete :class:`TTSAdapter` used for synthesis.
        max_workers: Maximum number of worker threads.
        cache_dir: Directory for cached WAV files. ``None`` disables caching.
        show_progress: Whether to display a ``tqdm`` progress bar when rendering
            batches.
    """

    def __init__(
        self,
        adapter: TTSAdapter,
        max_workers: int = 2,
        cache_dir: Path | None = None,
        show_progress: bool = True,
    ) -> None:
        self.adapter = adapter
        self.max_workers = int(max_workers)
        self.cache_dir = cache_dir
        self.show_progress = show_progress
        self._tqdm = None  # lazily imported

    # ------------------------------------------------------------------
    # Internal helpers
    def _cache_path(self, task: TTSTask) -> Path:
        """Compute the cache file path for ``task``."""

        if self.cache_dir is None:
            return Path()

        norm_text = TextNormalizer.normalize(task.text)
        tn_ver = getattr(TextNormalizer, "version", lambda: "0")()
        adapter_ver = getattr(self.adapter, "version", lambda: "0")()
        seed = getattr(task, "seed", "")
        params = getattr(task, "engine_params", None) or getattr(task, "params", None)
        parts: list[str] = [
            task.engine or "",
            adapter_ver,
            tn_ver,
            norm_text,
            task.voice or "",
            task.style or "",
            task.profile_id or "",
            seed or "",
        ]
        if task.refs:
            parts.extend(sorted(Path(r).name for r in task.refs))
        if params:
            parts.extend(f"{k}={v}" for k, v in sorted(params.items()))
        h = hashlib.sha256()
        h.update("|".join(parts).encode("utf-8"))
        digest = h.hexdigest()
        return self.cache_dir / task.engine / digest[:2] / f"{digest}.wav"

    def _link_or_copy(self, src: Path, dst: Path) -> None:
        """Hardlink ``src`` to ``dst`` if possible, otherwise copy."""

        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    # ------------------------------------------------------------------
    # Public API
    def render_one(self, task: TTSTask) -> Path:
        """Render a single task, using the cache when available.

        Args:
            task: The synthesis request to render.

        Returns:
            Path to the rendered WAV file (same as ``task.out_path``).

        Raises:
            SynthesisError: If the underlying adapter fails to synthesize.
        """

        cache_path = self._cache_path(task)
        out_path = task.out_path

        if self.cache_dir and cache_path.exists():
            self._link_or_copy(cache_path, out_path)
            return out_path

        if self.cache_dir:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache_path.with_suffix(".tmp.wav")
            tmp_task = TTSTask(
                text=task.text,
                speaker=task.speaker,
                engine=task.engine,
                voice=task.voice,
                profile_id=task.profile_id,
                refs=task.refs,
                out_path=tmp,
                pause_ms=task.pause_ms,
                style=task.style,
            )
            result = self.adapter.synth(tmp_task)
            os.replace(result, cache_path)
            self._link_or_copy(cache_path, out_path)
            return out_path

        out_path.parent.mkdir(parents=True, exist_ok=True)
        return self.adapter.synth(task)

    def render_batch(self, tasks: list[TTSTask]) -> list[Path]:
        """Render many tasks concurrently.

        Args:
            tasks: A list of synthesis jobs.

        Returns:
            List of output paths corresponding to ``tasks`` in the same order.

        Raises:
            SynthesisError: If any task fails to synthesize.
        """

        if not tasks:
            return []

        self.adapter.preload()

        if self.show_progress and self._tqdm is None:  # pragma: no cover - import guard
            try:
                from tqdm import tqdm  # type: ignore

                self._tqdm = tqdm
            except Exception:  # pragma: no cover
                self._tqdm = None

        results: list[Path] = [Path()] * len(tasks)
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            future_map = {ex.submit(self.render_one, t): i for i, t in enumerate(tasks)}
            pbar = (
                self._tqdm(total=len(tasks))
                if self._tqdm and self.show_progress
                else None
            )
            try:
                for fut in as_completed(future_map):
                    idx = future_map[fut]
                    results[idx] = fut.result()
                    if pbar is not None:
                        pbar.update(1)
            finally:
                if pbar is not None:
                    pbar.close()
        return results
