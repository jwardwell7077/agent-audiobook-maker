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
    displayed using ``tqdm`` if available.

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

        if show_progress:
            try:  # pragma: no cover - import guard
                from tqdm import tqdm  # type: ignore

                self._tqdm = tqdm
            except Exception:  # pragma: no cover - fallback when tqdm missing
                self._tqdm = None
        else:
            self._tqdm = None

    # ------------------------------------------------------------------
    # Internal helpers
    def _cache_path(self, task: TTSTask) -> Path:
        """Compute the cache file path for ``task``."""

        if self.cache_dir is None:
            return Path()

        norm_text = TextNormalizer.normalize(task.text)
        parts: list[str] = [
            self.adapter.__class__.__name__,
            task.engine or "",
            task.voice or "",
            task.profile_id or "",
            norm_text,
        ]
        if task.refs:
            parts.extend(sorted(Path(r).name for r in task.refs))
        digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
        return self.cache_dir / task.engine / digest[:2] / f"{digest}.wav"

    def _link_or_copy(self, src: Path, dst: Path) -> None:
        """Hardlink ``src`` to ``dst`` if possible, otherwise copy."""

        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)

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

        out_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.adapter.synth(task)

        if self.cache_dir:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            if not cache_path.exists():
                try:
                    os.link(result, cache_path)
                except OSError:
                    shutil.copyfile(result, cache_path)
        return result

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
