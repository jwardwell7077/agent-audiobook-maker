from abm.lf_components.audiobook.abm_span_attribution import ABMSpanAttribution


def _mk_span(
    *,
    seg: int,
    typ: str,
    text: str,
    book_id: str = "b",
    ch_idx: int = 0,
    ch_num: int = 1,
    block_id: int = 0,
):
    return {
        "book_id": book_id,
        "chapter_index": ch_idx,
        "chapter_number": ch_num,
        "block_id": block_id,
        "segment_id": seg,
        "type": typ,
        "text_norm": text,
    }


def _wrap(seq):
    return {"spans_cls": seq}


def test_continuity_prev_applies_within_window():
    # Layout:
    # 0: narr "Alice said." (tag gives detection for first dialogue)
    # 1: dial "Hi"
    # 2: narr "She said." (pronoun tag ignored by blocklist)
    # 3: dial "..." (no detection, continuity_prev should apply with d_spans=2)
    seq = [
        _mk_span(seg=0, typ="narration", text="Alice said."),
        _mk_span(seg=1, typ="dialogue", text='"Hi"'),
        _mk_span(seg=2, typ="narration", text="She said."),
        _mk_span(seg=3, typ="dialogue", text='"..."'),
    ]
    comp = ABMSpanAttribution(
        spans_cls=_wrap(seq),
        write_to_disk=False,
        search_radius_spans=1,
        enable_continuity_prev=True,
        continuity_max_distance_spans=2,
    )
    out = comp.attribute_spans().data["spans_attr"]
    dials = [r for r in out if (r.get("type") or r.get("role")) == "dialogue"]
    assert len(dials) == 2
    # First dialogue should attribute to Alice via tag
    assert dials[0]["character_name"] == "Alice"
    # Second dialogue should use continuity_prev and keep Alice
    assert dials[1]["character_name"] == "Alice"
    assert dials[1]["attribution"]["method"] in {"continuity_prev", "unknown"}
    # Ensure evidence mentions continuity when deterministic is on by default
    ev = dials[1]["attribution"].get("evidence", {})
    if isinstance(ev, dict):
        det = ev.get("detection") or {}
        # Either explicit continuity_prev detection or absent when deterministic is disabled
        assert det.get("method") in {None, "continuity_prev"}


def test_continuity_prev_gated_by_distance():
    # Layout with extra narration to push span distance to 3 (>2 window):
    # 0: narr "Alice said." (tag gives detection for first dialogue)
    # 1: dial "Hi"
    # 2: narr "She said." (pronoun ignored)
    # 3: narr "no names here." (no names)
    # 4: dial "..." (no detection, continuity should NOT apply → Unknown)
    seq = [
        _mk_span(seg=0, typ="narration", text="Alice said."),
        _mk_span(seg=1, typ="dialogue", text='"Hi"'),
        _mk_span(seg=2, typ="narration", text="She said."),
        _mk_span(seg=3, typ="narration", text="no names here."),
        _mk_span(seg=4, typ="dialogue", text='"..."'),
    ]
    comp = ABMSpanAttribution(
        spans_cls=_wrap(seq),
        write_to_disk=False,
        search_radius_spans=1,
        enable_continuity_prev=True,
        continuity_max_distance_spans=2,
    )
    out = comp.attribute_spans().data["spans_attr"]
    dials = [r for r in out if (r.get("type") or r.get("role")) == "dialogue"]
    assert len(dials) == 2
    # First dialogue should attribute to Alice via tag
    assert dials[0]["character_name"] == "Alice"
    # Second dialogue should be Unknown due to distance beyond window
    assert dials[1]["character_name"] == "Unknown"
