"""ABM Chapter Volume Loader Component for LangFlow."""

from __future__ import annotations

import json
from pathlib import Path

from langflow.custom import Component
from langflow.io import IntInput, Output, StrInput
from langflow.schema import Data


class ABMChapterVolumeLoader(Component):
    display_name = "ABM Chapter Volume Loader"
    description = "Load chapters from a book volume for audiobook processing"
    icon = "book-open"
    name = "ABMChapterVolumeLoader"

    inputs = [
        StrInput(
            name="book_name",
            display_name="Book Name",
            info="Name of the book to load chapters from",
            value="mvs",
            required=True,
        ),
        IntInput(
            name="volume_number",
            display_name="Volume Number",
            info="Volume number to load (1-based)",
            value=1,
            required=True,
        ),
        StrInput(
            name="base_data_dir",
            display_name="Base Data Directory",
            info="Base directory containing book data",
            value="/home/jon/repos/audio-book-maker-lg/data/clean",
            required=False,
        ),
    ]

    outputs = [Output(name="chapters_data", display_name="Chapters Data", method="load_chapters")]

    def load_chapters(self) -> Data:
        """Load chapters from the specified book and volume."""
        try:
            base_dir = Path(self.base_data_dir)
            chapters_file = base_dir / self.book_name / "chapters.json"

            if not chapters_file.exists():
                error_msg = f"Chapters file not found: {chapters_file}"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})

            with open(chapters_file, encoding="utf-8") as f:
                all_chapters = json.load(f)
            # Filter chapters for the specified volume
            volume_chapters = [chapter for chapter in all_chapters if chapter.get("volume", 1) == self.volume_number]

            if not volume_chapters:
                msg = f"No chapters found for volume {self.volume_number}"
                self.status = f"Warning: {msg}"
                return Data(data={"chapters": [], "volume": self.volume_number})

            result_data = {
                "chapters": volume_chapters,
                "volume": self.volume_number,
                "book": self.book_name,
                "total_chapters": len(volume_chapters),
            }

            status_msg = f"Loaded {len(volume_chapters)} chapters from {self.book_name} volume {self.volume_number}"
            self.status = status_msg
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to load chapters: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})


def run(book: str, base_dir: str) -> dict:
    """Convenience wrapper used by abm.langflow_runner for CLI-style chaining."""
    comp = ABMChapterVolumeLoader()
    comp.book_name = book
    comp.volume_number = 1
    # base_dir is expected to be the project root; chapters live under data/clean/<book>/chapters.json
    comp.base_data_dir = str(Path(base_dir) / "data" / "clean")
    data = comp.load_chapters().data
    # Return a plain dict for downstream non-LangFlow callers
    return data
