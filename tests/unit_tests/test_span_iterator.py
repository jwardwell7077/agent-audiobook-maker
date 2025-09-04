from abm.lf_components.audiobook.abm_span_iterator import ABMSpanIterator


def _spans_payload():
    return {
        "spans": [
            {"span_uid": "u0", "role": "narration", "book_id": "b", "chapter_index": 0, "block_id": 0, "segment_id": 0},
            {"span_uid": "u1", "role": "dialogue", "book_id": "b", "chapter_index": 0, "block_id": 0, "segment_id": 1},
            {"span_uid": "u2", "role": "narration", "book_id": "b", "chapter_index": 0, "block_id": 1, "segment_id": 0},
        ]
    }


def test_span_iterator_windowing():
    comp = ABMSpanIterator(spans_data=_spans_payload(), start_span=1, max_spans=1)
    d1 = comp.get_next_span().data
    assert d1["span"]["span_uid"] == "u1"
    # next call should complete
    d2 = comp.get_next_span().data
    assert d2["processing_status"] == "completed"


def test_span_iterator_dialogue_only():
    comp = ABMSpanIterator(spans_data=_spans_payload(), dialogue_only=True)
    d1 = comp.get_next_span().data
    assert d1["span"]["role"] == "dialogue"
    d2 = comp.get_next_span().data
    assert d2["processing_status"] == "completed"
