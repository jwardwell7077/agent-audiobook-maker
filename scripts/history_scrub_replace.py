#!/usr/bin/env python3
"""Git filter-repo blob callback helper.

Reads lines from stdin as emitted by ``git filter-repo --blob-callback`` and
replaces any legacy proprietary tokens with neutral SAMPLE_BOOK identifiers.
Echoes non-blob lines unchanged; for blobs it rewrites the content bytes.
"""

import sys

_LEGACY_FULL = bytes.fromhex("4d7956616d7069726553797374656d")  # legacy full name
_LEGACY_SHORT = b"SB"
TARGETS = [_LEGACY_FULL, _LEGACY_SHORT]
REPLACEMENTS = {_LEGACY_FULL: b"SAMPLE_BOOK", _LEGACY_SHORT: b"SB"}
_MIN_BLOB_PARTS = 3  # protocol minimum tokens for a blob line


def replace(content: bytes) -> bytes:
    """Return content with legacy markers substituted (if present)."""
    if _LEGACY_FULL not in content and _LEGACY_SHORT not in content:
        return content
    out = content
    for t in TARGETS:
        out = out.replace(t, REPLACEMENTS[t])
    return out


def main() -> None:
    """Stream filter-repo protocol lines from stdin and apply replacements."""
    for line in sys.stdin.buffer:
        parts = line.rstrip(b"\n").split(b" ")
        if len(parts) < _MIN_BLOB_PARTS:  # passthrough unexpected formatting
            sys.stdout.buffer.write(line)
            continue
        if parts[1] == b"blob":
            size = int(parts[2])
            data = sys.stdin.buffer.read(size)
            new = replace(data)
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.write(new)
        else:
            sys.stdout.buffer.write(line)


if __name__ == "__main__":
    main()
