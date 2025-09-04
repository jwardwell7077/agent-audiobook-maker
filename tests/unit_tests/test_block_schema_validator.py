from abm.lf_components.audiobook.abm_block_schema_validator import (
    ABMBlockSchemaValidator,
)


def _make_blocks_payload(book_name: str = "mvs", chapter_index: int = 0):
    return {
        "book_name": book_name,
        "chapter_index": chapter_index,
        "chapter_title": "Chapter Title",
        "blocks": [
            {"block_id": 0, "text": "  “Hello”  world!  ", "type": "dialogue"},
            {"block_id": 1, "text": "Narration line.", "type": "narration"},
        ],
    }


def test_block_schema_validator_happy_path_deterministic():
    payload = _make_blocks_payload()
    comp = ABMBlockSchemaValidator(
        blocks_data=payload,
        book_id="mvs",
        chapter_index=0,
        write_to_disk=False,
    )

    res1 = comp.validate_blocks()
    meta1 = comp.get_meta()

    assert hasattr(res1, "data")
    blocks1 = res1.data["blocks"]
    assert isinstance(blocks1, list) and len(blocks1) == 2
    assert all("block_uid" in b for b in blocks1)
    assert all(b["chapter_index"] == 0 for b in blocks1)
    assert all(b["chapter_number"] == 1 for b in blocks1)
    # normalization collapsed whitespace and quotes
    assert blocks1[0]["text_norm"] == '"Hello" world!'
    assert meta1.data["valid"] is True
    assert meta1.data["total_blocks"] == 2

    # Determinism: re-run and compare uids
    comp2 = ABMBlockSchemaValidator(
        blocks_data=payload,
        book_id="mvs",
        chapter_index=0,
        write_to_disk=False,
    )
    res2 = comp2.validate_blocks()
    blocks2 = res2.data["blocks"]
    assert [b["block_uid"] for b in blocks1] == [b["block_uid"] for b in blocks2]


def test_block_schema_validator_missing_text_error():
    payload = {
        "book_name": "mvs",
        "chapter_index": 0,
        "blocks": [
            {"block_id": 0},  # missing text
        ],
    }
    comp = ABMBlockSchemaValidator(blocks_data=payload, write_to_disk=False)

    res = comp.validate_blocks()
    meta = comp.get_meta()
    assert hasattr(res, "data")
    assert res.data["blocks"] == []
    assert meta.data["valid"] is False
    assert meta.data["total_blocks"] == 0
    assert any("missing text" in e for e in meta.data["errors"])  # informative error
