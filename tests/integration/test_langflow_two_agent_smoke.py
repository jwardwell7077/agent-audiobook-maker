"""Legacy two-agent smoke test (intentionally skipped)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy two-agent pipeline removed; superseded by spans-first tests.")


def test_two_agent_smoke() -> None:  # pragma: no cover - skipped
    assert True
