#!/usr/bin/env python3
"""
Demo: Run the spans-first orchestrator with deterministic confidence and an optional threshold.

Usage (optional args):
  python scripts/demo_confidence_orchestrator.py --min 75
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure src/ is importable when running from repo root
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from abm.lf_components.audiobook.abm_artifact_orchestrator import ABMArtifactOrchestrator
except Exception as e:  # pragma: no cover - friendliness for missing deps
    print(
        "Missing dependencies to run orchestrator. Ensure dev env is set up (see README-HOTRELOAD.md) "
        "and install requirements. You can also run scripts/setup-phase1.sh.\n"
        f"Import error: {e}"
    )
    raise SystemExit(2) from e


def _demo_blocks() -> dict[str, Any]:
    # Single block with adjacent narration → dialogue → narration so attribution can use tags
    text = 'Quinn walked in. "Hello there." Bob said.'
    return {
        "book_name": "DEMO_BOOK",
        "chapter_index": 0,
        "blocks": [
            {"text": text},
            {"text": "The door closed behind him."},
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", dest="min_conf", type=int, default=75, help="Min confidence percent for dialogue")
    args = ap.parse_args()

    blocks_data = _demo_blocks()

    orch = ABMArtifactOrchestrator(
        blocks_data=blocks_data,
        write_to_disk=False,
        output_dir="",
        min_confidence_pct=str(args.min_conf),
    )
    result = orch.generate_artifacts().data
    spans_attr = (result.get("spans_attr") or {}).get("spans_attr") or []

    total = len(spans_attr)
    dlg = [s for s in spans_attr if (s.get("role") == "dialogue" or s.get("type") == "dialogue")]
    kept = len(dlg)

    print(f"Orchestrator completed. Threshold={args.min_conf}%")
    print(f"Total spans_attr records: {total}")
    print(f"Dialogue kept: {kept}")
    for s in dlg[:3]:
        name = s.get("character_name")
        conf = (s.get("attribution") or {}).get("confidence")
        txt = s.get("text_norm")
        try:
            conf_s = f"{float(conf if conf is not None else 'nan'):.2f}"
        except Exception:
            conf_s = "?"
        print(f" - {name} @ {conf_s}: {txt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
