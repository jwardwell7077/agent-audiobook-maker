from __future__ import annotations

class _BaseIO:
    # Accept arbitrary construction parameters (external library behavior)
    def __init__(self, *args: object, **kwargs: object) -> None: ...

class BoolInput(_BaseIO):
    name: str
    display_name: str

class IntInput(_BaseIO):
    name: str
    display_name: str

class StrInput(_BaseIO):
    name: str
    display_name: str

class DictInput(_BaseIO):
    name: str
    display_name: str

class Output(_BaseIO):
    name: str
    display_name: str
    method: str | None
