from __future__ import annotations

import json
from pathlib import Path

from abm.ingestion.welldone_to_json import WellDoneToJSONL


def test_convert_text_discovers_ingest_meta_sidecar(tmp_path: Path) -> None:
    # Arrange: write well-done text and a sidecar ingest meta next to it
    base = "book1_well_done"
    text = "Para 1\n\nPara 2"
    # Sidecar path pattern: <stem>_ingest_meta.json with stem without _well_done suffix
    sidecar = tmp_path / "book1_ingest_meta.json"
    sidecar.write_text(json.dumps({"options": {"foo": "bar"}}), encoding="utf-8")

    # Act
    out = WellDoneToJSONL().convert_text(text, base_name=base, out_dir=tmp_path)

    # Assert
    meta = json.loads((out["meta"]).read_text(encoding="utf-8"))
    assert meta["block_count"] == 2
    # options propagated from sidecar
    assert meta["options"] == {"foo": "bar"}
    # ingested_from points to discovered sidecar
    assert meta["ingested_from"].endswith("book1_ingest_meta.json")


def test_convert_text_uses_provided_ingest_meta_path_when_exists(tmp_path: Path) -> None:
    base = "x_well_done"
    text = "Only one"
    provided = tmp_path / "custom_ingest_meta.json"
    provided.write_text(json.dumps({"options": {"x": 1}}), encoding="utf-8")

    out = WellDoneToJSONL().convert_text(text, base_name=base, out_dir=tmp_path, ingest_meta_path=provided)
    meta = json.loads((out["meta"]).read_text(encoding="utf-8"))
    assert meta["block_count"] == 1
    assert meta["options"] == {"x": 1}
    assert meta["ingested_from"].endswith("custom_ingest_meta.json")


def test_convert_text_handles_missing_or_invalid_ingest_meta(tmp_path: Path) -> None:
    base = "x_well_done"
    text = "P1\n\nP2\n\nP3"
    # Provide a path that doesn't exist -> should set ingested_from to None and options None
    out = WellDoneToJSONL().convert_text(
        text,
        base_name=base,
        out_dir=tmp_path,
        ingest_meta_path=tmp_path / "nope.json",
    )
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    assert meta["block_count"] == 3
    assert meta["ingested_from"] is None
    assert meta["options"] is None


def test_meta_infers_book_from_clean_dir_and_handles_invalid_options_json(tmp_path: Path) -> None:
    # Create data/clean/<book>/ structure
    clean_dir = tmp_path / "data" / "clean" / "novel"
    clean_dir.mkdir(parents=True)
    base = "novel_well_done"
    text = "A\n\nB"
    # Write a bogus sidecar to trigger JSON parse failure path
    sidecar = clean_dir / "novel_ingest_meta.json"
    sidecar.write_text("not json", encoding="utf-8")

    out = WellDoneToJSONL().convert_text(text, base_name=base, out_dir=clean_dir)
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    assert meta["book"] == "novel"
    assert meta["options"] is None
