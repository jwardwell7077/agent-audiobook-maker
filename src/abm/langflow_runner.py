from __future__ import annotations

import argparse
from pathlib import Path

from .lf_components import (
    chapter_volume_loader,
    segment_dialogue_narration,
    utterance_jsonl_writer,
)


def run(
    book: str, out_stem: str | None = None, base_dir: str | None = None
) -> str:
    base = Path(base_dir) if base_dir else Path.cwd()
    loaded = chapter_volume_loader.run(book=book, base_dir=str(base))
    segmented = segment_dialogue_narration.run(loaded)
    result = utterance_jsonl_writer.run(
        segmented, base_dir=str(base), stem=out_stem
    )
    return result["path"]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Run segmentation flow deterministically"
    )
    p.add_argument(
        "book",
        help="Short key under data/clean/<book>/chapters.json",
    )
    p.add_argument("--stem", help="Output file stem (default: segments_<ts>)")
    p.add_argument("--base-dir", help="Project base directory", default=None)
    args = p.parse_args(argv)
    path = run(args.book, args.stem, args.base_dir)
    print(path)


if __name__ == "__main__":
    main()
