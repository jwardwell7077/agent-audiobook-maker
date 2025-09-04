"""Legacy ABMSpeakerAttribution unit tests (intentionally skipped)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy non-span attribution removed; use ABMSpanAttribution.")


def test_attribute_speaker_dialogue_tag() -> None:  # pragma: no cover - skipped
    assert True


def test_attribute_speaker_non_dialogue() -> None:  # pragma: no cover - skipped
    assert True
