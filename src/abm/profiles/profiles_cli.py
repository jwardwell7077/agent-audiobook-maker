"""CLI helpers for character profile management."""

from __future__ import annotations

import argparse
import json
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
        CharacterProfilesDB.load(path)
    except Exception as exc:  # pragma: no cover - validation details
        print(f"Validation failed: {exc}", file=sys.stderr)
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
        print("Unmapped speakers:" + ", ".join(unmapped))
    if orphan_ids:
        print("Orphan profiles:" + ", ".join(orphan_ids))
    if unmapped or orphan_ids:
        return 1
    print("All speakers mapped")
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

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        return _cmd_validate(args.file)
    if args.cmd == "audit":
        return _cmd_audit(args.roster, args.profiles)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
