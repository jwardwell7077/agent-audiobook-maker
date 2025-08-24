#!/usr/bin/env python3
"""
Fix Mermaid comment syntax in Markdown files:
- Inside ```mermaid fenced blocks, convert // comments to %% comments.
- Convert HTML comments <!-- --> inside Mermaid blocks to %% comments.

Heuristics:
- Replace occurrences of (start-of-line or whitespace) // with %% to avoid touching http:// or https://.
- Replace HTML comments by turning '<!--' into '%% ' and removing '-->' tokens.

Only modifies content within mermaid code fences.
"""

from __future__ import annotations

import re
from pathlib import Path

FENCE_START_RE = re.compile(r"^```\s*mermaid\b", re.IGNORECASE)
FENCE_END_RE = re.compile(r"^```\s*$")
INLINE_SLASH_SLASH_RE = re.compile(r"(^|[\t\x20])//")


def fix_block_lines(lines: list[str]) -> list[str]:
    fixed: list[str] = []
    for line in lines:
        new = line
        # Convert HTML comments to %% comments (inline and whole-line)
        if "<!--" in new:
            new = new.replace("<!--", "%% ")
        if "-->" in new:
            new = new.replace("-->", "")
        # Convert // comments when at SOL or preceded by whitespace
        if "//" in new:
            new = INLINE_SLASH_SLASH_RE.sub(r"\1%%", new)
        fixed.append(new)
    return fixed


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=False)
    out: list[str] = []
    i = 0
    changed = False
    n = len(text)

    while i < n:
        line = text[i]
        if FENCE_START_RE.match(line):
            # collect block
            out.append(line)
            i += 1
            block_lines: list[str] = []
            while i < n and not FENCE_END_RE.match(text[i]):
                block_lines.append(text[i])
                i += 1
            fixed_block = fix_block_lines(block_lines)
            if fixed_block != block_lines:
                changed = True
            out.extend(fixed_block)
            # append closing fence if present
            if i < n and FENCE_END_RE.match(text[i]):
                out.append(text[i])
                i += 1
        else:
            out.append(line)
            i += 1

    if changed:
        path.write_text("\n".join(out) + ("\n" if text and not text[-1].endswith("\n") else ""), encoding="utf-8")
    return changed


def main() -> None:
    root = Path(".").resolve()
    md_files = [p for p in root.rglob("*.md") if p.is_file()]
    modified = []
    for p in md_files:
        try:
            if process_file(p):
                modified.append(p)
        except Exception as e:
            print(f"ERROR processing {p}: {e}")
    if modified:
        print("Modified files:")
        for p in modified:
            print(f" - {p}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
