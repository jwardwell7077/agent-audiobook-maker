"""LangFlow component that logs keys and value types of an incoming payload."""

from __future__ import annotations

from typing import Any

from langflow.custom import Component
from langflow.io import DictInput, Output


class PayloadLogger(Component):
    """Log keys/types of a dict payload for wiring debug in flows."""

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

    # Runtime-injected by LangFlow
    payload: dict[str, Any] | None

    def echo(self) -> dict[str, Any]:  # returns the payload unchanged
        """Return payload unchanged while emitting a summarized log line."""
        payload: dict[str, Any] = self.payload or {}
        summary = {k: type(v).__name__ for k, v in payload.items()}
        self.log(f"[PayloadLogger] keys/types: {summary}")
        return payload
