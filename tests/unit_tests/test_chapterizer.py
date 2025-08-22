from pathlib import Path
from abm.structuring.chapterizer import chapterize_from_text


def test_chapterizer_happy_with_fallback() -> None:
    demo = Path("tests/data/books/public_domain_demo/public_domain_demo.txt")
    assert demo.exists(), "demo input missing"
    out = chapterize_from_text(demo)

    # Expect at least two chapters
    assert len(out["chapters"]) >= 2  # type: ignore[index]
    # Fallback likely used since body lines are simple (CHAPTER I/II)
    # while TOC titles are longer
    assert any(
        "fallback used" in w for w in out["warnings"]  # type: ignore[index]
    )
    # Spans are sane and ordered
    spans = []
    for c in out["chapters"]:  # type: ignore[index]
        spans.append((c["start_char"], c["end_char"]))
    for i, (s, e) in enumerate(spans):
        assert 0 <= s < e
        if i > 0:
            prev_e = spans[i - 1][1]
            assert s >= prev_e


def test_chapterizer_duplicate_guard_or_single_match(tmp_path: Path) -> None:
    # Build a tiny book where a title repeats many times in the body slice.
    # Depending on upstream cleaning, duplicates may be collapsed.
    txt = (
        "TABLE OF CONTENTS\n\n"
        "Chapter A ................ 2\n\n"
        "1\n\f\n"
        + ("Chapter A\n" * 12)
    )
    f = tmp_path / "dup.txt"
    f.write_text(txt, encoding="utf-8")

    out = chapterize_from_text(f)
    warnings = out["warnings"]  # type: ignore[index]
    if any("aborted: duplicate" in w for w in warnings):
        # Duplicate guard triggered — no chapters expected.
        assert out["chapters"] == []  # type: ignore[index]
        # Count should be at least 5 to meet the abort condition
        # count >= 5 meets the abort condition
        assert (
            out["duplicate_title_matches"][0]["count"] >= 5
        )  # type: ignore[index]
    else:
        # Cleaning likely collapsed duplicates; still produce a chapter.
        chapters = out["chapters"]  # type: ignore[index]
        assert len(chapters) >= 1
        # Basic sanity on the first chapter
        c0 = chapters[0]
        assert c0["end_char"] > c0["start_char"]
        assert c0["body_text"].strip() != ""


def test_chapterizer_mvs_optional() -> None:
    """Optional integration test using local mvs data if present.

    Skips automatically when the dev sample isn't available in the workspace.
    This avoids adding private data to the repository while letting devs
    validate chapterization end-to-end on a real book locally.
    """
    try:
        import pytest  # local import to avoid unused when skipped by CI
    except Exception:  # pragma: no cover - pytest always available under tests
        pytest = None  # type: ignore[assignment]

    mvs_txt = Path("data/clean/mvs/mvs.txt")
    if not mvs_txt.exists():
        if 'pytest' in globals() and pytest is not None:  # type: ignore[name-defined]
            pytest.skip(
                "mvs dev sample not present; skipping"
            )
        return

    out = chapterize_from_text(mvs_txt)
    chapters = out["chapters"]  # type: ignore[index]
    assert len(chapters) >= 3
    # Expect one chapter title to include "Ability Level" as seen in sample
    assert any("Ability Level" in c.get("title", "") for c in chapters)


def test_chapterizer_abort_many_unmatched(tmp_path: Path) -> None:
    # TOC with 5 titles that do not appear in body and no numeric fallback
    toc_lines = [f"Foo {i} .......... {i+2}" for i in range(5)]
    txt = (
        "TABLE OF CONTENTS\n\n" + "\n".join(toc_lines) + "\n\n"
        "1\n\f\n"  # One body page with unrelated content
        "Nothing relevant here.\n"
    )
    f = tmp_path / "unmatched.txt"
    f.write_text(txt, encoding="utf-8")

    out = chapterize_from_text(f)
    assert out["chapters"] == []  # type: ignore[index]
    assert any(
        "aborted: too many unmatched" in w
        for w in out["warnings"]  # type: ignore[index]
    )
    # Unmatched should list most or all titles
    assert len(out["unmatched_titles"]) >= 3  # type: ignore[index]
