from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    from langflow.custom import Component  # type: ignore
    from langflow.io import IntInput, StrInput, Output  # type: ignore
    from langflow.schema import Data  # type: ignore
except Exception:  # pragma: no cover
    class Component:
        def __init__(self) -> None:
            self.status = ""

        def log(self, msg: str) -> None:
            pass

    class _IO:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class StrInput(_IO):
        pass

    class IntInput(_IO):
        pass

    class Output:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class Data:
        def __init__(self, data: Any) -> None:
            self.data = data


class ABMChapterVolumeLoader(Component):
    """Load book metadata and chapters from the repo's data folder."""

    display_name = "Chapter Volume Loader"
    description = "Load a specific book's chapters from data/books."
    icon = "MaterialSymbolsFolderOpen"
    name = "abm_chapter_volume_loader"

    inputs = [
        StrInput(
            name="book_id",
            display_name="Book ID",
            value="mvs",
            info="Subfolder name under data/books (e.g., 'mvs').",
        ),
        StrInput(
            name="base_dir",
            display_name="Base Dir",
            value="data/books",
            info="Base directory containing book folders.",
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            value=None,
            advanced=True,
            info="Optional limit of chapters to read.",
        ),
    ]

    outputs = [Output(display_name="Payload", name="payload", method="load")]

    def load(
        self,
        book_id: str = "mvs",
        base_dir: str = "data/books",
        limit: int | None = None,
    ) -> Data:
        book_path = Path(base_dir) / book_id
        chapters_dir = book_path

        chapters: List[Dict[str, Any]] = []
        if chapters_dir.exists():
            for idx, p in enumerate(sorted(chapters_dir.glob("*.txt"))):
                if limit is not None and idx >= int(limit):
                    break
                text = p.read_text(encoding="utf-8", errors="ignore")
                chapters.append({"title": p.stem, "text": text})

        payload = {"book": {"id": book_id}, "chapters": chapters}
        self.status = f"loaded {len(chapters)}"
        return Data(data=payload)
