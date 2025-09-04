from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy runner removed (langflow_runner). Optional test skipped.")


def test_langflow_runner_mvs_optional() -> None:  # pragma: no cover - skipped
    assert True
