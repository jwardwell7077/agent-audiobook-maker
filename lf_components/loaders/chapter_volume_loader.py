"""LangFlow component for loading a volume manifest and a selected chapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, IntInput, Output, StrInput


class ChapterVolumeLoader(Component):
    """Load a volume manifest and one chapter JSON from disk.

    Provide either:
    - manifest_path: direct path to real_sample_volume.json
    - directory: folder containing a "*_volume.json" (auto-discovered)

    Relative chapter json_path values are resolved against data_root (if set)
    otherwise the manifest directory.
    """

    display_name = "Chapter Volume Loader"
    description = "Load an existing volume manifest and selected chapter from disk."
    icon = "book"
    name = "ChapterVolumeLoader"

    # ---------- Inputs shown in the LangFlow UI ----------
    inputs = [
        # Option A: Direct path to the manifest JSON file
        StrInput(
            name="manifest_path",
            display_name="Manifest Path (real_sample_volume.json)",
            value="",  # leave empty if you want to use `directory` instead
        ),
        # Option B: Directory containing the manifest; auto-discover pattern
        #   "*_volume.json"
        StrInput(
            name="directory",
            display_name="Directory Containing Manifest",
            value="",  # e.g., /home/jon/repos/.../data/clean/SAMPLE_BOOK
        ),
        # Optional data root to resolve relative chapter json_path values
        StrInput(
            name="data_root",
            display_name="Data Root (optional for relative chapter paths)",
            value="",  # e.g., /home/jon/repos/.../data/clean/SAMPLE_BOOK
        ),
        IntInput(
            name="chapter_index",
            display_name="Chapter Index",
            value=0,
        ),
        BoolInput(
            name="log_debug",
            display_name="Verbose Logs",
            value=True,
        ),
    ]

    # ---------- Outputs (ports) ----------
    outputs = [
        Output(
            name="chapters_index",
            display_name="Chapters Index",
            method="load_chapters_index",
        ),
        Output(
            name="selected_chapter",
            display_name="Selected Chapter",
            method="load_selected_chapter",
        ),
    ]

    # Runtime-injected by LangFlow
    manifest_path: str | None
    directory: str | None
    data_root: str | None
    chapter_index: int | None
    log_debug: bool | None

    # ---------- Helpers ----------
    def _resolve_manifest_path(self) -> Path:
        """Resolve manifest from manifest_path or directory."""
        if self.manifest_path:
            p = Path(str(self.manifest_path)).expanduser()
            if not p.exists():
                raise FileNotFoundError(f"Manifest not found at path: {p}")
            return p

        if self.directory:
            d = Path(str(self.directory)).expanduser()
            if not d.exists():
                raise FileNotFoundError(f"Directory does not exist: {d}")
            # find the newest *_volume.json if multiple exist
            candidates = sorted(d.glob("*_volume.json"))
            if not candidates:
                # also search recursively as a fallback
                candidates = sorted(d.rglob("*_volume.json"))
            if not candidates:
                raise FileNotFoundError(
                    "No '*_volume.json' found in {d} (or subfolders). Provide a Manifest Path or Directory."
                )
            chosen = candidates[-1]
            if self.log_debug:
                self.log(f"[Loader] Using discovered manifest: {chosen}")
            return chosen

        raise ValueError("Provide either Manifest Path or Directory to locate the manifest.")

    def _load_manifest(self) -> dict[str, Any]:
        manifest_path = self._resolve_manifest_path()
        if self.log_debug:
            self.log(f"[Loader] Loading manifest: {manifest_path}")
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["_manifest_path"] = str(manifest_path)
        manifest["_manifest_dir"] = str(manifest_path.parent)
        return manifest

    def _resolve_chapter_path(self, json_path_value: str, manifest_dir: Path) -> Path:
        """Resolve chapter path (absolute or relative)."""
        p = Path(json_path_value)
        if p.is_absolute():
            return p

        # try data_root first if provided
        if self.data_root:
            root = Path(str(self.data_root)).expanduser()
            candidate = (root / p).resolve()
            if candidate.exists():
                return candidate

        # fallback: relative to manifest directory
        candidate = (manifest_dir / p).resolve()
        return candidate

    # ---------- Outputs Implementation ----------
    def load_chapters_index(self) -> list[dict[str, Any]]:  # returns list
        """Return list of chapter metadata dicts from manifest."""
        manifest = self._load_manifest()
        chapters: list[dict[str, Any]] = manifest.get("chapters", [])  # type: ignore[assignment]
        if self.log_debug:
            self.log(f"[Loader] Chapters in manifest: {len(chapters)}")
        return chapters

    def load_selected_chapter(self) -> dict[str, Any]:  # returns plain dict
        """Return full selected chapter JSON payload.

        Raises:
            ValueError: If chapters array missing or index out of range.
            FileNotFoundError: If chapter JSON path cannot be resolved.
        """
        manifest = self._load_manifest()
        chapters: list[dict[str, Any]] = manifest.get("chapters", [])  # type: ignore[assignment]
        if not chapters:
            raise ValueError("Manifest has no 'chapters' array.")

        idx = int(self.chapter_index or 0)
        if idx < 0 or idx >= len(chapters):
            raise ValueError(f"Chapter index {idx} out of range (0..{len(chapters) - 1}).")

        ch_meta = chapters[idx]
        json_path_value = ch_meta.get("json_path")
        if not json_path_value:
            raise ValueError(f"Chapter at index {idx} missing 'json_path'.")

        manifest_dir = Path(manifest["_manifest_dir"])
        chapter_path = self._resolve_chapter_path(json_path_value, manifest_dir)

        if not chapter_path.exists():
            raise FileNotFoundError(
                f"Chapter file not found: {chapter_path}\n"
                f"- json_path in manifest: {json_path_value}\n"
                f"- manifest_dir: {manifest_dir}\n"
                f"- data_root: {self.data_root or '(none)'}"
            )

        if self.log_debug:
            self.log(f"[Loader] Loading chapter {idx} from: {chapter_path}")

        with chapter_path.open("r", encoding="utf-8") as f:
            chapter = json.load(f)

        return chapter
