"""CLI helpers for character profile management."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from abm.profiles.character_profiles import CharacterProfilesDB

logger = logging.getLogger(__name__)

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


def _run_alias_resolver(args: argparse.Namespace) -> None:
    """Invoke the alias resolver CLI if the user requested it.

    The resolver is optional and only executed when ``--resolve-aliases`` is
    provided together with the necessary paths.  Errors are propagated to the
    caller so that CI surfaces them as failures.
    """

    if not getattr(args, "resolve_aliases", False):
        return
    if not args.annotations or not args.out_dir:
        raise SystemExit("--annotations and --out-dir required with --resolve-aliases")
    from . import alias_cli

    alias_cli.main(
        [
            "run",
            "--annotations",
            str(args.annotations),
            "--profiles",
            str(args.profiles),
            "--out-dir",
            str(args.out_dir),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``profiles`` CLI."""

    parser = argparse.ArgumentParser(prog="profiles")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate")
    p_val.add_argument("--file", type=Path, required=True)

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--roster", type=Path, required=True)
    p_audit.add_argument("--profiles", type=Path, required=True)

    p_audit.add_argument("--resolve-aliases", action="store_true")
    p_audit.add_argument("--annotations", type=Path)
    p_audit.add_argument("--out-dir", type=Path)
    p_audit.add_argument("--annotations", type=Path, default=None)
    p_audit.add_argument("--eval-after", action="store_true")
    p_audit.add_argument("--eval-dir", default="reports")


    args = parser.parse_args(argv)

    if args.cmd == "validate":
        return _cmd_validate(args.file)
    if args.cmd == "audit":
        rc = _cmd_audit(args.roster, args.profiles)
        if rc == 0:
            _run_alias_resolver(args)
        if args.eval_after and args.annotations:
            cmd = [
                sys.executable,
                "-m",
                "abm.audit",
                "--refined",
                str(args.annotations),
                "--out-dir",
                args.eval_dir or "reports",
                "--title",
                "Eval — profiles audit",
            ]
            try:
                rc = subprocess.run(cmd, check=False).returncode
                if rc:
                    logger.warning("audit exited with code %s", rc)
            except Exception as exc:
                logger.warning("audit skipped: %s", exc)
        return rc
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
