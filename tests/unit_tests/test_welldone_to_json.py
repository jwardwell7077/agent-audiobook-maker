from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from abm.ingestion.welldone_to_json import WellDoneToJSONL


def test_convert_text_emits_jsonl_and_meta(tmp_path: Path) -> None:
    text = "One\n\nTwo\n\nThree"
    out = WellDoneToJSONL().convert_text(text, base_name="demo_well_done", out_dir=tmp_path)
    jl = out["jsonl"]
    meta = out["meta"]
    assert jl.exists() and meta.exists()

    lines = jl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    for i, ln in enumerate(lines):
        obj = json.loads(ln)
        assert obj["index"] == i
        assert isinstance(obj["text"], str)

    meta_obj = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_obj["block_count"] == 3
    assert meta_obj["immutable"] is True


def test_convert_reads_well_done_file_and_raises_on_missing(tmp_path: Path) -> None:
    wd = tmp_path / "t.txt"
    with pytest.raises(FileNotFoundError):
        WellDoneToJSONL().convert(wd)
    # create file and convert
    wd.write_text("A\n\nB", encoding="utf-8")
    out = WellDoneToJSONL().convert(wd)
    assert out["jsonl"].exists()


def test_meta_links_ingest_options_when_sidecar_present(tmp_path: Path) -> None:
    # Prepare a fake ingest meta sidecar with options
    wd = tmp_path / "book_well_done.txt"
    wd.write_text("Z", encoding="utf-8")
    ingest_meta = tmp_path / "book_ingest_meta.json"
    ingest_meta.write_text(json.dumps({"options": {"mode": "dev"}}), encoding="utf-8")

    out = WellDoneToJSONL().convert_text(
        "Z",
        base_name="book_well_done",
        out_dir=tmp_path,
        ingest_meta_path=ingest_meta,
    )
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    assert meta["options"] == {"mode": "dev"}


def test_meta_book_detected_from_clean_path(tmp_path: Path) -> None:
    # Ensure book is inferred from path data/clean/<book>/...
    out_dir = tmp_path / "data" / "clean" / "novella"
    out = WellDoneToJSONL().convert_text("P1\n\nP2", base_name="story_well_done", out_dir=out_dir)
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    assert meta["book"] == "novella"


def test_meta_sidecar_discovery_without_explicit_path(tmp_path: Path) -> None:
    # Create a sidecar with the expected discovered name next to the well_done.txt
    out_dir = tmp_path / "out"
    # The converter will look for <stem>_ingest_meta.json, where stem is base_name with _well_done removed
    sidecar = out_dir / "story_ingest_meta.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"options": {"flag": True}}), encoding="utf-8")

    out = WellDoneToJSONL().convert_text("A\n\nB", base_name="story_well_done", out_dir=out_dir)
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    # options lifted from discovered sidecar; ingested_from points to it
    assert meta["options"] == {"flag": True}
    assert meta["ingested_from"].endswith("story_ingest_meta.json")


def test_meta_with_provided_ingest_path_missing(tmp_path: Path) -> None:
    # Provide a non-existent ingest_meta_path; options should remain None and ingested_from None
    out = WellDoneToJSONL().convert_text(
        "X\n\nY",
        base_name="demo_well_done",
        out_dir=tmp_path,
        ingest_meta_path=tmp_path / "does_not_exist.json",
    )
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    assert meta["options"] is None
    assert meta["ingested_from"] is None


def test_meta_sidecar_invalid_json_yields_none_options(tmp_path: Path) -> None:
    # Sidecar exists but contains invalid JSON → options=None, ingested_from is still set
    out_dir = tmp_path / "o"
    sidecar = out_dir / "t_ingest_meta.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("{this is not json]", encoding="utf-8")

    out = WellDoneToJSONL().convert_text("A", base_name="t_well_done", out_dir=out_dir)
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    assert meta["options"] is None
    assert meta["ingested_from"].endswith("t_ingest_meta.json")


def test_meta_includes_iso_created_at_and_source_path(tmp_path: Path) -> None:
    out = WellDoneToJSONL().convert_text("Alpha\n\nBeta", base_name="alpha_well_done", out_dir=tmp_path)
    meta = json.loads(out["meta"].read_text(encoding="utf-8"))
    # created_at is ISO and parseable
    datetime.fromisoformat(meta["created_at"])  # does not raise
    # source_well_done points to the .txt alongside outputs
    assert meta["source_well_done"].endswith("alpha_well_done.txt")
