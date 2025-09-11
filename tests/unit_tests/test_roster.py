"""Tests for roster building and merging utilities."""

from abm.annotate.roster import build_chapter_roster, merge_book_roster


def test_build_chapter_roster_extracts_heuristic_names() -> None:
    text = (
        '"Thanks, Bob!" Alice said.\n'
        "Captain Holt arrived.\n"
        "<User: Quinn>"
    )

    roster = build_chapter_roster(text)

    assert roster["Quinn"] == ["Quinn"]
    assert roster["Bob"] == ["Bob"]
    assert roster["Holt"] == ["Holt"]


def test_merge_book_roster_alias_matching() -> None:
    book = {"Robert": ["Robert", "Bob"]}
    chap = {"Bob": ["Bob"], "Alice": ["Alice"]}

    merged = merge_book_roster(book, chap)

    assert "Robert" in merged
    assert set(merged["Robert"]) == {"Robert", "Bob"}
    assert "Bob" not in merged
    assert merged["Alice"] == ["Alice"]


def test_merge_book_roster_fuzzy(monkeypatch) -> None:
    from abm.annotate import roster as roster_mod

    monkeypatch.setattr(roster_mod, "_HAS_RAPIDFUZZ", True)

    class DummyFuzz:
        @staticmethod
        def ratio(a: str, b: str) -> int:
            return 95

    monkeypatch.setattr(roster_mod, "fuzz", DummyFuzz)

    rb = roster_mod.RosterBuilder()
    book = {"Jon": ["Jon"]}
    chap = {"John": ["John"]}
    merged = rb.merge_book_roster(book, chap)
    assert "Jon" in merged and "John" not in merged


def test_build_chapter_roster_spacy(monkeypatch) -> None:
    from types import SimpleNamespace

    from abm.annotate import roster as roster_mod

    monkeypatch.setattr(roster_mod, "_HAS_SPACY", True)

    def fake_nlp(text: str):
        return SimpleNamespace(ents=[SimpleNamespace(text="John Smith", label_="PERSON")])

    monkeypatch.setattr(roster_mod.RosterBuilder, "_get_nlp", lambda self: fake_nlp)
    rb = roster_mod.RosterBuilder()
    roster = rb.build_chapter_roster("nothing")
    canon = next(iter(roster))
    assert "John" in roster[canon]
    assert "Smith" in roster[canon]

