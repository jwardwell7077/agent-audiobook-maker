"""ABM Span Casting (LangFlow Component).

Assign TTS voices to spans (dialogue/narration) using a voice bank and
 deterministic fallback palette. Accepts spans with attribution when available
 (character_name/character_id) and falls back to role-based mapping.
 Optionally writes spans_cast.jsonl + spans_cast.meta.json to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data


class ABMSpanCasting(Component):
    display_name = "ABM Span Casting"
    description = "Assign voices to spans using a voice bank or deterministic palette"
    icon = "user-voice"
    name = "ABMSpanCasting"

    inputs = [
        DataInput(
            name="spans_in",
            display_name="Spans (classified/attributed)",
            info="From ABMSpanAttribution.spans_attr or ABMSpanClassifier.spans_cls",
            required=True,
        ),
        StrInput(
            name="voice_bank_path",
            display_name="Voice Bank Path",
            value="data/casting/voice_bank.json",
            required=False,
        ),
        StrInput(
            name="default_voice_id",
            display_name="Default Voice ID",
            value="builtin:narrator_1",
            required=False,
        ),
        BoolInput(
            name="strict_mode",
            display_name="Strict Mode",
            info="If true, unknown speakers raise an error",
            value=False,
            required=False,
        ),
        BoolInput(
            name="write_to_disk",
            display_name="Write JSONL + meta to disk",
            value=False,
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            info="If empty, defaults to output/{book_id}/ch{chapter_number:02d}",
            value="",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Casted Spans", name="spans_cast", method="assign_voices"),
    ]

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
        except Exception:  # noqa: BLE001
            return {}

    def _hash_index(self, key: str, modulo: int) -> int:
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(h, 16) % max(1, modulo)

    def _palette_pick(self, speaker: str) -> dict[str, Any]:
        idx = self._hash_index(speaker or "unknown", len(self._PALETTE))
        return self._PALETTE[idx]

    def _resolve_voice(self, speaker: str, bank: dict[str, Any], default_voice_id: str) -> dict[str, Any]:
        speaker_norm = (speaker or "").strip()
        assignments = (bank.get("assignments") or {}) if isinstance(bank, dict) else {}
        voices: list[dict[str, Any]] = (bank.get("voices") or []) if isinstance(bank, dict) else []
        voice_by_id = {v.get("id"): v for v in voices if isinstance(v, dict) and v.get("id")}

        assigned_id = assignments.get(speaker_norm)
        if assigned_id and assigned_id in voice_by_id:
            return voice_by_id[assigned_id]

        for v in voices:
            labels = [str(x).strip().lower() for x in (v.get("labels") or [])]
            if speaker_norm.lower() in labels:
                return v

        defaults = bank.get("defaults") or {}
        default_id = defaults.get("unknown") or default_voice_id
        if default_id in voice_by_id:
            return voice_by_id[default_id]

        return self._palette_pick(speaker_norm or "unknown")

    def _speaker_from_span(self, s: dict[str, Any]) -> str:
        # Prefer explicit attribution
        name = s.get("character_name") or s.get("speaker")
        if name:
            return str(name)
        # Fallbacks: narration -> Narrator, dialogue without attribution -> Unknown
        t = (s.get("type") or s.get("role") or "").lower()
        if t == "narration":
            return "Narrator"
        return "Unknown"

    def assign_voices(self) -> Data:
        # Input payload shape: {"spans_attr": [...]} or {"spans_cls": [...]} or {"spans": [...]}
        src = getattr(self, "spans_in", None)
        if src is None:
            err = "spans_in is required"
            self.status = f"Error: {err}"
            return Data(data={"error": err})

        payload = src.data if hasattr(src, "data") else src
        if not isinstance(payload, dict):
            payload = {}

        spans = payload.get("spans_attr") or payload.get("spans_cls") or payload.get("spans") or []
        # Also accept a single-span payload from ABMSpanIterator (key: 'span')
        if (not spans) and payload.get("span"):
            spans = [payload.get("span")]
        if not isinstance(spans, list):
            err = "Invalid spans payload"
            self.status = f"Error: {err}"
            return Data(data={"error": err})
        # Ensure list of dicts
        spans = [s for s in spans if isinstance(s, dict)]

        bank = self._load_voice_bank(getattr(self, "voice_bank_path", None))
        strict = bool(getattr(self, "strict_mode", False))
        default_voice_id = getattr(self, "default_voice_id", "builtin:narrator_1")

        casted: list[dict[str, Any]] = []
        voices_used: dict[str, int] = {}
        speakers_to_voices: dict[str, str] = {}

        for s in spans:
            speaker = self._speaker_from_span(s)
            if not speaker or speaker == "Unknown":
                if strict:
                    self.status = "Error: Unknown speaker and strict_mode is enabled"
                    return Data(data={"error": "Unknown speaker", "span": s})
            voice = self._resolve_voice(speaker or "unknown", bank, default_voice_id)
            voice_id = voice.get("id", "unknown")
            voices_used[voice_id] = voices_used.get(voice_id, 0) + 1
            speakers_to_voices.setdefault(speaker, voice_id)

            casted.append({**s, "voice": voice})

        # Try to infer outdir for optional write
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir and casted:
            s0 = casted[0]
            book_id = s0.get("book_id", "UNKNOWN_BOOK")
            chnum = int(s0.get("chapter_number", (s0.get("chapter_index") or 0) + 1))
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")

        if bool(getattr(self, "write_to_disk", False)) and outdir:
            Path(outdir).mkdir(parents=True, exist_ok=True)
            p = Path(outdir) / "spans_cast.jsonl"
            meta_p = Path(outdir) / "spans_cast.meta.json"
            with p.open("w", encoding="utf-8") as f:
                for rec in casted:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            with meta_p.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "component": self.name,
                        "voices_used": voices_used,
                        "speakers_to_voices": speakers_to_voices,
                        "voice_bank_path": getattr(self, "voice_bank_path", None),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        self.status = f"Assigned voices to {len(casted)} spans (speakers: {len(speakers_to_voices)})"
        return Data(
            data={
                "spans_cast": casted,
                "voices_used": voices_used,
                "speakers_to_voices": speakers_to_voices,
                "voice_bank_path": getattr(self, "voice_bank_path", None),
            }
        )
