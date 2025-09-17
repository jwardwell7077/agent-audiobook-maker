"""Post-process a chapter plan to adjust pauses contextually.

Rules (additive, capped):
- Hard stops (., !, ?, …, ...): +160 ms
- Comma/emdash/semicolon: +80–120 ms (same as planner's punctuation bonus, but additive)
- Paragraph/section breaks: if previous kind differs from current and previous had Narration/Heading, +180 ms
- Speaker change: if speaker differs between adjacent segments, +120 ms
- Kind change (Narration <-> Dialogue/Thought): +120 ms

The added pause is applied on top of existing pause_ms and capped at +240 ms extra per segment.

Usage:
  python -m scripts.post_process_plan_padding --in data/ann/mvs/plans/ch_0001.json --out data/ann/mvs/plans/ch_0001_padded.json
  # Or in-place:
  python -m scripts.post_process_plan_padding --in plan.json --in-place
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HARD_STOP_CHARS = (".", "!", "?", "…")


def extra_for_text(text: str, hardstop_ms: int, comma_ms: int) -> int:
    t = (text or "").rstrip()
    if not t:
        return 0
    if t.endswith(("...", "…")):
        return hardstop_ms
    if t[-1] in HARD_STOP_CHARS:
        return hardstop_ms
    if t[-1] in {",", ";", "—"}:
        return comma_ms
    return 0


def post_process(
    plan: dict[str, Any],
    *,
    hardstop_ms: int = 160,
    comma_ms: int = 100,
    speaker_ms: int = 120,
    kind_ms: int = 120,
    paragraph_ms: int = 180,
    cap_ms: int = 240,
    scale: float = 1.0,
    min_ms: int = 0,
    add_ms: int = 0,
) -> dict[str, Any]:
    raw_segments = plan.get("segments", [])
    segs: list[dict[str, Any]] = raw_segments if isinstance(raw_segments, list) else []
    prev = None
    for seg in segs:
        base = int(seg.get("pause_ms", 0))
        extra = 0
        extra += extra_for_text(seg.get("text", ""), hardstop_ms, comma_ms)
        # Speaker change bonus
        if prev and (prev.get("speaker") != seg.get("speaker")):
            extra += speaker_ms
        # Kind change bonus
        if prev and (prev.get("kind") != seg.get("kind")):
            extra += kind_ms
        # Paragraph/section break heuristic: previous Heading/Narration to current Narration/Dialogue
        if (
            prev
            and prev.get("kind") in {"Heading", "Narration"}
            and seg.get("kind")
            in {
                "Narration",
                "Dialogue",
                "Thought",
            }
        ):
            if prev.get("id") and seg.get("id"):
                # Always add a modest pad when transitioning out of headings or long narration blocks
                extra += paragraph_ms
        # Apply scale and cap total extra to prevent runaway spacing
        extra = int(extra * float(scale))
        extra = min(cap_ms, max(0, extra))
        seg["pause_ms"] = max(min_ms, base + extra + int(add_ms))
        prev = seg
    return plan


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, required=True)
    ap.add_argument("--out", dest="out_path", type=Path)
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--hardstop-ms", type=int, default=160)
    ap.add_argument("--comma-ms", type=int, default=100)
    ap.add_argument("--speaker-ms", type=int, default=120)
    ap.add_argument("--kind-ms", type=int, default=120)
    ap.add_argument("--paragraph-ms", type=int, default=180)
    ap.add_argument("--cap-ms", type=int, default=240)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--min-ms", type=int, default=0)
    ap.add_argument("--add-ms", type=int, default=0)
    args = ap.parse_args(argv)
    plan = json.loads(args.in_path.read_text(encoding="utf-8"))
    new_plan = post_process(
        plan,
        hardstop_ms=args.hardstop_ms,
        comma_ms=args.comma_ms,
        speaker_ms=args.speaker_ms,
        kind_ms=args.kind_ms,
        paragraph_ms=args.paragraph_ms,
        cap_ms=args.cap_ms,
        scale=args.scale,
        min_ms=args.min_ms,
        add_ms=args.add_ms,
    )
    if args.in_place:
        args.in_path.write_text(json.dumps(new_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    out_path = args.out_path or args.in_path.with_name(args.in_path.stem + "_padded.json")
    out_path.write_text(json.dumps(new_plan, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
