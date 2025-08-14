from __future__ import annotations
from langflow.custom import Component
from langflow.io import DictInput, Output
from typing import Any, Dict


class PayloadLogger(Component):
    """Debug helper: logs keys & value types of incoming dict payload."""

    display_name = "Payload Logger"
    description = "Log keys/types of an incoming dict for wiring debug"
    icon = "info"
    name = "PayloadLogger"

    inputs = [
        DictInput(name="payload", display_name="Payload"),
    ]

    outputs = [
        Output(name="echo", display_name="Echo", method="echo"),
    ]

    def echo(self):  # returns the payload unchanged
        payload: Dict[str, Any] = self.payload or {}
        summary = {k: type(v).__name__ for k, v in payload.items()}
        self.log(f"[PayloadLogger] keys/types: {summary}")
        return payload
