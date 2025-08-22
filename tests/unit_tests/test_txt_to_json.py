from __future__ import annotations

import json
from pathlib import Path

import pytest
from abm.structuring.txt_to_json import TxtToJsonConverter, TxtToJsonOptions


def test_happy_path_pages_and_paragraphs(tmp_path: Path) -> None:
    txt = (
        "Title page\n\nParagraph one line 1\nline 2\n\n"
        "Next para\n\f"
        "Second page first para\n\nSecond page para two\n"
    )
    txt_path = tmp_path / "sample.txt"
    out_path = tmp_path / "out.jsonl"
    txt_path.write_text(txt, encoding="utf-8")

    conv = TxtToJsonConverter()
    conv.convert(
        txt_path,
        out_path,
        TxtToJsonOptions(preserve_form_feeds=True),
    )

    lines = out_path.read_text(encoding="utf-8").splitlines()
    objs = [json.loads(line) for line in lines]

    assert [o["page"] for o in objs] == [1, 1, 2, 2]
    assert [o["para_index"] for o in objs] == [0, 1, 0, 1]
    assert objs[0]["text"] == "Title page"
    assert objs[1]["text"] == "Paragraph one line 1\nline 2"
    assert objs[2]["text"] == "Second page first para"
    assert objs[3]["text"] == "Second page para two"


def test_no_form_feeds_single_page(tmp_path: Path) -> None:
    txt = "A\n\nB\nC\n\nD\n"
    txt_path = tmp_path / "a.txt"
    out_path = tmp_path / "a.jsonl"
    txt_path.write_text(txt, encoding="utf-8")

    conv = TxtToJsonConverter()
    conv.convert(
        txt_path,
        out_path,
        TxtToJsonOptions(preserve_form_feeds=True),
    )
    objs = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]

    assert [o["page"] for o in objs] == [1, 1, 1]
    assert [o["para_index"] for o in objs] == [0, 1, 2]


def test_invalid_newline_raises(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError):
        TxtToJsonOptions(newline="bad")


def test_determinism(tmp_path: Path) -> None:
    txt = "Hello\n\nWorld\n"
    p = tmp_path / "t.txt"
    out1 = tmp_path / "o1.jsonl"
    out2 = tmp_path / "o2.jsonl"
    p.write_text(txt, encoding="utf-8")

    conv = TxtToJsonConverter()
    conv.convert(p, out1)
    conv.convert(p, out2)

    assert out1.read_bytes() == out2.read_bytes()
