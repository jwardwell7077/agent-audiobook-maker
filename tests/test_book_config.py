from pathlib import Path

import pytest

from abm.audio.book_config import load_book_meta


def test_load_book_meta_roundtrip(tmp_path: Path) -> None:
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"")
    cfg = tmp_path / "book.yaml"
    cfg.write_text(
        f"""
        title: My Book
        author: Jane Doe
        series: Series X
        language: en
        year: 2020
        cover: {cover}
        publisher: Demo
        """,
        encoding="utf-8",
    )
    meta = load_book_meta(cfg)
    assert meta.title == "My Book"
    assert meta.cover == cover


def test_load_book_meta_missing_cover(tmp_path: Path) -> None:
    cfg = tmp_path / "book.yaml"
    cfg.write_text(
        """
        title: My Book
        author: Jane Doe
        cover: missing.jpg
        """,
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError):
        load_book_meta(cfg)
