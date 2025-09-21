from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EvidenceSnippet(BaseModel):
    chapter: Optional[str] = None
    location: Optional[str] = None  # e.g., "ch_0003: paragraph 18"
    text: str


class CharacterSeed(BaseModel):
    name: str
    aliases: List[str] = Field(default_factory=list)
    min_mentions: int = 3  # threshold to keep


class CharacterProfile(BaseModel):
    name: str
    gender: Optional[str] = None
    approx_age: Optional[str] = None
    nationality_or_accent_hint: Optional[str] = None
    role_in_story: Optional[str] = None
    traits_dialogue: List[str] = Field(default_factory=list)
    pacing: Optional[str] = None
    energy: Optional[str] = None
    voice_register: Optional[str] = None
    consistency_notes: Optional[str] = "Keep timbre consistent across segments"
    first_mentions_evidence: List[EvidenceSnippet] = Field(default_factory=list)
    notes: Dict[str, str] = Field(default_factory=dict)
