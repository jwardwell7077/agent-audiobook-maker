"""Unit tests for graph and state configuration.

Ensures Pregel graph instance and State defaults are as expected.
"""

from langgraph.pregel import Pregel

from agent import State, graph


def test_graph_instance() -> None:
    assert isinstance(graph, Pregel)


def test_state_defaults() -> None:
    s = State(text="")
    assert s.segments == []
    assert s.notes == []
