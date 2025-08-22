"""Command-line interface for the Section Classifier.

Reads a plain text file that contains book pages joined either by form-feed
characters (``\f``) or by double newlines, converts it into the classifier's
Page objects, runs classification, and writes four JSON artifacts to an
output directory.

Usage (programmatic):
    from abm.classifier import classifier_cli
    exit_code = classifier_cli.main(["input.txt", "out_dir"])  # type:
    # ignore[arg-type]

This mirrors the style of ``pdf_to_text_cli`` for tests and simplicity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

from abm.classifier.section_classifier import classify_sections
from abm.classifier.types import ClassifierInputs, Page


def _split_pages(text: str) -> list[str]:
    """Split the input text into page-sized strings.

    Prefer form-feed (\f) separators when present. Otherwise, treat double
    newlines as page boundaries. Trailing whitespace is stripped.
    """

    if "\f" in text:
        parts = text.split("\f")
    else:
        parts = text.split("\n\n")
    # Normalize line endings and strip outer whitespace per page
    return [p.strip("\n\r ") for p in parts]


def _to_pages(raw_pages: Iterable[str]) -> list[Page]:
    pages: list[Page] = []
    for i, p in enumerate(raw_pages):
        if not p:
            lines: list[str] = []
        else:
            lines = p.splitlines()
        pages.append(Page(page_index=i + 1, lines=lines))
    return pages


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    """Run the classifier CLI.

    Args:
        argv: Command-line arguments, expected ``[input_txt, output_dir]``.
            If None, ``sys.argv[1:]`` is used.
    Returns:
        Process exit code (0 on success, non-zero on error).
    """

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        sys.stderr.write("Usage: classifier_cli <input.txt> <output_dir>\n")
        return 2

    in_path = Path(args[0])
    out_dir = Path(args[1])
    if not in_path.exists() or not in_path.is_file():
        sys.stderr.write(f"Input text not found: {in_path}\n")
        return 3

    try:
        text = in_path.read_text(encoding="utf-8")
    except Exception as exc:
        sys.stderr.write(f"Failed to read input: {exc}\n")
        return 4

    raw_pages = _split_pages(text)
    pages = _to_pages(raw_pages)
    inputs: ClassifierInputs = {"pages": pages}
    outputs = classify_sections(inputs)

    try:
        _write_json(
            out_dir / "front_matter.json",
            outputs["front_matter"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "toc.json",
            outputs["toc"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "chapters_section.json",
            outputs["chapters_section"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "back_matter.json",
            outputs["back_matter"],  # type: ignore[index]
        )
    except Exception as exc:
        sys.stderr.write(f"Failed to write outputs: {exc}\n")
        return 5

    # print a tiny summary to stdout for interactive usage
    sys.stdout.write(
        "Wrote classifier artifacts to " + str(out_dir) + "\n"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
