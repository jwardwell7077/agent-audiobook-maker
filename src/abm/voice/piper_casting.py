"""Propose Piper voice casting for book characters.

This tool leverages existing profiles and annotations to suggest a mapping from
characters to Piper voices:

- Enumerates installed Piper voices (via piper_catalog)
- Loads current profiles and the refined annotations
- Picks a small audition line per character
- Writes a proposed casting YAML and a review markdown with commands to audition

All outputs go under an ignored directory (reports/ by default) so nothing leaks
into version control.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore

    HAVE_YAML = True
except Exception:  # pragma: no cover - optional dependency missing
    yaml = None
    HAVE_YAML = False

from abm.profiles import load_profiles
from abm.voice.piper_catalog import PiperVoice, discover_piper_voices


@dataclass(slots=True)
class AuditionLine:
    speaker: str
    text: str


def _collect_characters(annotations: Path, max_chars: int | None = None) -> list[str]:
    data = json.loads(annotations.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for ch in data.get("chapters", []):
        for s in ch.get("spans", []):
            if s.get("type") in {"Dialogue", "Thought"}:
                sp = s.get("speaker")
                if not sp:
                    continue
                counts[sp] = counts.get(sp, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    names = [k for k, _ in ordered]
    if max_chars is not None:
        names = names[:max_chars]
    return names


def _pick_audition_lines(annotations: Path, speakers: list[str], max_chars: int = 12) -> list[AuditionLine]:
    """Pick one short line per speaker as an audition text."""

    data = json.loads(annotations.read_text(encoding="utf-8"))
    out: list[AuditionLine] = []
    remaining = set(speakers[:max_chars])
    for ch in data.get("chapters", []):
        for s in ch.get("spans", []):
            if not remaining:
                return out
            if s.get("type") in {"Dialogue", "Thought"}:
                sp = s.get("speaker")
                text = (s.get("text") or "").strip()
                if sp in remaining and 20 <= len(text) <= 140:
                    out.append(AuditionLine(speaker=sp, text=text))
                    remaining.remove(sp)
    # Fallback: if some remain, take any line even if length bounds not met
    if remaining:
        for ch in data.get("chapters", []):
            for s in ch.get("spans", []):
                if not remaining:
                    break
                if s.get("type") in {"Dialogue", "Thought"} and s.get("speaker") in remaining:
                    out.append(AuditionLine(speaker=s.get("speaker"), text=(s.get("text") or "").strip()))
                    remaining.remove(s.get("speaker"))
            if not remaining:
                break
    return out


def _render_review_md(out_dir: Path, lines: list[AuditionLine], voices: list[PiperVoice], engine: str = "piper") -> str:
    """Produce a small review markdown with suggested cli trials."""

    rows = [
        "# Piper Casting Review",
        "",
        f"Total voices discovered: {len(voices)}",
        "",
        "Try auditioning a few combinations (replace voice as needed):",
        "",
    ]
    if not voices:
        rows.append("No Piper voices discovered. Install voices and re-run catalog/proposal.")
        return "\n".join(rows)

    # Use the first discovered voice as an example; user can swap IDs or paths
    v0 = voices[0]
    m_arg = f'-m "{v0.model_path}"'
    c_arg = f' -c "{v0.config_path}"' if v0.config_path else ""
    for ln in lines:
        safe = ln.speaker.replace(" ", "_")
        out = out_dir / "auditions" / f"{safe}_{v0.id.replace('/', '-')}.wav"
        text = (ln.text[:80] + "...") if len(ln.text) > 80 else ln.text
        cmd = f'echo "{text}" | piper --quiet {m_arg}{c_arg} -f "{out}"'
        rows.append(f"- {ln.speaker}: {cmd}")
    return "\n".join(rows)


def propose_casting(
    profiles_path: Path,
    annotations_path: Path,
    out_dir: Path,
    *,
    engine: str = "piper",
    max_chars: int = 12,
) -> dict[str, Any]:
    """Generate a simple casting proposal scaffold.

    Returns a summary dictionary with discovered voices and selected characters.
    """

    cfg = load_profiles(profiles_path)
    voices = discover_piper_voices()
    chars = _collect_characters(annotations_path, max_chars=max_chars)
    lines = _pick_audition_lines(annotations_path, chars, max_chars=max_chars)

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "engine": engine,
        "voices": [v.id for v in voices],
        "characters": chars,
        "audition_lines": [{"speaker": a.speaker, "text": a.text} for a in lines],
    }

    # Proposed YAML scaffold: keep existing voice if set, else blank to fill
    if HAVE_YAML and yaml is not None:
        # Seed voices with existing mapping where available; else blank for manual fill-in
        speakers_block = {sp: {"engine": engine, "voice": ""} for sp in chars}
        proposed = {
            "version": 1,
            "defaults": {
                "engine": engine,
                "narrator_voice": cfg.defaults_narrator_voice,
                "style": {
                    "pace": cfg.defaults_style.pace,
                    "energy": cfg.defaults_style.energy,
                    "pitch": cfg.defaults_style.pitch,
                    "emotion": cfg.defaults_style.emotion,
                },
            },
            "voices": {engine: [v.id for v in voices]},
            "speakers": speakers_block,
        }
        (out_dir / "casting_proposed.yaml").write_text(yaml.safe_dump(proposed, sort_keys=False), encoding="utf-8")

    (out_dir / "casting_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "REVIEW.md").write_text(_render_review_md(out_dir, lines, voices), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="piper_casting", description="Propose Piper casting for characters")
    ap.add_argument("--profiles", required=True, type=Path)
    ap.add_argument("--annotations", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="Output directory (ignored by git)")
    ap.add_argument("--engine", default="piper")
    ap.add_argument("--max-chars", type=int, default=12)
    ns = ap.parse_args(argv)

    propose_casting(ns.profiles, ns.annotations, ns.out, engine=ns.engine, max_chars=ns.max_chars)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
