"""Command-line interface for the Section Classifier.

Reads a plain text file and splits it into paragraph blocks on blank-line
boundaries, runs the block-based classifier, and writes four JSON artifacts to
an output directory.

Usage (programmatic):
    from abm.classifier import classifier_cli
    exit_code = classifier_cli.main(["input.txt", "out_dir"])  # type:
    # ignore[arg-type]

This mirrors the style of ``pdf_to_text_cli`` for tests and simplicity.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from abm.classifier.section_classifier import classify_sections


def _split_blocks(text: str) -> list[str]:
    """Split input into paragraph blocks by blank-line boundaries."""

    parts = re.split(r"\n\s*\n+", text)
    return [p for p in parts if p and p.strip()]


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

    blocks = _split_blocks(text)
    outputs = classify_sections({"blocks": blocks})

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
            out_dir / "chapters.json",
            outputs["chapters"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "back_matter.json",
            outputs["back_matter"],  # type: ignore[index]
        )
    except Exception as exc:
        sys.stderr.write(f"Failed to write outputs: {exc}\n")
        return 5

    # print a tiny summary to stdout for interactive usage
    sys.stdout.write("Wrote classifier artifacts to " + str(out_dir) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
