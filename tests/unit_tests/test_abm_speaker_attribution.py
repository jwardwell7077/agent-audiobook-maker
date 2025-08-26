"""
Test Agent 2 - ABM Speaker Attribution Component

Basic validation tests for the speaker attribution functionality.
"""

from __future__ import annotations

from abm.lf_components.audiobook.abm_speaker_attribution import ABMSpeakerAttribution


def test_attribute_speaker_dialogue_tag() -> None:
    comp = ABMSpeakerAttribution()
    payload = {
        "classification": "dialogue",
        "dialogue_text": '"Hello there," John said.'
    }
    comp.classified_utterance = type("D", (), {"data": payload})()  # minimal Data-like stub
    out = comp.attribute_speaker().data
    assert out.get("character_name") in {"John", "Unknown"}


def test_attribute_speaker_non_dialogue() -> None:
    comp = ABMSpeakerAttribution()
    payload = {
        "classification": "narration",
        "dialogue_text": "The sun was setting."
    }
    comp.classified_utterance = type("D", (), {"data": payload})()
    out = comp.attribute_speaker().data
    assert out.get("character_name") == "Unknown"
