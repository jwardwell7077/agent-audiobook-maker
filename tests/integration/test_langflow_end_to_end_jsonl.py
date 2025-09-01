"""Legacy two-agent pipeline test (intentionally skipped)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy two-agent pipeline removed; superseded by spans-first tests.")


def test_end_to_end_jsonl() -> None:  # pragma: no cover - skipped
    assert True
