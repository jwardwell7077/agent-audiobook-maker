#!/usr/bin/env python3
"""Quick docs link checker for relative links in docs/.

Finds Markdown links [text](path) and verifies local paths exist (ignores http/https/mailto).
Prints a summary and up to 50 missing links.
"""
from __future__ import annotations

import os
import re


def main() -> int:
    root = os.path.abspath(os.path.dirname(__file__) + "/..")
    docs_dir = os.path.join(root, "docs")
    md_files: list[str] = []
    for base, _, files in os.walk(docs_dir):
        for f in files:
            if f.endswith(".md"):
                md_files.append(os.path.join(base, f))

    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    missing: list[tuple[str, str]] = []

    for path in md_files:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        for m in link_re.finditer(text):
            href = m.group(1).strip()
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            href = href.split(" ")[0]  # strip title part
            href_no_anchor = href.split("#")[0].strip("`")
            if not href_no_anchor or href_no_anchor.startswith("<"):
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), href_no_anchor))
            if not os.path.exists(resolved):
                missing.append((os.path.relpath(path, root), href))

    print(f"DOC_LINK_FILES {len(md_files)}")
    print(f"DOC_LINK_MISSING_COUNT {len(missing)}")
    for p, h in missing[:50]:
        print(f"- {p}: {h}")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
