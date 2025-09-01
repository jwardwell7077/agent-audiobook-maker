from __future__ import annotations

import argparse
from pathlib import Path

from typing import Any

from abm.lf_components.audiobook import abm_chapter_loader
from abm.lf_components.audiobook import abm_utterance_jsonl_writer
try:
    from abm.lf_components.audiobook import abm_segment_dialogue_narration
except Exception:  # pragma: no cover - optional
    abm_segment_dialogue_narration = None  # type: ignore


def run(book: str, out_stem: str | None = None, base_dir: str | None = None) -> str:
    base = Path(base_dir) if base_dir else Path.cwd()
    # Load chapters
    loader = abm_chapter_loader.ABMChapterLoader(book_name=book, base_data_dir=str(base))
    loaded_data = loader.load_chapters().data
    loaded = {"book": book, "chapters": loaded_data.get("chapters", [])}

    # Optionally segment
    if abm_segment_dialogue_narration is None:
        # If the optional component is unavailable, pass through with a compatible structure
        segmented: dict[str, Any] = {"segmented_chapters": [], **loaded}
    else:
        segmented = abm_segment_dialogue_narration.run(loaded)

    # Write JSONL
    result = abm_utterance_jsonl_writer.run(segmented, base_dir=str(base), stem=out_stem)
    return result["path"]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Run segmentation flow deterministically")
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
