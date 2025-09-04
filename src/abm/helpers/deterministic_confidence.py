"""Deterministic confidence scoring helper (non-LangFlow component)."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any


@dataclass
class DeterministicConfidenceConfig:
    w_dialogue_tag: float = 3.0
    w_proper_noun_proximity: float = 1.5
    w_continuity_prev_same: float = 0.75
    w_adjacent_narration_present: float = 0.25
    sigmoid_scale: float = 0.6
    min_confidence: float = 0.35
    max_confidence: float = 0.95
    # Narration-specific knobs
    narration_sigmoid_scale: float = 0.6
    narration_min_confidence: float = 0.6
    narration_max_confidence: float = 0.99
    w_narration_no_quotes: float = 0.8
    w_narration_has_quotes: float = -2.0
    w_narration_adjacent_dialogue: float = -0.3
    w_narration_narration_verbs: float = 0.4
    w_narration_long_sentence: float = 0.2


class DeterministicConfidenceScorer:
    def __init__(self, config: DeterministicConfidenceConfig | None = None):
        self.config = config or DeterministicConfidenceConfig()

    def score(
        self,
        *,
        dialogue_text: str,
        before_text: str | None,
        after_text: str | None,
        detected_method: str | None,
        detected_speaker: str | None,
        prev_dialogue_speaker: str | None,
        detection_distance: int | None = None,
    ) -> tuple[float, dict[str, Any], str]:
        cfg = self.config
        features: dict[str, float] = {}
        # Distance decay: downweight detections farther away from the dialogue span
        # base^max(distance-1,0) so immediate neighbor (1) = 1.0
        distance_decay_base = 0.8
        dd = 1.0
        if detection_distance is not None and detection_distance > 1:
            dd = distance_decay_base ** (detection_distance - 1)

        if detected_method == "dialogue_tag":
            features["dialogue_tag"] = cfg.w_dialogue_tag * dd
        elif detected_method == "proper_noun_proximity":
            features["proper_noun_proximity"] = cfg.w_proper_noun_proximity * dd

        if detected_speaker and prev_dialogue_speaker and detected_speaker == prev_dialogue_speaker:
            features["continuity_prev_same"] = cfg.w_continuity_prev_same

        if before_text or after_text:
            features["adjacent_narration_present"] = cfg.w_adjacent_narration_present

        raw_score = sum(features.values())

        k = cfg.sigmoid_scale
        logistic = 1.0 / (1.0 + exp(-k * raw_score))
        conf = cfg.min_confidence + (cfg.max_confidence - cfg.min_confidence) * logistic
        conf = max(cfg.min_confidence, min(cfg.max_confidence, conf))

        evidence = {
            "confidence_method": "deterministic_v1",
            "raw_score": raw_score,
            "features": features,
            "params": {
                "sigmoid_scale": cfg.sigmoid_scale,
                "min": cfg.min_confidence,
                "max": cfg.max_confidence,
            },
            "detection_distance": detection_distance,
        }

        return float(conf), evidence, "deterministic_v1"

    def score_narration(
        self,
        *,
        narration_text: str,
        before_text: str | None,
        after_text: str | None,
        before_is_dialogue: bool,
        after_is_dialogue: bool,
    ) -> tuple[float, dict[str, Any], str]:
        """Evidence-based confidence for narration spans.

        Higher when text clearly lacks quotes and reads like narration; lower when quotes appear
        or surrounded by dialogue (possible mislabel).
        """
        cfg = self.config
        t = (narration_text or "").strip()
        has_quotes = ('"' in t) or ("'" in t and t.count("'") >= 2)
        no_quotes = not has_quotes
        length_tokens = max(1, len(t.split()))

        features: dict[str, float] = {}
        if no_quotes:
            features["no_quotes"] = cfg.w_narration_no_quotes
        if has_quotes:
            features["has_quotes"] = cfg.w_narration_has_quotes
        if before_is_dialogue or after_is_dialogue:
            features["adjacent_dialogue"] = cfg.w_narration_adjacent_dialogue

        # Simple narration verb hint (weak positive)
        verbs = ("walked", "looked", "thought", "remembered", "asked", "replied", "said", "whispered")
        # Even though some appear as speech verbs, their presence without quotes is still narrative-like.
        if any(v in t.lower() for v in verbs) and no_quotes:
            features["narration_verbs"] = cfg.w_narration_narration_verbs

        if length_tokens >= 8 and no_quotes:
            features["long_sentence"] = cfg.w_narration_long_sentence

        raw_score = sum(features.values())
        k = cfg.narration_sigmoid_scale
        logistic = 1.0 / (1.0 + exp(-k * raw_score))
        conf = cfg.narration_min_confidence + (cfg.narration_max_confidence - cfg.narration_min_confidence) * logistic
        conf = max(cfg.narration_min_confidence, min(cfg.narration_max_confidence, conf))

        evidence = {
            "confidence_method": "deterministic_narration_v1",
            "raw_score": raw_score,
            "features": features,
            "params": {
                "sigmoid_scale": cfg.narration_sigmoid_scale,
                "min": cfg.narration_min_confidence,
                "max": cfg.narration_max_confidence,
            },
        }
        return float(conf), evidence, "deterministic_narration_v1"
