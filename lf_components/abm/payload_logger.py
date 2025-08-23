from __future__ import annotations

import json
from typing import Any, Dict, Optional

try:  # Optional import so repo stays green without LangFlow installed
    from langflow.base.custom import Component  # type: ignore
    from langflow.io import (  # type: ignore
        BoolInput,
        DataInput,
        IntInput,
        StrInput,
        Output,
    )
    from langflow.schema.data import Data  # type: ignore
except Exception:  # pragma: no cover - fallback lightweight stubs
    class Component:  # minimal base for subclassing
        def __init__(self) -> None:
            self.status = ""

        def log(self, msg: str) -> None:  # noqa: D401
            pass

    class _IO:
        def __init__(self, *args, **kwargs) -> None:  # noqa: D401
            pass

    class DataInput(_IO):
        pass

    class IntInput(_IO):
        pass

    class StrInput(_IO):
        pass

    class BoolInput(_IO):
        pass

    class Output:
        def __init__(self, *args, **kwargs) -> None:  # noqa: D401
            pass

    class Data:
        def __init__(self, data: Any) -> None:  # noqa: D401
            self.data = data


class ABMPayloadLogger(Component):
    """Attach a compact preview of the payload and optionally echo to logs."""

    display_name = "Payload Logger"
    description = (
        "Append a preview string to payload['log'] and optionally echo."
    )
    icon = "MaterialSymbolsNotes"
    name = "abm_payload_logger"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Any dict-like payload to preview.",
            required=True,
        ),
        StrInput(
            name="preview_key",
            display_name="Preview Key",
            value="utterances",
            info="Key to preview, e.g. 'utterances' or 'chapters'.",
        ),
        IntInput(
            name="max_chars",
            display_name="Max Chars",
            value=400,
            advanced=True,
            info="Maximum preview length.",
        ),
        BoolInput(
            name="echo",
            display_name="Echo",
            value=False,
            advanced=True,
            info="Print preview to component logs.",
        ),
    ]

    outputs = [Output(display_name="Payload", name="payload", method="apply")]

    def apply(
        self,
        payload: Data,
        preview_key: str = "utterances",
        max_chars: int = 400,
        echo: bool = False,
    ) -> Data:
        data = payload.data if isinstance(payload, Data) else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dict-like Data object")

        key = str(preview_key or "")
        val: Optional[Any] = data.get(key)
        snippet = (
            json.dumps(val, ensure_ascii=False) if val is not None else "null"
        )
        if len(snippet) > int(max_chars):
            snippet = snippet[: int(max_chars)] + "…"

        preview = f"{key} preview: {snippet}"
        logs = []
        if isinstance(data.get("log"), list):
            logs = list(data["log"])  # copy
        logs.append(preview)

        out: Dict[str, Any] = dict(data)
        out["log"] = logs

        self.status = f"logged {key}"
        if echo:
            # LangFlow collects component logs; keep it small.
            try:
                self.log(preview)
            except Exception:
                pass
        return Data(data=out)
