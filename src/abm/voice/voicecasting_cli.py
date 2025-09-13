from __future__ import annotations

import argparse
from pathlib import Path

from abm.voice.voicecasting import VoiceCasting


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build speaker profiles and a casting plan for TTS.")
    ap.add_argument("--combined", required=True, help="Path to combined (possibly refined) JSON.")
    ap.add_argument("--out-profiles", required=True, help="Path to write speaker_profile.json.")
    ap.add_argument("--out-cast", required=True, help="Path to write casting_plan.json.")
    ap.add_argument("--top-k", type=int, default=16, help="Number of distinct major voices.")
    ap.add_argument("--minor-pool", type=int, default=6, help="Number of pooled minor voices.")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    vc = VoiceCasting(verbose=args.verbose)

    profiles = vc.build_profiles(Path(args.combined))
    vc.write_profiles(profiles, Path(args.out_profiles))

    plan = vc.plan_cast(profiles, top_k=args.top_k, minor_pool_slots=args.minor_pool)
    vc.write_cast(plan, Path(args.out_cast))

    if args.verbose:
        print(f"[voice] wrote {args.out_profiles} and {args.out_cast}")


if __name__ == "__main__":
    main()
