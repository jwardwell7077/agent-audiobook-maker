"""Thin CLI for Chapterizer.

Reads a cleaned text file (with form-feed or double-newline page splits),
runs the chapterizer, and writes a chapters JSON file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from abm.structuring.chapterizer import (
    chapterize_from_text,
    write_chapters_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chapterize a cleaned text file",
    )
    parser.add_argument("input", help="Path to input text (from PDF→Text)")
    parser.add_argument("output", help="Path to output chapters.json")
    parser.add_argument(
        "--dev",
        action="store_true",
        help=(
            "Dev mode: also write a human-readable JSON copy with word-wrapped"
            " body_text (suffix _readable.json) while preserving the main"
            " artifact"
        ),
    )
    args = parser.parse_args(argv)

    in_p = Path(args.input)
    out_p = Path(args.output)
    if not in_p.exists():
        print(f"Input not found: {in_p}")
        return 2
    data = chapterize_from_text(in_p)
    write_chapters_json(out_p, data)
    print(f"Wrote chapters to {out_p}")

    if args.dev:
        # Produce a readability-focused variant with explicit lines
        readable = {
            **data,
            "chapters": [],
        }

        for ch in data.get("chapters", []):
            # Copy all fields; add an explicit array of lines for readability
            new_ch = dict(ch)
            bt = ch.get("body_text", "")
            new_ch["body_lines"] = bt.splitlines()
            readable["chapters"].append(new_ch)

        readable_path = out_p.with_name(
            out_p.stem + "_readable" + out_p.suffix
        )
        write_chapters_json(readable_path, readable)  # reuse pretty writer
        print(f"Wrote readable chapters to {readable_path}")

        # Also emit a plain-text variant with original line endings, grouping
        # by chapter.
        readable_txt_path = out_p.with_name(
            out_p.stem + "_readable.txt"
        )
        lines: list[str] = []
        for ch in readable["chapters"]:
            title = ch.get("title", "")
            idx = ch.get("index", 0)
            lines.append(f"=== Chapter {idx}: {title} ===")
            lines.append("")
            # Append the original body text (no dev-time wrapping)
            body = ch.get("body_text", "")
            lines.append(body)
            lines.append("")
            lines.append("")
        readable_txt_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote readable text to {readable_txt_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
