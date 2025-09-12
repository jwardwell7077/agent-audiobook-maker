from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abm.sidecar.booknlp_adapter import BookNLPAdapter


@dataclass
class BNLPRefinePolicy:
    """Policy to accept or fuse BookNLP attribution."""

    accept_when_rule_unknown_min_prob: float = 0.70
    boost_when_agree_to_conf: float = 0.97
    max_char_gap: int = 40  # allow small offset drift when matching quotes


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _match_quotes(
    spans: list[dict[str, Any]],
    bnlp: list[dict[str, Any]],
    max_char_gap: int,
) -> dict[tuple[int, int], dict[str, Any]]:
    """Greedy match BookNLP quotes to our spans by max char overlap / small gap."""
    index: dict[tuple[int, int], dict[str, Any]] = {}
    bnlp_sorted = sorted(bnlp, key=lambda q: (q["start"], q["end"]))
    for s in spans:
        if s.get("type") not in {"Dialogue", "Thought"}:
            continue
        a = (int(s["start"]), int(s["end"]))
        best: dict[str, Any] | None = None
        best_ol = 0
        for q in bnlp_sorted:
            b = (int(q["start"]), int(q["end"]))
            ol = _overlap(a, b)
            if ol > best_ol or (ol == 0 and abs(a[0] - b[0]) <= max_char_gap):
                best = q
                best_ol = ol
        if best is not None:
            index[a] = best
    return index


def refine_with_bnlp(tagged_path: Path, out_path: Path, *, policy: BNLPRefinePolicy, verbose: bool = False) -> None:
    doc = json.loads(tagged_path.read_text(encoding="utf-8"))

    adapter = BookNLPAdapter(verbose=verbose)
    if not adapter.enabled():
        if verbose:
            print("[bnlp] BookNLP not available; copying input → output")
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    changed = 0
    total = 0

    for ch in doc.get("chapters", []):
        text = ch.get("text", "") or "\n".join(ch.get("paragraphs", []))
        bnlp_quotes = adapter.annotate_text(text, work_id=f"ch_{ch.get('chapter_index', 'x')}")
        if not bnlp_quotes:
            continue

        mapping = _match_quotes(ch.get("spans", []), bnlp_quotes, policy.max_char_gap)

        for s in ch.get("spans", []):
            if s.get("type") not in {"Dialogue", "Thought"}:
                continue
            total += 1
            key = (int(s["start"]), int(s["end"]))
            q = mapping.get(key)
            if not q:
                continue

            b_speaker = (q.get("speaker") or "Unknown").strip() or "Unknown"
            b_prob = float(q.get("prob") or 0.0)

            rule_speaker = s.get("speaker", "Unknown")
            rule_conf = float(s.get("confidence", 0.0))

            if (
                rule_speaker == "Unknown"
                and b_speaker != "Unknown"
                and b_prob >= policy.accept_when_rule_unknown_min_prob
            ):
                s["speaker"] = b_speaker
                s["method"] = "neural:booknlp"
                s["confidence"] = max(rule_conf, min(0.90, b_prob))
                changed += 1
            elif rule_speaker == b_speaker and b_speaker != "Unknown":
                # agree → boost confidence (cap to 0.97)
                if rule_conf < policy.boost_when_agree_to_conf:
                    s["method"] = "fuse:rule+booknlp"
                    s["confidence"] = policy.boost_when_agree_to_conf
                    changed += 1
            # else: keep rule; Stage B (LLM) will arbitrate

    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if verbose:
        print(f"[bnlp] modified spans: {changed}/{total}")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fuse BookNLP quote attribution into Stage-A combined.json.")
    ap.add_argument("--tagged", required=True, help="Path to Stage-A combined.json")
    ap.add_argument("--out", required=True, help="Path to write BNLP-fused JSON")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    refine_with_bnlp(Path(args.tagged), Path(args.out), policy=BNLPRefinePolicy(), verbose=args.verbose)


if __name__ == "__main__":
    main()
