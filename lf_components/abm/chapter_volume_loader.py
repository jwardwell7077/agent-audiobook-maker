from __future__ import annotations

import json
from pathlib import Path

from langflow.custom import Component
from langflow.io import IntInput, StrInput, Output
from langflow.schema import Data


class ABMChapterVolumeLoader(Component):
    """Load book metadata and chapters from the repo's data/clean folder."""

    display_name = "Chapter Volume Loader"
    description = "Load a specific book's chapters from data/clean structure."
    icon = "MaterialSymbolsFolderOpen"
    name = "abm_chapter_volume_loader"

    inputs = [
        StrInput(
            name="book_id",
            display_name="Book ID",
            value="mvs",
            info="Book ID subfolder (e.g., 'mvs').",
        ),
        StrInput(
            name="base_dir",
            display_name="Base Dir",
            value="data/clean",
            info="Base directory containing book data.",
        ),
        IntInput(
            name="chapter_limit",
            display_name="Chapter Limit",
            value=None,
            advanced=True,
            info="Optional limit of chapters to load (for testing).",
        ),
    ]

    outputs = [Output(display_name="Payload", name="payload", method="load")]

    def load(
        self,
        book_id: str = "mvs",
        base_dir: str = "data/clean",
        chapter_limit: int | None = None,
    ) -> Data:
        """Load chapters from JSON structure in data/clean/{book_id}/."""
        book_path = Path(base_dir) / book_id
        chapters_file = book_path / "chapters.json"
        
        if not chapters_file.exists():
            self.status = f"ERROR: {chapters_file} not found"
            error_msg = f"Chapters file not found: {chapters_file}"
            return Data(data={"error": error_msg})
        
        try:
            with open(chapters_file, "r", encoding="utf-8") as f:
                chapters_data = json.load(f)
            
            chapters = chapters_data.get("chapters", [])
            
            # Apply chapter limit if specified
            if chapter_limit is not None and chapter_limit > 0:
                chapters = chapters[:chapter_limit]
            
            # Create payload compatible with downstream components
            payload = {
                "book_id": book_id,
                "book_metadata": {
                    "id": book_id,
                    "total_chapters": len(chapters),
                    "source_file": str(chapters_file)
                },
                "chapters": chapters
            }
            
            self.status = f"Loaded {len(chapters)} chapters from {book_id}"
            return Data(data=payload)
            
        except json.JSONDecodeError as e:
            self.status = f"ERROR: Invalid JSON in {chapters_file}"
            return Data(data={"error": f"JSON decode error: {e}"})
        except Exception as e:
            self.status = f"ERROR: {str(e)}"
            return Data(data={"error": str(e)})
