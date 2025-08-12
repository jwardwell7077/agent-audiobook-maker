from langgraph.pregel import Pregel

from agent import graph, State


def test_graph_instance() -> None:
    assert isinstance(graph, Pregel)


def test_state_defaults() -> None:
    s = State(text="")
    assert s.segments == []
    assert s.notes == []
