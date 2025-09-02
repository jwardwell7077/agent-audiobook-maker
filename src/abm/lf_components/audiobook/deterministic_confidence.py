"""Deterministic confidence scoring for span speaker attribution.

This scorer computes a confidence value in [0,1] using simple, explainable
features from local context and prior continuity. Intended to be stable and
configurable via weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any


@dataclass
class DeterministicConfidenceConfig:
    # Feature weights (tune conservatively; monotonic mapping to [0,1])
    w_dialogue_tag: float = 3.0
    w_proper_noun_proximity: float = 1.5
    w_continuity_prev_same: float = 0.75
    w_adjacent_narration_present: float = 0.25
    # Logistic scale
    sigmoid_scale: float = 0.6
    # Clamp to a friendly range to avoid 0/1 extremes
    min_confidence: float = 0.35
    max_confidence: float = 0.95


class DeterministicConfidenceScorer:
    def __init__(self, config: DeterministicConfidenceConfig | None = None):
        self.config = config or DeterministicConfidenceConfig()

    def score(
        self,
        *,
        dialogue_text: str,
        before_text: str | None,
        after_text: str | None,
        detected_method: str | None,  # e.g., "dialogue_tag" | "proper_noun_proximity" | None
        detected_speaker: str | None,
        prev_dialogue_speaker: str | None,
    ) -> tuple[float, dict[str, Any], str]:
        """Return (confidence, evidence, method_name).

        method_name is the confidence method (not the speaker detection method).
        """
        cfg = self.config
        features: dict[str, float] = {}

        # Primary detection signals
        if detected_method == "dialogue_tag":
            features["dialogue_tag"] = cfg.w_dialogue_tag
        elif detected_method == "proper_noun_proximity":
            features["proper_noun_proximity"] = cfg.w_proper_noun_proximity

        # Continuity: if the same speaker continues, boost a bit
        if detected_speaker and prev_dialogue_speaker and detected_speaker == prev_dialogue_speaker:
            features["continuity_prev_same"] = cfg.w_continuity_prev_same

        # Presence of adjacent narration at all is a small positive signal of context
        if before_text or after_text:
            features["adjacent_narration_present"] = cfg.w_adjacent_narration_present

        raw_score = sum(features.values())

        # Map via logistic, then clamp to [min, max]
        # logistic(x) = 1/(1+e^{-k x}), use k=sigmoid_scale
        k = cfg.sigmoid_scale
        logistic = 1.0 / (1.0 + exp(-k * raw_score))
        # Now scale to [min, max]
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
        }

        return float(conf), evidence, "deterministic_v1"
