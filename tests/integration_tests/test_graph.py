import pytest

from agent import graph, State

pytestmark = pytest.mark.anyio


async def test_annotation_graph_basic() -> None:
    state = State(text="Hello world. This is a test. Another sentence.")
    res = await graph.ainvoke(state)
    assert isinstance(res, dict)
    segs = res.get("segments")
    assert segs, "Segments should be produced"
    # handle dataclass instances
    speakers = [getattr(s, "speaker", None) for s in segs]
    assert any(speakers), "Speakers assigned"
    # emotion enabled by default
    assert any(getattr(s, "emotion", None) for s in segs)


async def test_disable_emotion() -> None:
    text = "A. B. C. D. E."
    res_enabled = await graph.ainvoke(State(text=text))
    res_disabled = await graph.ainvoke(
        State(text=text, enable_emotion=False)
    )
    assert any(getattr(s, "emotion", None) for s in res_enabled["segments"])
    assert all(
        getattr(s, "emotion", None) is None for s in res_disabled["segments"]
    )


async def test_max_segments_limit() -> None:
    text = ". ".join([f"Sentence {i}" for i in range(20)])
    res = await graph.ainvoke(State(text=text, max_segments=3))
    assert len(res["segments"]) <= 3


async def test_idempotent_segmentation() -> None:
    text = "First. Second. Third."
    initial = await graph.ainvoke(State(text=text))
    # Re-run starting with existing segments should not add more
    from agent.graph import Segment  # local import to build State

    state_with_segments = State(
        text=text,
        segments=[
            Segment(
                id=s.id,
                text=s.text,
                speaker=None,
            )
            for s in initial["segments"]
        ],
    )
    rerun = await graph.ainvoke(state_with_segments)
    assert len(rerun["segments"]) == len(initial["segments"])
