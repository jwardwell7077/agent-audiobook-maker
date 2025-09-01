"""Command-line interface for the Section Classifier (JSON/JSONL only).

Reads structured input and runs the block-based classifier, then writes four
JSON artifacts to an output directory. This CLI intentionally rejects raw .txt
inputs to enforce a structured boundary.

Accepted inputs:
- .jsonl: One record per line, each an object with a "text" field.
- .json: An object with a top-level key "blocks" containing list[str].

Usage (programmatic):
    from abm.classifier import classifier_cli
    exit_code = classifier_cli.main(["input.jsonl", "out_dir"])  # type: ignore[arg-type]

This mirrors the style of ``pdf_to_text_cli`` but with a strict JSON/JSONL contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from abm.classifier.section_classifier import classify_sections


def _read_blocks_from_jsonl(path: Path) -> list[str]:
    blocks: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - rare
                raise ValueError(f"Invalid JSONL on line {i}: {exc}") from exc
            if not isinstance(obj, dict) or "text" not in obj or not isinstance(obj["text"], str):
                raise ValueError(f"JSONL line {i} must be an object with a string 'text' field")
            blocks.append(obj["text"])
    return blocks


def _read_blocks_from_json(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path.name}: {exc}") from exc
    if not isinstance(data, dict) or "blocks" not in data:
        raise ValueError("JSON input must be an object with top-level 'blocks': list[str]")
    blocks = data["blocks"]
    if not isinstance(blocks, list) or not all(isinstance(b, str) for b in blocks):
        raise ValueError("'blocks' must be list[str]")
    return blocks


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    """Run the classifier CLI.

    Args:
        argv: Command-line arguments, expected ``[input.json|input.jsonl, output_dir]``.
            If None, ``sys.argv[1:]`` is used.
    Returns:
        Process exit code (0 on success, non-zero on error).
    """

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        sys.stderr.write("Usage: classifier_cli <input.json|input.jsonl> <output_dir>\n")
        return 2

    in_path = Path(args[0])
    out_dir = Path(args[1])
    if not in_path.exists() or not in_path.is_file():
        sys.stderr.write(f"Input not found: {in_path}\n")
        return 3

    suffix = in_path.suffix.lower()
    if suffix == ".txt":
        sys.stderr.write("Error: .txt input is not supported. Provide .json or .jsonl with paragraph blocks.\n")
        return 4

    try:
        if suffix == ".jsonl":
            blocks = _read_blocks_from_jsonl(in_path)
        elif suffix == ".json":
            blocks = _read_blocks_from_json(in_path)
        else:
            sys.stderr.write("Unsupported input type. Use .json or .jsonl.\n")
            return 4
    except Exception as exc:
        sys.stderr.write(f"Failed to parse input: {exc}\n")
        return 4

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
