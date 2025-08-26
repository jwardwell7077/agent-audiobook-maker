from __future__ import annotations

from dataclasses import dataclass

from langflow.custom import Component
from langflow.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    FileInput,
    FloatInput,
    IntInput,
    MultilineInput,
    Output,
    StrInput,
)
from langflow.schema.data import Data
from langflow.schema.message import Message


@dataclass
class _Row:
    item: str


class MasterExample(Component):
    display_name = "Master Example"
    description = "Golden example component showing inputs/outputs APIs."
    icon = "sparkles"
    name = "MasterExample"

    inputs = [
        StrInput(name="title", display_name="Title", value="Demo", required=False, real_time_refresh=True),
        MultilineInput(name="notes", display_name="Notes", value="", required=False),
        BoolInput(name="enabled", display_name="Enabled", value=True, required=False),
        IntInput(name="count", display_name="Count", value=1, required=False),
        FloatInput(name="threshold", display_name="Threshold", value=0.5, required=False),
        DropdownInput(
            name="mode",
            display_name="Mode",
            options=["Message", "Data", "DataFrame"],
            value="Message",
            required=False,
            real_time_refresh=True,
        ),
        StrInput(name="tags", display_name="Tags (comma-separated)", value="", required=False),
        DataInput(name="data_in", display_name="Optional Data Input", required=False),
        FileInput(name="file", display_name="Optional File", required=False),
        StrInput(name="items", display_name="Items (CSV)", value="one,two", required=False),
    ]

    outputs = [
        Output(name="msg_out", display_name="Message", method="build_message"),
        Output(name="data_out", display_name="Data", method="build_data"),
        Output(name="df_out", display_name="DataFrame", method="build_dataframe"),
    ]

    def _items_list(self) -> list[str]:
        raw = getattr(self, "items", "") or ""
        if isinstance(raw, list):
            vals = [str(x).strip() for x in raw]
        else:
            vals = [s.strip() for s in str(raw).split(",")]
        return [v for v in vals if v]

    def _tags_list(self) -> list[str]:
        raw = getattr(self, "tags", "") or ""
        return [s.strip() for s in str(raw).split(",") if s.strip()]

    def build_message(self) -> Message:
        if not getattr(self, "enabled", True):
            self.status = "Disabled; emitted placeholder message."
            return Message(text="(MasterExample disabled)")

        title = getattr(self, "title", "Demo")
        notes = getattr(self, "notes", "")
        items = self._items_list()
        tags = self._tags_list()

        lines: list[str] = [f"Title: {title}"]
        if notes:
            lines.append(notes)
        if items:
            lines.append(f"Items: {', '.join(items)}")
        if tags:
            lines.append(f"Tags: {', '.join(tags)}")
        if getattr(self, "file", None):
            try:
                with open(self.file, encoding="utf-8") as f:  # type: ignore[arg-type]
                    content = f.read().strip()
                lines.append(content)
            except Exception as e:  # pragma: no cover
                lines.append(f"[file read error: {e}]")

        text = "\n".join(lines)
        self.status = "Built Message output."
        return Message(text=text)

    def build_data(self) -> Data:
        items = self._items_list()
        payload = {
            "items": items,
            "count": getattr(self, "count", 0),
            "threshold": getattr(self, "threshold", 0.0),
            "mode": getattr(self, "mode", "Message"),
        }
        self.status = "Built Data output."
        return Data(data=payload)

    def build_dataframe(self) -> Data:
        rows = [_Row(item=x) for x in self._items_list()]
        records = [{"item": r.item} for r in rows]
        self.status = f"Built DataFrame with {len(records)} rows."
        # In current LangFlow, prefer returning Data for tabular payloads
        return Data(data={"rows": records})
