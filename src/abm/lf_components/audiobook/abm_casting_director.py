"""ABM Casting Director for LangFlow.

Assigns a TTS voice to each utterance based on a voice bank file and/or a
deterministic fallback palette. Outputs enriched utterances including
`voice` metadata and simple summaries of assignments.

Works directly with the normalized payload from ABM Results → Utterances.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data


class ABMCastingDirector(Component):
    display_name = "ABM Casting Director"
    description = "Assign TTS voices to utterances using a voice bank or fallback palette"
    icon = "user-voice"
    name = "ABMCastingDirector"

    inputs = [
        DataInput(
            name="utterances_data",
            display_name="Utterances Data",
            info="Normalized utterances from ABM Results → Utterances",
            required=True,
        ),
        StrInput(
            name="voice_bank_path",
            display_name="Voice Bank Path",
            info="JSON file with voice definitions and optional speaker assignments",
            value="data/casting/voice_bank.json",
            required=False,
        ),
        StrInput(
            name="default_voice_id",
            display_name="Default Voice ID",
            info="Used for unknown/empty speakers if not found in bank",
            value="builtin:narrator_1",
            required=False,
        ),
        BoolInput(
            name="strict_mode",
            display_name="Strict Mode",
            info="If true, unknown speakers raise an error instead of using fallback",
            value=False,
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Enriched Utterances", name="enriched_utterances", method="assign_voices"),
    ]

    # Built-in fallback palette (vendor-agnostic IDs)
    _PALETTE: list[dict[str, Any]] = [
        {"id": "builtin:narrator_1", "vendor": "builtin", "model": "neutral", "style": "narration"},
        {"id": "builtin:voice_m1", "vendor": "builtin", "model": "neutral", "style": "male"},
        {"id": "builtin:voice_f1", "vendor": "builtin", "model": "neutral", "style": "female"},
        {"id": "builtin:voice_m2", "vendor": "builtin", "model": "neutral", "style": "male"},
        {"id": "builtin:voice_f2", "vendor": "builtin", "model": "neutral", "style": "female"},
    ]

    def _load_voice_bank(self, path: str | None) -> dict[str, Any]:
        if not path:
            return {}
        p = Path(path)
        if not p.exists() or p.is_dir():
            return {}
        try:
            text = p.read_text(encoding="utf-8").strip()
            if not text:
                return {}
            return json.loads(text)
        except Exception:
            return {}

    def _hash_index(self, key: str, modulo: int) -> int:
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(h, 16) % max(1, modulo)

    def _palette_pick(self, speaker: str) -> dict[str, Any]:
        idx = self._hash_index(speaker or "unknown", len(self._PALETTE))
        return self._PALETTE[idx]

    def _resolve_voice_for_speaker(self, speaker: str, bank: dict[str, Any], default_voice_id: str) -> dict[str, Any]:
        speaker_norm = (speaker or "").strip()
        # 1) Direct assignment map
        assignments = (bank.get("assignments") or {}) if isinstance(bank, dict) else {}
        voices: list[dict[str, Any]] = (bank.get("voices") or []) if isinstance(bank, dict) else []
        voice_by_id = {v.get("id"): v for v in voices if isinstance(v, dict) and v.get("id")}

        # Exact speaker match
        assigned_id = assignments.get(speaker_norm)
        if assigned_id and assigned_id in voice_by_id:
            return voice_by_id[assigned_id]

        # Label match (aliases)
        for v in voices:
            labels = [str(x).strip().lower() for x in (v.get("labels") or [])]
            if speaker_norm.lower() in labels:
                return v

        # Defaults in bank
        defaults = bank.get("defaults") or {}
        default_id = defaults.get("unknown") or default_voice_id
        if default_id in voice_by_id:
            return voice_by_id[default_id]

        # Fallback to palette (deterministic by name)
        return self._palette_pick(speaker_norm or "unknown")

    def assign_voices(self) -> Data:
        payload = self.utterances_data.data
        if "error" in payload:
            self.status = "Input contains error, passing through"
            return Data(data=payload)

        utterances: list[dict[str, Any]] = list(payload.get("utterances") or [])
        if not isinstance(utterances, list):
            error = "Invalid utterances payload"
            self.status = f"Error: {error}"
            return Data(data={"error": error})

        bank = self._load_voice_bank(self.voice_bank_path)

        speakers_to_voices: dict[str, dict[str, Any]] = {}
        voices_used_counter: dict[str, int] = {}

        enriched: list[dict[str, Any]] = []
        for u in utterances:
            speaker = (u.get("speaker") or "").strip()
            if not speaker:
                if self.strict_mode:
                    error = "Empty speaker in utterance and strict_mode is enabled"
                    self.status = f"Error: {error}"
                    return Data(data={"error": error, "utterance": u})
                voice = self._resolve_voice_for_speaker("unknown", bank, self.default_voice_id)
            else:
                if speaker not in speakers_to_voices:
                    speakers_to_voices[speaker] = self._resolve_voice_for_speaker(speaker, bank, self.default_voice_id)
                voice = speakers_to_voices[speaker]

            voice_id = voice.get("id", "unknown")
            voices_used_counter[voice_id] = voices_used_counter.get(voice_id, 0) + 1

            enriched.append({**u, "voice": voice})

        result = {
            "utterances": enriched,
            "speakers_to_voices": {k: v.get("id") for k, v in speakers_to_voices.items()},
            "voices_used": voices_used_counter,
            "voice_bank_path": self.voice_bank_path,
        }

        self.status = f"Assigned voices to {len(enriched)} utterances (speakers: {len(speakers_to_voices)})"
        return Data(data=result)
