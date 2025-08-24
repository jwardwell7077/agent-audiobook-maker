"""Minimal test component to verify LangFlow discovery."""

from langflow.custom import Component
from langflow.io import StrInput, Output
from langflow.schema import Data


class TestComponent(Component):
    display_name = "Test Component"
    description = "A minimal test component"
    icon = "sparkles"
    name = "TestComponent"

    inputs = [
        StrInput(
            name="test_input",
            display_name="Test Input",
            info="A simple test input",
            value="Hello World"
        )
    ]

    outputs = [
        Output(
            name="test_output",
            display_name="Test Output",
            method="build_output"
        )
    ]

    def build_output(self) -> Data:
        """Simple test method that returns the input."""
        result = f"Processed: {self.test_input}"
        self.status = "Successfully processed input"
        return Data(data={"result": result})
