from abm.lf_components.audiobook.abm_span_attribution import ABMSpanAttribution


def _spans_cls(dialogue_text: str, before: str | None = None, after: str | None = None):
    seq = []
    if before is not None:
        seq.append(
            {
                "book_id": "b",
                "chapter_index": 0,
                "chapter_number": 1,
                "block_id": 0,
                "segment_id": 0,
                "type": "narration",
                "text_norm": before,
            }
        )
    seq.append(
        {
            "book_id": "b",
            "chapter_index": 0,
            "chapter_number": 1,
            "block_id": 0,
            "segment_id": 1,
            "type": "dialogue",
            "text_norm": dialogue_text,
        }
    )
    if after is not None:
        seq.append(
            {
                "book_id": "b",
                "chapter_index": 0,
                "chapter_number": 1,
                "block_id": 0,
                "segment_id": 2,
                "type": "narration",
                "text_norm": after,
            }
        )
    return {"spans_cls": seq}


def test_attribution_from_dialogue_tag_after():
    comp = ABMSpanAttribution(spans_cls=_spans_cls('"Hello there"', after="Bob said."))
    data = comp.attribute_spans().data
    # Find the dialogue record
    recs = [r for r in data["spans_attr"] if r["type"] == "dialogue"]
    assert recs and recs[0]["character_name"] == "Bob"
    assert recs[0]["attribution"]["method"] in {"dialogue_tag", "proper_noun_proximity"}


def test_attribution_proper_noun_before():
    comp = ABMSpanAttribution(spans_cls=_spans_cls('"It\'s late"', before="Quinn walked in."))
    data = comp.attribute_spans().data
    recs = [r for r in data["spans_attr"] if r["type"] == "dialogue"]
    assert recs and recs[0]["character_name"] == "Quinn"


def test_narration_marked_narrator():
    comp = ABMSpanAttribution(spans_cls={"spans_cls": [{"type": "narration", "text_norm": "The night fell."}]})
    data = comp.attribute_spans().data
    recs = data["spans_attr"]
    assert recs and recs[0]["character_name"] == "Narrator"
