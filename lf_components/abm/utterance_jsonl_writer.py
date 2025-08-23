from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:  # Optional imports to avoid hard dependency during tests
    from langflow.base.custom import Component  # type: ignore
    from langflow.io import DataInput, StrInput, Output  # type: ignore
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

    class StrInput(_IO):
        pass

    class Output:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class Data:
        def __init__(self, data: Any) -> None:
            self.data = data


class ABMUtteranceJSONLWriter(Component):
    """Write utterances to JSONL and return payload with the output path."""

    display_name = "Utterance JSONL Writer"
    description = "Write utterances to data path and return payload with path."
    icon = "MaterialSymbolsOutput"
    name = "abm_utterance_jsonl_writer"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Payload containing 'utterances' list.",
            required=True,
        ),
        StrInput(
            name="base_dir",
            display_name="Base Dir",
            value="data/clean/mvs",
            info="Base directory for outputs.",
        ),
        StrInput(
            name="stem",
            display_name="Filename Stem",
            value="utterances",
            info="Filename stem, e.g. 'chapter_01'.",
        ),
    ]

    outputs = [Output(display_name="Payload", name="payload", method="write")]

    def write(
        self,
        payload: Data,
        base_dir: str = "data/clean/mvs",
        stem: str = "utterances",
    ) -> Data:
        data = payload.data if isinstance(payload, Data) else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dict-like Data object")
        out_dir = Path(base_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{stem}.jsonl"

        utterances = data.get("utterances") or []
        import json

        with path.open("w", encoding="utf-8") as f:
            for u in utterances:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")

        out: Dict[str, Any] = dict(data)
        out["output_path"] = str(path)
        self.status = f"wrote {len(utterances)}"
        return Data(data=out)
