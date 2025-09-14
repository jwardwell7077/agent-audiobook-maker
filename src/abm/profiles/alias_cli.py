"""CLI entry points for the alias resolver.

The command line interface is intentionally lightweight.  It exposes three
sub-commands – ``discover``, ``apply`` and ``run`` – mirroring the behaviour
from the project specification.  ``discover`` analyses annotations and writes
proposal artefacts, ``apply`` applies auto-approved proposals to the profiles
file, and ``run`` performs both steps in one go.

The implementation here focuses on determinism and offline operation.  The
optional LLM verification mentioned in the design is not implemented, but the
command line flags are accepted so that future versions can hook into the same
interface.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

from abm.profiles.character_profiles import CharacterProfilesDB
from .alias_resolver import (
    Proposal,
    ResolverConfig,
    apply_proposals,
    propose_aliases,
    save_artifacts,
)

__all__ = ["main"]


# ---------------------------------------------------------------------------
# Utilities


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_profiles(path: Path) -> CharacterProfilesDB:
    return CharacterProfilesDB.load(path)


def _save_profiles(db: CharacterProfilesDB, path: Path) -> None:
    db.save(path)


def _proposals_from_file(path: Path) -> List[Proposal]:
    proposals: List[Proposal] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            proposals.append(Proposal(**data))
    return proposals


# ---------------------------------------------------------------------------
# Command handlers


def _cmd_discover(args: argparse.Namespace) -> int:
    cfg = ResolverConfig(
        tau_auto=args.tau_auto,
        tau_review=args.tau_review,
        use_llm=args.use_llm,
        llm_model=args.model,
    )
    refined = _load_json(args.annotations)
    profiles = _load_profiles(args.profiles)
    proposals = propose_aliases(refined, profiles, cfg)
    save_artifacts(proposals, args.out_dir)
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    profiles = _load_profiles(args.profiles)
    proposals = _proposals_from_file(args.proposals)
    apply_proposals(proposals, profiles)
    _save_profiles(profiles, args.profiles)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = ResolverConfig(
        tau_auto=args.tau_auto,
        tau_review=args.tau_review,
        use_llm=args.use_llm,
        llm_model=args.model,
    )
    refined = _load_json(args.annotations)
    profiles = _load_profiles(args.profiles)
    proposals = propose_aliases(refined, profiles, cfg)
    apply_proposals(proposals, profiles)
    save_artifacts(proposals, args.out_dir)
    _save_profiles(profiles, args.profiles)
    return 0


# ---------------------------------------------------------------------------
# CLI entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="alias_cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dis = sub.add_parser("discover")
    p_dis.add_argument("--annotations", type=Path, required=True)
    p_dis.add_argument("--profiles", type=Path, required=True)
    p_dis.add_argument("--out-dir", type=Path, required=True)
    p_dis.add_argument("--tau-auto", type=float, default=0.85)
    p_dis.add_argument("--tau-review", type=float, default=0.65)
    p_dis.add_argument("--use-llm", action="store_true")
    p_dis.add_argument("--model", type=str, default="llama3.1:8b-instruct-fp16")

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--proposals", type=Path, required=True)
    p_apply.add_argument("--profiles", type=Path, required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--annotations", type=Path, required=True)
    p_run.add_argument("--profiles", type=Path, required=True)
    p_run.add_argument("--out-dir", type=Path, required=True)
    p_run.add_argument("--tau-auto", type=float, default=0.85)
    p_run.add_argument("--tau-review", type=float, default=0.65)
    p_run.add_argument("--use-llm", action="store_true")
    p_run.add_argument("--model", type=str, default="llama3.1:8b-instruct-fp16")

    args = parser.parse_args(argv)
    if args.cmd == "discover":
        return _cmd_discover(args)
    if args.cmd == "apply":
        return _cmd_apply(args)
    if args.cmd == "run":
        return _cmd_run(args)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
