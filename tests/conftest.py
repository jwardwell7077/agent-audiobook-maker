from __future__ import annotations

# Ensure src/ is on sys.path so we can import abm.* without using `import src.*` patterns.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
