from __future__ import annotations

import argparse
from pathlib import Path

from abm.annotate.llm_prep import LLMCandidateConfig, LLMCandidatePreparer


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Prepare candidates JSONL for LLM refinement.")
    ap.add_argument("--in", dest="input", required=True, help="Path to combined.json (or combined_bnlp.json)")
    ap.add_argument("--out", dest="out", required=True, help="Path to write spans_for_llm.jsonl")
    ap.add_argument("--conf-threshold", type=float, default=0.90, help="Min confidence to skip LLM (default 0.90)")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = LLMCandidateConfig(conf_threshold=args.conf_threshold)
    prep = LLMCandidatePreparer(cfg)

    doc = Path(args.input).read_text(encoding="utf-8")
    import json

    candidates = prep.prepare(json.loads(doc))
    LLMCandidatePreparer().write_jsonl(Path(args.out), candidates)

    print(f"[llm_prep] wrote {len(candidates)} candidates → {args.out}")


if __name__ == "__main__":
    main()
