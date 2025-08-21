from __future__ import annotations

from typing import Any, ClassVar

class Component:
    """Minimal stub of langflow.custom.Component for static type checking.
    Real implementation provides runtime wiring, logging, and execution model.

    Args:
        None (stub class, attributes set by runtime)

    Returns:
        None

    Raises:
        None
    """

    # Common metadata attributes referenced by components
    display_name: ClassVar[str]
    description: ClassVar[str]
    icon: ClassVar[str]
    name: ClassVar[str]

    # Inputs/outputs descriptors: lists of objects (keep as Any for now).
    inputs: ClassVar[list[Any]]
    outputs: ClassVar[list[Any]]

    # Generic payload attributes set dynamically by LangFlow runtime
    def log(self, message: str) -> None: ...
