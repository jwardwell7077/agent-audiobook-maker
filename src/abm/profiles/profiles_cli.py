"""CLI helpers for character profile management."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from abm.profiles.character_profiles import CharacterProfilesDB

__all__ = ["main"]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _cmd_validate(path: Path) -> int:
    try:
        db = CharacterProfilesDB.load(path)
        issues = db.validate()
    except Exception as exc:  # pragma: no cover - validation details
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    if issues:
        print("Validation failed: " + "; ".join(issues), file=sys.stderr)
        return 1
    print("OK")
    return 0


def _cmd_audit(roster_path: Path, profiles_path: Path) -> int:
    roster = _load_json(roster_path)
    speakers = set(roster.get("speakers", roster))
    db = CharacterProfilesDB.load(profiles_path)
    mapped = set(db.speaker_map.keys())
    unmapped = sorted(speakers - mapped)
    referenced = set(db.speaker_map.values())
    orphan_ids = sorted(set(db.profiles.keys()) - referenced)

    if unmapped:
        print("unmapped=" + ",".join(unmapped))
    if orphan_ids:
        print("orphan=" + ",".join(orphan_ids))
    if unmapped or orphan_ids:
        return 1
    print("ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``profiles`` CLI."""

    parser = argparse.ArgumentParser(prog="profiles")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate")
    p_val.add_argument("--file", type=Path, required=True)

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--roster", type=Path, required=True)
    p_audit.add_argument("--profiles", type=Path, required=True)
    p_audit.add_argument("--annotations", type=Path, default=None)
    p_audit.add_argument("--eval-after", action="store_true")
    p_audit.add_argument("--eval-dir", default="reports")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        return _cmd_validate(args.file)
    if args.cmd == "audit":
        rc = _cmd_audit(args.roster, args.profiles)
        if args.eval_after and args.annotations:
            cmd = [sys.executable, "-m", "abm.audit", "--refined", str(args.annotations), "--out-dir", args.eval_dir, "--title", "Eval — profiles audit"]
            try:
                subprocess.run(cmd, check=False)
            except Exception as e:
                print(f"audit skipped: {e}", file=sys.stderr)
        return rc
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
