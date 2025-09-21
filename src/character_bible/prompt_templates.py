from __future__ import annotations

from typing import Iterable

from .schema import EvidenceSnippet
from .textutils import normalize_ws


def _format_evidence(evidence: Iterable[EvidenceSnippet]) -> str:
    lines = []
    for snippet in evidence:
        meta_parts = []
        if snippet.chapter:
            meta_parts.append(snippet.chapter)
        if snippet.location:
            meta_parts.append(snippet.location)
        header = " - ".join(meta_parts)
        body = normalize_ws(snippet.text)
        if header:
            lines.append(f"{header}\n{body}")
        else:
            lines.append(body)
    return "\n\n".join(lines)


def character_prompt(name: str, evidence: Iterable[EvidenceSnippet]) -> str:
    """Construct the LLM prompt for generating a character profile."""
    evidence_block = _format_evidence(evidence)
    if not evidence_block:
        evidence_block = "No direct evidence was found. Use 'unknown' for unsupported fields."

    prompt = f"""System: You are a careful literary analyst. Extract character facts ONLY from the provided evidence. Do not invent new details.
User: Build a character-bible entry for {name} from the evidence below.
Evidence excerpts (chronological, earliest first):

{evidence_block}

Output JSON with these keys only:
{{"name": "...","gender": "...","approx_age": "...","nationality_or_accent_hint": "...","role_in_story":"...","traits_dialogue":["..."],"pacing":"...","energy":"...","voice_register":"...","notes":{{}}}}
Rules: If a field is not supported by evidence, set it to "unknown". Keep descriptions concise and neutral. Avoid brand/model voice names.
"""
    return prompt


__all__ = ["character_prompt"]
