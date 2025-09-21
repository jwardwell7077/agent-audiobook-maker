from __future__ import annotations

import json
from typing import Iterable, List, Sequence

import orjson
from tqdm import tqdm

from .extract import first_mentions
from .llm_client import LLMClient
from .prompt_templates import character_prompt
from .schema import CharacterProfile, CharacterSeed
from .textutils import normalize_ws


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        parts = stripped.split("\n", 1)
        if len(parts) == 2:
            inner = parts[1]
            if inner.endswith("```"):
                inner = inner[: -3]
            return inner.strip()
    return stripped


def _coerce_traits(value: object) -> List[str]:
    if isinstance(value, list):
        cleaned: List[str] = []
        for item in value:
            normalized = normalize_ws(str(item))
            if normalized:
                cleaned.append(normalized)
        return cleaned
    if isinstance(value, str):
        cleaned: List[str] = []
        for part in value.replace(";", ",").split(","):
            normalized = normalize_ws(part)
            if normalized:
                cleaned.append(normalized)
        return cleaned
    return []


def _coerce_optional_str(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        normalized = normalize_ws(value)
        if not normalized:
            return "unknown"
        return "unknown" if normalized.lower() == "unknown" else normalized
    return "unknown"


def _parse_response(raw: str) -> dict[str, object]:
    candidate = _strip_code_fence(raw)
    try:
        return orjson.loads(candidate)
    except orjson.JSONDecodeError:
        pass

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        fragment = candidate[start : end + 1]
        try:
            return json.loads(fragment)
        except json.JSONDecodeError:
            pass
    return {}


def build_character_profile(
    chapters: Sequence[dict[str, str]],
    seed: CharacterSeed,
    client: LLMClient,
    max_hits: int = 5,
    sent_window: int = 1,
) -> CharacterProfile:
    evidence = first_mentions(chapters, seed, max_hits=max_hits, sent_window=sent_window)
    prompt = character_prompt(seed.name, evidence)
    response_text = client.generate_sync(prompt)
    parsed = _parse_response(response_text)

    profile_data: dict[str, object] = {
        "name": seed.name,
        "gender": _coerce_optional_str(parsed.get("gender")),
        "approx_age": _coerce_optional_str(parsed.get("approx_age")),
        "nationality_or_accent_hint": _coerce_optional_str(parsed.get("nationality_or_accent_hint")),
        "role_in_story": _coerce_optional_str(parsed.get("role_in_story")),
        "traits_dialogue": _coerce_traits(parsed.get("traits_dialogue")),
        "pacing": _coerce_optional_str(parsed.get("pacing")),
        "energy": _coerce_optional_str(parsed.get("energy")),
        "voice_register": _coerce_optional_str(parsed.get("voice_register")),
        "notes": {},
        "first_mentions_evidence": list(evidence),
    }

    raw_notes = parsed.get("notes")
    if isinstance(raw_notes, dict):
        profile_data["notes"] = {str(k): normalize_ws(str(v)) for k, v in raw_notes.items()}

    return CharacterProfile(**profile_data)


def build_all(
    chapters: Sequence[dict[str, str]],
    seeds: Iterable[CharacterSeed],
    client: LLMClient,
    max_hits: int = 5,
    sent_window: int = 1,
) -> List[CharacterProfile]:
    seed_list = list(seeds)
    profiles: List[CharacterProfile] = []
    for seed in tqdm(seed_list, desc="Building profiles", unit="character"):
        profile = build_character_profile(
            chapters,
            seed,
            client,
            max_hits=max_hits,
            sent_window=sent_window,
        )
        profiles.append(profile)
    return profiles


__all__ = ["build_character_profile", "build_all"]
