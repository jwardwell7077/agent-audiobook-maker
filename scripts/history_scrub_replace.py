#!/usr/bin/env python3
# filter-repo blob callback: replace proprietary tokens with neutral
# SAMPLE_BOOK identifiers.
import sys
_LEGACY_FULL = bytes.fromhex(
    '4d7956616d7069726553797374656d'
)  # legacy full name
_LEGACY_SHORT = b'SB'
TARGETS = [_LEGACY_FULL, _LEGACY_SHORT]
REPLACEMENTS = {_LEGACY_FULL: b'SAMPLE_BOOK', _LEGACY_SHORT: b'SB'}


def replace(content: bytes) -> bytes:
    if _LEGACY_FULL not in content and _LEGACY_SHORT not in content:
        return content
    out = content
    for t in TARGETS:
        out = out.replace(t, REPLACEMENTS[t])
    return out


def main():
    for line in sys.stdin.buffer:
        parts = line.rstrip(b'\n').split(b' ')
        if len(parts) < 3:
            print(line.decode('utf-8').rstrip())
            continue
        typ = parts[1]
        if typ == b'blob':
            data = sys.stdin.buffer.read(int(parts[2]))
            new = replace(data)
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.write(new)
        else:
            sys.stdout.buffer.write(line)


if __name__ == '__main__':
    main()
