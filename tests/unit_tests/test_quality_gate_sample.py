def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        Sum of a and b.
    """
    return a + b


def test_add_happy_path() -> None:
    assert add(2, 3) == 5


def test_add_edge_zero() -> None:
    assert add(0, 0) == 0
