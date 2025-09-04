from __future__ import annotations

import sys
from pathlib import Path

# Ensure workspace root is importable so `components` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure src/ is on sys.path so we can import abm.* without using `import src.*` patterns.
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
