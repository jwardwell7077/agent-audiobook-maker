"""Convert refined annotations into per-chapter render plans."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from abm.profiles import ProfileConfig, load_profiles
from abm.voice import pick_voice

__all__ = ["build_plans", "main"]

_SENT_RE = re.compile(r"(?<=[.!?…])\s+")


@dataclass
class _Options:
    sample_rate: int
    crossfade_ms: int
    max_chars: int
    pause_defaults: dict[str, int]
    prefer_engine: str


def _split_text(text: str, kind: str, max_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if kind == "Dialogue" and len(text) <= 280:
        return [text]
    if len(text) <= max_chars:
        return [text]
    parts = [p.strip() for p in _SENT_RE.split(text) if p.strip()]
    out: list[str] = []
    for p in parts:
        if len(p) <= max_chars:
            out.append(p)
        else:
            sub = re.split(r"[,;]", p)
            out.extend(s.strip() for s in sub if s.strip())
    return out or [text]


_PUNCT_BONUS = {
    ",": 80,
    ";": 100,
    "—": 120,
    "…": 150,
    "...": 150,
}


def _pause(kind: str, text: str, defaults: dict[str, int]) -> int:
    base = defaults.get(kind, 0)
    t = text.rstrip()
    bonus = 0
    if t.endswith(("...", "…")):
        bonus = _PUNCT_BONUS["..."]
    elif t:
        bonus = _PUNCT_BONUS.get(t[-1], 0)
    bonus = min(200, bonus)
    return base + bonus


def _style_for(kind: str, base: Any) -> dict[str, float]:
    style: dict[str, float] = {"pace": 1.0, "energy": 1.0}
    if isinstance(base, dict):
        style.update({k: float(v) for k, v in base.items() if isinstance(v, (int | float))})
    if kind == "Narration":
        style["pace"] = style.get("pace", 1.0) * 0.98
    if kind == "Thought":
        style["energy"] = style.get("energy", 1.0) * 0.9
    return style


def _process_chapter(ch: dict[str, Any], cfg: ProfileConfig, opt: _Options) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    seg_counter = 0
    for span in ch.get("spans", []):
        kind = span.get("type") or ""
        text = span.get("text", "")
        if not text.strip():
            continue
        pieces = _split_text(text, kind, opt.max_chars)
        decision = pick_voice(cfg, span.get("speaker", ""), preferred_engine=opt.prefer_engine)
        base_style = asdict(decision.style)
        style = _style_for(kind, base_style)
        for piece in pieces:
            seg_counter += 1
            segments.append(
                {
                    "id": f"{ch.get('chapter_index')}-{seg_counter:05d}",
                    "speaker": span.get("speaker"),
                    "kind": kind,
                    "text": piece,
                    "pause_ms": _pause(kind, piece, opt.pause_defaults),
                    "engine": decision.engine,
                    "voice": decision.voice,
                    "description": decision.description,
                    "seed": decision.seed,
                    "style": style,
                    "refs": [],
                    "reason": decision.reason or "exact",
                }
            )
    return {
        "chapter_index": ch.get("chapter_index"),
        "title": ch.get("title", ""),
        "sample_rate": opt.sample_rate,
        "crossfade_ms": opt.crossfade_ms,
        "segments": segments,
    }


def build_plans(
    combined_json: Path,
    cast_profiles: Path,
    out_dir: Path,
    *,
    sample_rate: int,
    crossfade_ms: int,
    max_chars: int,
    pause_narr: int,
    pause_dialog: int,
    pause_thought: int,
    prefer_engine: str,
) -> list[Path]:
    data = json.loads(combined_json.read_text(encoding="utf-8"))
    cfg = load_profiles(cast_profiles)
    opt = _Options(
        sample_rate=sample_rate,
        crossfade_ms=crossfade_ms,
        max_chars=max_chars,
        pause_defaults={
            "Narration": pause_narr,
            "Dialogue": pause_dialog,
            "Thought": pause_thought,
        },
        prefer_engine=prefer_engine,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for ch in data.get("chapters", []):
        plan = _process_chapter(ch, cfg, opt)
        path = out_dir / f"ch_{int(ch.get('chapter_index')):04d}.json"
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input", type=Path, required=True)
    parser.add_argument("--cast", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--sr", type=int, default=48000)
    parser.add_argument("--crossfade-ms", type=int, default=120)
    parser.add_argument("--max-chars", type=int, default=220)
    parser.add_argument("--pause-narr", type=int, default=120)
    parser.add_argument("--pause-dialog", type=int, default=80)
    parser.add_argument("--pause-thought", type=int, default=140)
    parser.add_argument("--prefer-engine", type=str, default="piper")
    parser.add_argument("--only", type=int, default=None, help="Only emit plan for this chapter index")
    parser.add_argument("--verbose", action="store_true", help="Print a brief summary after writing plans")
    args = parser.parse_args(argv)
    # If --only is provided, load JSON, keep a single chapter, and write through
    if args.only is not None:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        keep = []
        for ch in data.get("chapters", []):
            try:
                idx = int(ch.get("chapter_index") or ch.get("index") or 0)
            except Exception:
                idx = 0
            if idx == int(args.only):
                keep = [ch]
                break
        data["chapters"] = keep
        tmp = args.out_dir / ".tmp_only.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        input_path = tmp
    else:
        input_path = args.input

    paths = build_plans(
        input_path,
        args.cast,
        args.out_dir,
        sample_rate=args.sr,
        crossfade_ms=args.crossfade_ms,
        max_chars=args.max_chars,
        pause_narr=args.pause_narr,
        pause_dialog=args.pause_dialog,
        pause_thought=args.pause_thought,
        prefer_engine=args.prefer_engine,
    )
    if args.verbose:
        # Print a tiny summary for convenience
        print(f"Wrote {len(paths)} plan(s) to {args.out_dir}")
        try:
            sample = paths[0]
            segs = json.loads(sample.read_text(encoding="utf-8")).get("segments", [])
            engines = sorted({s.get("engine") for s in segs if s.get("engine")})
            voices = sorted({s.get("voice") for s in segs if s.get("voice")})
            print(f"Sample {sample.name}: {len(segs)} segments; engines={engines[:5]}; voices≈{len(voices)}")
        except Exception:
            pass
