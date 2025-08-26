"""Convert raw .txt files into Structured JSON with paragraph splits.

This utility reads a UTF-8 text file where paragraphs are separated by
blank lines (double newlines) and produces a JSON object that preserves
paragraph boundaries for downstream processing.

Outputs one JSON per input text, with fields kept minimal to avoid
guessing metadata. Callers can enrich later.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TxtToStructuredOptions:
    book_id: str
    chapter_id: str
    chapter_index: int = 0
    title: str = ""
    preserve_lines: bool = False


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by blank lines, preserving lines inside.

    Rules:
    - Preserve single newlines within a paragraph (line boundaries).
    - Treat one or more blank lines as a paragraph separator.
    - Trim only trailing carriage returns; preserve spaces inside lines as-is.
    """
    # Normalize CRLF to LF for splitting, preserve content otherwise
    text_lf = text.replace("\r\n", "\n")
    # Split on two or more newlines to define paragraphs; allow extra blanks
    # while ignoring leading/trailing whitespace-only sections.
    raw_paragraphs = [p for p in text_lf.split("\n\n")]
    # Clean up: remove leading/trailing solitary newlines introduced by split
    paragraphs = [p.strip("\n") for p in raw_paragraphs]
    # Drop paragraphs that are entirely empty after cleanup
    return [p for p in paragraphs if p != ""]


def parse_paragraphs_preserve_lines(text: str) -> list[str]:
    """Return paragraphs as physical lines; blank lines are appended to prior item.

    - Each non-empty line becomes its own paragraph entry.
    - A blank line appends a double newline to the previous paragraph (if any).
    - Leading blank lines are ignored; trailing blanks are folded into the last item.
    """
    text_lf = text.replace("\r\n", "\n")
    lines = text_lf.split("\n")
    paragraphs: list[str] = []
    for line in lines:
        if line == "":
            if paragraphs:
                paragraphs[-1] = paragraphs[-1] + "\n\n"
            # else: skip leading blanks
        else:
            paragraphs.append(line)
    return paragraphs


def convert_txt_to_structured(input_txt: str | Path, options: TxtToStructuredOptions) -> dict[str, Any]:
    input_p = Path(input_txt)
    content = input_p.read_text(encoding="utf-8")
    # Keep text exactly (normalize CRLF to LF to be consistent across platforms)
    text_lf = content.replace("\r\n", "\n")
    if options.preserve_lines:
        paragraphs = parse_paragraphs_preserve_lines(text_lf)
    else:
        paragraphs = parse_paragraphs(text_lf)

    # Build the v1.0-like chapter JSON, preserving original text (LF normalized)
    text_out = text_lf

    result: dict[str, Any] = {
        "schema_version": "1.0",
        "book_id": options.book_id,
        "chapter_id": options.chapter_id,
        "index": options.chapter_index,
        "title": options.title,
        "pages": {"start": 0, "end": 0},
        "text": text_out,
        "paragraphs": paragraphs,
        "text_sha256": _sha256_hex(text_out),
        "meta": {"warnings": []},
    }
    return result


def write_structured_json(input_txt: str | Path, output_json: str | Path, options: TxtToStructuredOptions) -> None:
    obj = convert_txt_to_structured(input_txt, options)
    out_p = Path(output_json)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Convert .txt to structured JSON with paragraph splits")
    parser.add_argument("input", help="Path to input .txt file")
    parser.add_argument("output", help="Path to output .json file")
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--chapter-id", required=True)
    parser.add_argument("--chapter-index", type=int, default=0)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    write_structured_json(
        args.input,
        args.output,
        TxtToStructuredOptions(
            book_id=args.book_id,
            chapter_id=args.chapter_id,
            chapter_index=args.chapter_index,
            title=args.title,
        ),
    )
