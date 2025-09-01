from abm.lf_components.audiobook.abm_style_planner import ABMStylePlanner


def test_style_planner_defaults_dialogue_and_narration_rates():
    spans = {
        "spans_cls": [
            {"type": "dialogue", "text_norm": '"Hello there!"'},
            {"type": "narration", "text_norm": "He paused, then continued."},
        ]
    }
    comp = ABMStylePlanner(spans_in=spans)
    out = comp.plan_styles().data
    styled = out["spans_style"]
    assert styled[0]["style_plan"]["rate"] > styled[1]["style_plan"]["rate"]
    assert styled[0]["style_plan"]["emotion"] in {"excited", "surprised", "questioning", "neutral"}


def test_style_planner_pauses_from_punctuation():
    spans = {"spans": [{"type": "narration", "text": "Wait... really?"}]}
    comp = ABMStylePlanner(spans_in=spans)
    out = comp.plan_styles().data
    pauses = out["spans_style"][0]["style_plan"]["pauses"]
    # Should detect at least one pause for '?' and maybe for '-'/ellipsis
    assert any(p["ms"] > 0 for p in pauses)
