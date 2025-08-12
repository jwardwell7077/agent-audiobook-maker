import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
