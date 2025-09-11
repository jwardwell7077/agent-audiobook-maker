from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Optional deps (handled gracefully)
try:
    import psutil  # type: ignore

    _HAS_PSUTIL = True
except Exception:
    psutil = None  # type: ignore
    _HAS_PSUTIL = False

try:
    import pynvml  # type: ignore

    pynvml.nvmlInit()
    _HAS_NVML = True
except Exception:
    _HAS_NVML = False


@dataclass
class ChapterMetrics:
    """Holds metrics for a single chapter processing pass."""

    chapter_index: int
    title: str = ""
    n_paragraphs: int = 0
    time_normalize: float = 0.0
    time_segment: float = 0.0
    time_roster: float = 0.0
    time_attribute: float = 0.0
    time_total: float = 0.0

    spans_total: int = 0
    spans_dialogue: int = 0
    spans_thought: int = 0
    spans_narration: int = 0
    spans_system: int = 0
    spans_meta: int = 0
    spans_section_break: int = 0
    spans_heading: int = 0

    unknown_speakers: int = 0
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 0.0

    rss_mb: float | None = None
    gpu_mem_mb: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable view."""
        return asdict(self)


class Timer:
    """Context manager timer to measure stage durations."""

    def __init__(self) -> None:
        self._t0: float | None = None
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._t0 is not None:
            self.elapsed = time.perf_counter() - self._t0


class MetricsCollector:
    """Collects and persists per-chapter metrics to a JSONL."""

    def __init__(self, jsonl_path: Path | None = None) -> None:
        """Initialize the collector.

        Args:
            jsonl_path: If provided, write one JSON line per chapter here.
        """
        self.jsonl_path = jsonl_path
        self._fh = None
        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.jsonl_path.open("w", encoding="utf-8")

    def close(self) -> None:
        """Close the underlying JSONL file handle."""
        if self._fh:
            self._fh.close()
            self._fh = None

    def write(self, cm: ChapterMetrics) -> None:
        """Write a metrics record as one JSON line."""
        if self._fh:
            self._fh.write(json.dumps(cm.to_dict(), ensure_ascii=False) + os.linesep)
            self._fh.flush()

    @staticmethod
    def sample_resources() -> dict[str, float]:
        """Return current RSS and (if available) GPU memory usage in MB."""
        rss_mb = None
        gpu_mb = None
        if _HAS_PSUTIL:
            p = psutil.Process()
            rss_mb = float(p.memory_info().rss) / (1024 * 1024)
        if _HAS_NVML:
            try:
                h = pynvml.nvmlDeviceGetHandleByIndex(0)
                mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                gpu_mb = float(mem.used) / (1024 * 1024)
            except Exception:
                gpu_mb = None
        out: dict[str, float] = {}
        if rss_mb is not None:
            out["rss_mb"] = rss_mb
        if gpu_mb is not None:
            out["gpu_mem_mb"] = gpu_mb
        return out
