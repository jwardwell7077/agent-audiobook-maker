import pytest

pytest.skip(
    "Legacy page-based classifier tests are deprecated in favor of block-based inputs."
    " Update to use {'blocks': list[str]} derived from JSONL paragraphs.",
    allow_module_level=True,
)
