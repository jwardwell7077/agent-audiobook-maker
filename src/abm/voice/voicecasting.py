from __future__ import annotations
# isort: skip_file

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any


_GENDER_TITLES = {
    "mr": "male",
    "sir": "male",
    "lord": "male",
    "king": "male",
    "prince": "male",
    "duke": "male",
    "father": "male",
    "mister": "male",
    "sir.": "male",
    "mrs": "female",
    "ms": "female",
    "miss": "female",
    "lady": "female",
    "queen": "female",
    "princess": "female",
    "duchess": "female",
    "mother": "female",
    "madam": "female",
}
_RANK_TITLES = {"sergeant", "captain", "major", "general", "lieutenant", "commander", "private", "agent", "professor"}


@dataclass
class VoiceHints:
    gender: str | None = None
    age: str | None = None
    accent: str | None = None
    role: str | None = None  # e.g., 'military', 'student', 'villain'
    style_tags: list[str] = field(default_factory=list)


@dataclass
class SpeakerProfile:
    speaker: str
    lines: int
    first_seen_ch: int | None
    titles: list[str] = field(default_factory=list)
    hints: VoiceHints = field(default_factory=VoiceHints)
    example_quotes: list[str] = field(default_factory=list)


@dataclass
class CastingPlan:
    """Map speakers to voice slots; cluster minor roles to a small pool."""

    top_k: int = 16
    minor_pool_slots: int = 6
    # Result fields:
    voices: dict[str, dict[str, Any]] = field(default_factory=dict)  # slot_id -> config
    assign: dict[str, str] = field(default_factory=dict)  # speaker -> slot_id


class VoiceCasting:
    """Derive voice profiles and a casting plan from the combined annotations."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose

    # ---------------------- public API ---------------------- #

    def build_profiles(self, combined_json: Path) -> dict[str, SpeakerProfile]:
        """Aggregate per-speaker metadata from Stage-A/Stage-B combined file."""
        data = json.loads(combined_json.read_text(encoding="utf-8"))
        # Count lines per speaker, collect first seen chapter and example quotes
        counts: Counter[str] = Counter()
        first_seen: dict[str, int] = {}
        examples: dict[str, list[str]] = defaultdict(list)

        for ch in data.get("chapters", []):
            ch_idx = int(ch.get("chapter_index", -1))
            for s in ch.get("spans", []):
                if s.get("type") not in {"Dialogue", "Thought"}:
                    continue
                spk = s.get("speaker") or "Unknown"
                counts[spk] += 1
                first_seen.setdefault(spk, ch_idx)
                if len(examples[spk]) < 3:
                    examples[spk].append(s.get("text", "")[:180])

        profiles: dict[str, SpeakerProfile] = {}
        for spk, n in counts.most_common():
            titles = self._extract_titles(spk)
            hints = self._infer_hints(spk, titles)
            profiles[spk] = SpeakerProfile(
                speaker=spk,
                lines=n,
                first_seen_ch=first_seen.get(spk),
                titles=titles,
                hints=hints,
                example_quotes=examples.get(spk, []),
            )
        return profiles

    def plan_cast(
        self,
        profiles: dict[str, SpeakerProfile],
        *,
        top_k: int = 16,
        minor_pool_slots: int = 6,
    ) -> CastingPlan:
        """Assign voice slots to top speakers; pool the rest."""
        plan = CastingPlan(top_k=top_k, minor_pool_slots=minor_pool_slots)
        # Sort by importance (lines desc, earlier first seen)
        ordered = sorted(
            profiles.values(),
            key=lambda p: (-p.lines, p.first_seen_ch if p.first_seen_ch is not None else 1_000_000),
        )

        # Major roles
        for i, p in enumerate(ordered[:top_k], start=1):
            slot = f"main_{i:02d}"
            plan.assign[p.speaker] = slot
            plan.voices[slot] = self._slot_from_profile(p)

        # Minor roles pooled
        pool_ids = [f"minor_{i:02d}" for i in range(1, minor_pool_slots + 1)]
        pool_idx = 0
        for p in ordered[top_k:]:
            slot = pool_ids[pool_idx % len(pool_ids)]
            plan.assign[p.speaker] = slot
            pool_idx += 1
        # Fill pool slot configs with semi-generic tags
        for sid in pool_ids:
            if sid not in plan.voices:
                plan.voices[sid] = {
                    "gender": "neutral",
                    "age": "adult",
                    "accent": None,
                    "style_tags": ["supporting"],
                    "tts_preset": "default_support",
                }
        return plan

    # ---------------------- persistence --------------------- #

    @staticmethod
    def write_profiles(profiles: dict[str, SpeakerProfile], out_path: Path) -> None:
        out = {
            spk: {
                "speaker": p.speaker,
                "lines": p.lines,
                "first_seen_ch": p.first_seen_ch,
                "titles": p.titles,
                "hints": {
                    "gender": p.hints.gender,
                    "age": p.hints.age,
                    "accent": p.hints.accent,
                    "role": p.hints.role,
                    "style_tags": p.hints.style_tags,
                },
                "example_quotes": p.example_quotes,
            }
            for spk, p in profiles.items()
        }
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def write_cast(plan: CastingPlan, out_path: Path) -> None:
        out = {
            "voices": plan.voices,
            "assign": plan.assign,
            "top_k": plan.top_k,
            "minor_pool_slots": plan.minor_pool_slots,
        }
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------------- heuristics ---------------------- #

    @staticmethod
    def _extract_titles(speaker: str) -> list[str]:
        s = speaker.lower()
        return [
            t
            for t in sorted(_RANK_TITLES | set(_GENDER_TITLES.keys()), key=len, reverse=True)
            if re.search(rf"\b{re.escape(t)}\.?\b", s)
        ]

    @staticmethod
    def _infer_hints(speaker: str, titles: list[str]) -> VoiceHints:
        """Simple deterministic hints from name/titles."""
        g = None
        for t in titles:
            if t in _GENDER_TITLES:
                g = _GENDER_TITLES[t]
                break
        # age guess: very coarse
        age = "adult"
        # role guess
        role = "military" if any(t in _RANK_TITLES for t in titles) else None
        style = ["major"] if any(k in speaker.lower() for k in ("king", "queen", "leader")) else []
        return VoiceHints(gender=g, age=age, accent=None, role=role, style_tags=style)

    @staticmethod
    def _slot_from_profile(p: SpeakerProfile) -> dict[str, Any]:
        hints = p.hints
        return {
            "gender": hints.gender or "neutral",
            "age": hints.age or "adult",
            "accent": hints.accent,
            "role": hints.role,
            "style_tags": ["lead"] + (hints.style_tags or []),
            # Hook for your TTS engine selection:
            "tts_preset": f"default_{(hints.gender or 'neutral')}",
        }
