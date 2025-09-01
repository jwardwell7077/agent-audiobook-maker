from abm.lf_components.audiobook.abm_span_classifier import ABMSpanClassifier


def _make_spans_payload():
    return {
        "spans": [
            {
                "span_uid": "uid-span-0",
                "book_id": "mvs",
                "chapter_index": 0,
                "chapter_number": 1,
                "block_id": 0,
                "segment_id": 0,
                "role": "dialogue",
                "text_norm": '"Hello there!"',
            },
            {
                "span_uid": "uid-span-1",
                "book_id": "mvs",
                "chapter_index": 0,
                "chapter_number": 1,
                "block_id": 1,
                "segment_id": 0,
                # no role hint
                "text_norm": "This is narration.",
            },
        ]
    }


def test_span_classifier_role_hint_and_fallback():
    payload = _make_spans_payload()
    comp = ABMSpanClassifier(spans=payload, use_role_hint=True, write_to_disk=False)
    out = comp.classify_spans().data["spans_cls"]
    meta = comp.get_meta().data

    assert len(out) == 2
    # First item keeps dialogue via hint
    assert out[0]["type"] == "dialogue"
    # Second item uses fallback (no quotes → narration)
    assert out[1]["type"] == "narration"
    # Meta counts
    assert meta["dialogue"] == 1
    assert meta["narration"] == 1
    assert meta["valid"] is True


def test_span_classifier_determinism():
    payload = _make_spans_payload()
    a = ABMSpanClassifier(spans=payload, use_role_hint=True).classify_spans().data["spans_cls"]
    b = ABMSpanClassifier(spans=payload, use_role_hint=True).classify_spans().data["spans_cls"]
    # Deterministic labels and features lengths
    assert [r["type"] for r in a] == [r["type"] for r in b]
    assert [r["features"]["len_words"] for r in a] == [r["features"]["len_words"] for r in b]
