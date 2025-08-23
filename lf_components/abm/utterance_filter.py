from __future__ import annotations

from typing import Any, Dict, List, Optional

from langflow.custom import Component
from langflow.io import (
    BoolInput,
    DataInput,
    IntInput,
    StrInput,
    Output,
)
from langflow.schema import Data


class ABMUtteranceFilter(Component):
    """Filter utterances array by role, length, or substring and return
    payload.
    """

    display_name = "Utterance Filter"
    description = (
        "Filter utterances by speaker role, token length, or substring match."
    )
    icon = "MaterialSymbolsFilterList"
    name = "abm_utterance_filter"

    inputs = [
        DataInput(
            name="payload",
            display_name="Payload",
            info="Input payload containing an 'utterances' list.",
            required=True,
        ),
        StrInput(
            name="role",
            display_name="Role",
            value=None,
            advanced=True,
            info="Keep only utterances with this role (exact match).",
        ),
        IntInput(
            name="min_len",
            display_name="Min Length",
            value=None,
            advanced=True,
            info="Minimum length of text (characters).",
        ),
        IntInput(
            name="max_len",
            display_name="Max Length",
            value=None,
            advanced=True,
            info="Maximum length of text (characters).",
        ),
        StrInput(
            name="contains",
            display_name="Contains",
            value=None,
            advanced=True,
            info="Case-insensitive substring to require in text.",
        ),
        BoolInput(
            name="keep_empty",
            display_name="Keep Empty",
            value=False,
            advanced=True,
            info="Keep items missing 'text' field.",
        ),
    ]

    outputs = [Output(display_name="Payload", name="payload", method="filter")]

    def filter(
        self,
        payload: Data,
        role: Optional[str] = None,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
        contains: Optional[str] = None,
        keep_empty: bool = False,
    ) -> Data:
        data = payload.data if isinstance(payload, Data) else payload
        if not isinstance(data, dict):
            raise ValueError("payload must be a dict-like Data object")

        utterances = data.get("utterances")
        if not isinstance(utterances, list):
            utterances = []

        def pred(u: Dict[str, Any]) -> bool:
            txt = u.get("text")
            if txt is None:
                return bool(keep_empty)
            s = str(txt)
            if role and str(u.get("role")) != role:
                return False
            if min_len is not None and len(s) < int(min_len):
                return False
            if max_len is not None and len(s) > int(max_len):
                return False
            if contains and contains.lower() not in s.lower():
                return False
            return True

        filtered: List[Dict[str, Any]] = [u for u in utterances if pred(u)]

        out = dict(data)
        out["utterances"] = filtered
        self.status = f"kept {len(filtered)}/{len(utterances)}"
        return Data(data=out)
