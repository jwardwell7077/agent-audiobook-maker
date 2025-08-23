from __future__ import annotations

from typing import Any, Dict, Optional

try:  # Optional import so repo stays green without LangFlow installed
    from langflow.base.custom import Component  # type: ignore
    from langflow.io import (  # type: ignore
        DataInput,
        IntInput,
        StrInput,
        Output,
    )
    from langflow.schema.data import Data  # type: ignore
except Exception:  # pragma: no cover
    class Component:
        def __init__(self) -> None:
            self.status = ""

        def log(self, msg: str) -> None:
            pass

    class _IO:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class DataInput(_IO):
        pass

    class IntInput(_IO):
        pass

    class StrInput(_IO):
        pass

    class Output:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class Data:
        def __init__(self, data: Any) -> None:
            self.data = data


class ABMChapterSelector(Component):
    """Select a single chapter by index or title substring from a payload.

    Expects a payload shaped like:
    {"book": {...}, "chapters": [{"title": str, ...}, ...]}
    and returns the same shape but with a single chapter in the list.
    """

    display_name = "Chapter Selector"
    description = (
        "Pick one chapter from the chapters list by index or title match."
    )
    icon = "MaterialSymbolsLibraryBooksSharp"
    name = "abm_chapter_selector"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Input payload with book and chapters.",
            required=True,
        ),
        IntInput(
            name="index",
            display_name="Index",
            value=None,
            advanced=True,
            info="0-based index of the chapter to select.",
        ),
        StrInput(
            name="title_contains",
            display_name="Title Contains",
            value=None,
            advanced=True,
            info="Case-insensitive substring to match chapter title.",
        ),
    ]

    outputs = [
        Output(display_name="Payload", name="payload", method="select"),
    ]

    def select(
        self,
        payload: Data,
        index: Optional[int] = None,
        title_contains: Optional[str] = None,
    ) -> Data:
        # Validate input is a mapping
        data = payload.data if isinstance(payload, Data) else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dict-like Data object")

        chapters = data.get("chapters") or []
        if not isinstance(chapters, list):
            chapters = []

        chosen: Optional[Dict[str, Any]] = None

        if isinstance(index, int) and 0 <= index < len(chapters):
            chosen = chapters[index]
        elif title_contains:
            needle = str(title_contains).lower()
            for ch in chapters:
                title = str(ch.get("title", "")).lower()
                if needle in title:
                    chosen = ch
                    break

        # Default to first chapter if nothing matched and list is non-empty
        if chosen is None and chapters:
            chosen = chapters[0]

        out = {
            "book": data.get("book"),
            "chapters": [chosen] if chosen else [],
        }

        self.status = "selected" if chosen else "no match"
        return Data(data=out)
