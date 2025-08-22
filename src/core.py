"""Core utilities.

This module hosts small, well-documented helpers that we can test to keep
the quality gate healthy while larger components are designed.
"""

from __future__ import annotations


def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Args:
        a: First integer operand.
        b: Second integer operand.

    Returns:
        The sum of ``a`` and ``b``.
    """

    return a + b
