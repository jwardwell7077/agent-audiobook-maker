from abm.lf_components.audiobook.abm_span_casting import ABMSpanCasting


def test_span_casting_narration_defaults_to_narrator():
    spans = {"spans_attr": [{"type": "narration", "text_norm": "The night fell."}]}
    comp = ABMSpanCasting(spans_in=spans)
    out = comp.assign_voices().data
    assert out["spans_cast"][0]["voice"]["id"].startswith("builtin:")


def test_span_casting_strict_mode_unknown_raises():
    spans = {"spans_attr": [{"type": "dialogue", "text_norm": '"Hello"'}]}
    comp = ABMSpanCasting(spans_in=spans, strict_mode=True)
    out = comp.assign_voices().data
    assert "error" in out


def test_span_casting_with_voice_bank(tmp_path):
    bank = {
        "voices": [
            {"id": "bank:alice", "labels": ["alice", "Alice"], "vendor": "bank", "model": "x"},
            {"id": "bank:narr", "labels": ["narrator"], "vendor": "bank", "model": "n"},
        ],
        "assignments": {"Bob": "bank:alice"},
        "defaults": {"unknown": "bank:narr"},
    }
    p = tmp_path / "bank.json"
    p.write_text(__import__("json").dumps(bank), encoding="utf-8")
    spans = {"spans_attr": [{"type": "dialogue", "character_name": "Bob", "text_norm": '"Hi"'}]}
    comp = ABMSpanCasting(spans_in=spans, voice_bank_path=str(p))
    out = comp.assign_voices().data
    assert out["spans_cast"][0]["voice"]["id"] == "bank:alice"
