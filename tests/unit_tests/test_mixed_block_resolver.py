from abm.lf_components.audiobook.abm_mixed_block_resolver import ABMMixedBlockResolver


def _make_validated_blocks(book_id: str = "mvs"):
    return {
        "blocks": [
            {
                "book_id": book_id,
                "chapter_index": 0,
                "chapter_number": 1,
                "block_id": 0,
                "text_norm": "This is narration without quotes.",
                "block_uid": "uid-block-0",
            },
            {
                "book_id": book_id,
                "chapter_index": 0,
                "chapter_number": 1,
                "block_id": 1,
                "text_norm": 'He said, "Hello there!" and left.',
                "block_uid": "uid-block-1",
            },
        ]
    }


def test_resolver_splits_mixed_block_and_counts_roles():
    payload = _make_validated_blocks()
    comp = ABMMixedBlockResolver(validated_blocks=payload, write_to_disk=False)
    spans = comp.resolve_spans().data["spans"]
    meta = comp.get_meta().data

    # Expect: first block yields one narration span; second yields narration, dialogue, narration
    assert len(spans) == 4
    roles = [s["role"] for s in spans]
    assert roles.count("dialogue") == 1
    assert roles.count("narration") == 3
    # Segment IDs per block should start at 0 and increase
    segs_block1 = [s["segment_id"] for s in spans if s["block_id"] == 1]
    assert segs_block1 == sorted(segs_block1)
    # Deterministic span_uid presence
    assert all("span_uid" in s for s in spans)
    assert meta["valid"] is True
    assert meta["dialogue_spans"] == 1
    assert meta["narration_spans"] == 3


def test_resolver_determinism():
    payload = _make_validated_blocks()
    a = ABMMixedBlockResolver(validated_blocks=payload, write_to_disk=False).resolve_spans().data["spans"]
    b = ABMMixedBlockResolver(validated_blocks=payload, write_to_disk=False).resolve_spans().data["spans"]
    assert [s["span_uid"] for s in a] == [s["span_uid"] for s in b]
