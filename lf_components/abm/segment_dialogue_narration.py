from __future__ import annotations

from typing import Any, Dict, List

try:
    from langflow.base.custom import Component  # type: ignore
    from langflow.io import DataInput, Output  # type: ignore
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

    class Output:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class Data:
        def __init__(self, data: Any) -> None:
            self.data = data


class ABMSegmentDialogueNarration(Component):
    """Split chapter text into simple dialogue/narration utterances."""

    display_name = "Segment Dialogue/Narration"
    description = "Simple segmentation of chapter text into utterances."
    icon = "MaterialSymbolsLyrics"
    name = "abm_segment_dialogue_narration"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Payload with a single chapter having 'text' field.",
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Payload", name="payload", method="segment")
    ]

    def segment(self, payload: Data) -> Data:
        data = payload.data if isinstance(payload, Data) else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dict-like Data object")

        chapters = data.get("chapters") or []
        text = ""
        if chapters and isinstance(chapters[0], dict):
            text = str(chapters[0].get("text", ""))

        # Naive segmentation: split by lines and tag quotes as dialogue
        utterances: List[Dict[str, Any]] = []
        for line in [t.strip() for t in text.splitlines() if t.strip()]:
            role = (
                "dialogue"
                if line.startswith(("\"", "'")) or line.endswith(("\"", "'"))
                else "narration"
            )
            utterances.append({"role": role, "text": line})

        out: Dict[str, Any] = dict(data)
        out["utterances"] = utterances
        self.status = f"segmented {len(utterances)} lines"
        return Data(data=out)
