"""Minimal Echo component for LangFlow discovery health."""

from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data


class ABMEcho(Component):
    display_name = "ABM Echo"
    description = "Echo back the provided text"
    icon = "message-circle"
    name = "ABMEcho"

    inputs = [
        MessageTextInput(name="text", display_name="Text", value="hello"),
    ]
    outputs = [
        Output(name="echo", display_name="Echo", method="build"),
    ]

    def build(self, **kwargs):  # noqa: ANN003
        return Data(data={"text": self.text})
