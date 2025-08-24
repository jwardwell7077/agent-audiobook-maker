#!/usr/bin/env python3
"""
Normalize standalone .mmd Mermaid diagram files for GitHub rendering:
- Remove any Markdown code fences (``` ... ```).
- Convert // and HTML comments to valid Mermaid comments (%%).

This script is idempotent and safe to run multiple times.
"""

from __future__ import annotations

import re
from pathlib import Path

TRIPLE_BACKTICK_RE = re.compile(r"^```.*$")
INLINE_SLASH_SLASH_RE = re.compile(r"(^|[\t\x20])//")


def normalize_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        # Drop any Markdown code fence lines entirely
        if TRIPLE_BACKTICK_RE.match(line):
            continue
        new = line
        # Convert HTML comments to %% comments (inline and whole-line)
        if "<!--" in new:
            new = new.replace("<!--", "%% ")
        if "-->" in new:
            new = new.replace("-->", "")
        # Convert // comments when at SOL or preceded by whitespace
        if "//" in new:
            new = INLINE_SLASH_SLASH_RE.sub(r"\1%%", new)
        out.append(new)
    return out


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    lines = original.splitlines(keepends=False)
    normalized = normalize_lines(lines)
    new_text = "\n".join(normalized)
    if not new_text.endswith("\n"):
        new_text += "\n"
    if new_text != original:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    root = Path(".").resolve()
    mmd_files = [p for p in root.rglob("*.mmd") if p.is_file()]
    modified = []
    for p in mmd_files:
        try:
            if process_file(p):
                modified.append(p)
        except Exception as e:
            print(f"ERROR processing {p}: {e}")
    if modified:
        print("Modified .mmd files:")
        for p in modified:
            print(f" - {p}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
