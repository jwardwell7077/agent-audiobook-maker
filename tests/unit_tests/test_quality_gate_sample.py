from core import add


def test_add_happy_path() -> None:
    assert add(2, 3) == 5


def test_add_edge_zero() -> None:
    assert add(0, 0) == 0
