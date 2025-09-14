"""Utilities for resolving speaker aliases.

This module implements a simplified version of the specification described in
`abm.profiles.alias_resolver`.  The goal is to discover alternative spellings or
forms of speaker names and map them to canonical speakers from the
``CharacterProfilesDB``.

The implementation here focuses on the core offline logic so that other
components can build upon it.  It purposefully avoids network calls and keeps
all behaviour deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Literal, Any

try:  # optional dependency used for phonetic matching
    from metaphone import doublemetaphone  # type: ignore
except Exception:  # pragma: no cover - dependency is optional
    doublemetaphone = None  # type: ignore


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------


@dataclass
class ResolverConfig:
    """Configuration for :mod:`alias_resolver`.

    Only a subset of the fields from the original design are currently used,
    but the structure mirrors the proposed interface so that future extensions
    remain backwards compatible.
    """

    max_edit_dist: int = 2
    phonetic: bool = True
    chargram_dim: int = 256
    tau_auto: float = 0.85
    tau_review: float = 0.65
    use_llm: bool = False
    llm_model: str = "llama3.1:8b-instruct-fp16"
    cache_dir: Path = Path("data/ann/_alias_cache")


@dataclass
class Proposal:
    """Proposed alias mapping."""

    mention: str
    normalized: str
    cluster_id: str
    candidate: str | None
    score: float
    evidence: Dict[str, Any]
    decision: Literal["auto", "review", "reject"]


# ---------------------------------------------------------------------------
# Helpers


_normalise_re = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Return a normalised version of ``name``.

    Normalisation follows a few simple heuristics: lower case, strip
    punctuation, collapse whitespace and drop a leading ``"i "`` pattern used by
    some transcribers.
    """

    name = name.strip().lower()
    if name.startswith("i "):
        name = name[2:]
    name = _normalise_re.sub(" ", name)
    return " ".join(name.split())


def _edit_distance(a: str, b: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""

    if a == b:
        return 0
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        ca = a[i - 1]
        for j in range(1, n + 1):
            cb = b[j - 1]
            cost = 0 if ca == cb else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # deletion
                dp[i][j - 1] + 1,  # insertion
                dp[i - 1][j - 1] + cost,  # substitution
            )
    return dp[m][n]


def _chargram_vector(text: str, dim: int) -> List[float]:
    """Return a simple hashed character n-gram vector."""

    vec = [0.0] * dim
    text = f"  {text}  "  # padding so leading/trailing grams are captured
    for n in range(3, 6):
        for i in range(len(text) - n + 1):
            gram = text[i : i + n]
            idx = hash(gram) % dim
            vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec


def _cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Core stages


def harvest_mentions(refined_json: dict) -> List[str]:
    """Extract speaker mentions from ``refined_json``.

    The structure of ``refined_json`` varies between pipelines.  This function
    looks for dictionaries with a ``speaker`` field and returns all unique values
    encountered.  It falls back to an empty list if nothing can be determined.
    """

    mentions: set[str] = set()

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            spk = obj.get("speaker")
            if isinstance(spk, str):
                mentions.add(spk)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(refined_json)
    return sorted(mentions)


def build_clusters(names: List[str], cfg: ResolverConfig) -> Dict[str, List[str]]:
    """Group names that normalise to the same string.

    The full system would use a BK-tree and phonetic keys.  For this initial
    implementation we simply bucket by the normalised form.
    """

    clusters: Dict[str, List[str]] = {}
    for name in names:
        norm = normalize_name(name)
        clusters.setdefault(norm, []).append(name)
    return clusters


def score_candidate(
    norm: str,
    canonical_list: List[str],
    aliases_map: Dict[str, List[str]],
    cfg: ResolverConfig,
) -> Tuple[str | None, float, Dict[str, Any]]:
    """Return the best candidate canonical speaker and a confidence score."""

    best_score = 0.0
    best_canonical: str | None = None
    evidence: Dict[str, Any] = {}
    mention_vec = _chargram_vector(norm, cfg.chargram_dim)
    mention_meta = doublemetaphone(norm)[0] if doublemetaphone else None

    for canonical in canonical_list:
        c_norm = normalize_name(canonical)
        if norm == c_norm or norm in [normalize_name(a) for a in aliases_map.get(canonical, [])]:
            return canonical, 1.0, {"rules": ["exact"]}

        # edit distance score
        lev = _edit_distance(norm, c_norm)
        if lev > cfg.max_edit_dist:
            lev_score = 0.0
        else:
            lev_score = 1 - (lev / (len(norm) + 1))

        # phonetic bonus
        bonus = 0.0
        if cfg.phonetic and mention_meta and doublemetaphone:
            c_meta = doublemetaphone(c_norm)[0]
            if mention_meta == c_meta:
                bonus += 0.1

        # prefix/suffix bonus
        if c_norm.startswith(norm) or c_norm.endswith(norm):
            bonus += 0.05

        # cosine similarity
        cos = _cosine(mention_vec, _chargram_vector(c_norm, cfg.chargram_dim))

        score = max(lev_score, cos) + bonus
        if score > best_score:
            best_score = min(score, 1.0)
            best_canonical = canonical
            evidence = {
                "rules": [f"edit={lev}", f"cos={cos:.2f}", f"bonus={bonus:.2f}"],
            }
    return best_canonical, best_score, evidence


def propose_aliases(
    refined_json: dict,
    profiles_db: "CharacterProfilesDB",
    cfg: ResolverConfig,
) -> List[Proposal]:
    """Return a list of :class:`Proposal` objects for potential aliases."""
    if cfg.use_llm:
        logger.warning("LLM verification not implemented; skipping")

    mentions = harvest_mentions(refined_json)
    clusters = build_clusters(mentions, cfg)

    canonical_list = list(profiles_db.speaker_map.keys())
    # Build alias map keyed by canonical speaker.  ``CharacterProfilesDB``
    # doesn't track aliases separately, so every speaker is treated as a
    # canonical with no existing aliases.
    aliases_map: Dict[str, List[str]] = {k: [] for k in canonical_list}

    proposals: List[Proposal] = []
    for cluster_id, variants in clusters.items():
        candidate, score, evidence = score_candidate(
            cluster_id, canonical_list, aliases_map, cfg
        )
        decision: Literal["auto", "review", "reject"]
        if score >= cfg.tau_auto:
            decision = "auto"
        elif score >= cfg.tau_review:
            decision = "review"
        else:
            decision = "reject"
        for mention in variants:
            proposals.append(
                Proposal(
                    mention=mention,
                    normalized=cluster_id,
                    cluster_id=cluster_id,
                    candidate=candidate,
                    score=score,
                    evidence=evidence,
                    decision=decision,
                )
            )
    return proposals


def apply_proposals(
    proposals: Iterable[Proposal],
    profiles_db: "CharacterProfilesDB",
) -> "CharacterProfilesDB":
    """Apply auto-accepted proposals to ``profiles_db`` in-place."""

    existing_lower = {k.lower() for k in profiles_db.speaker_map}
    for prop in proposals:
        if prop.decision != "auto" or not prop.candidate:
            continue
        target_profile = profiles_db.speaker_map.get(prop.candidate)
        if not target_profile:
            continue
        if prop.mention.lower() in existing_lower:
            continue
        profiles_db.speaker_map[prop.mention] = target_profile
        existing_lower.add(prop.mention.lower())

    # sort mapping case-insensitively for determinism
    profiles_db.speaker_map = dict(
        sorted(profiles_db.speaker_map.items(), key=lambda kv: kv[0].lower())
    )
    return profiles_db


def save_artifacts(proposals: Iterable[Proposal], out_dir: Path) -> None:
    """Persist proposal information to ``out_dir``.

    * ``proposals.jsonl`` – line-delimited :class:`Proposal` objects.
    * ``alias_patch.yaml`` – mapping suitable for merging into an existing
      speaker map.  Only ``auto`` decisions are written.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    proposals_path = out_dir / "proposals.jsonl"
    with proposals_path.open("w", encoding="utf-8") as f:
        for prop in proposals:
            f.write(json.dumps(prop.__dict__, ensure_ascii=False) + "\n")

    # Build alias patch for autos
    patch: Dict[str, str] = {}
    review: List[Proposal] = []
    for prop in proposals:
        if prop.decision == "auto" and prop.candidate and prop.mention not in patch:
            patch[prop.mention] = prop.candidate
        elif prop.decision == "review":
            review.append(prop)
    if patch:
        yaml_lines = ["# Auto-generated alias patch", "map:"]
        for alias, canonical in sorted(patch.items(), key=lambda kv: kv[0].lower()):
            yaml_lines.append(f"  {alias!r}: {canonical!r}")
        (out_dir / "alias_patch.yaml").write_text("\n".join(yaml_lines), "utf-8")

    # Review queue markdown
    review_lines = ["# Review Queue", "", "| mention | candidate | score |", "|---|---|---|"]
    for prop in review:
        review_lines.append(
            f"|{prop.mention}|{prop.candidate or ''}|{prop.score:.2f}|"
        )
    (out_dir / "review_queue.md").write_text("\n".join(review_lines), "utf-8")


__all__ = [
    "ResolverConfig",
    "Proposal",
    "harvest_mentions",
    "normalize_name",
    "build_clusters",
    "score_candidate",
    "propose_aliases",
    "apply_proposals",
    "save_artifacts",
]
