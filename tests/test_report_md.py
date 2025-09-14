from pathlib import Path

from abm.audit.report_md import render_markdown


def test_render_markdown(tmp_path):
    summary = {
        "generated_at": "now",
        "unknown_count": 1,
        "total_dialog_thought": 2,
        "unknown_rate": 0.5,
        "top_speakers": [("A", 1)],
        "worst_chapters": [
            {"title": "c1", "total": 2, "unknown": 1, "unknown_rate": 0.5}
        ],
    }
    out = tmp_path / "r.md"
    render_markdown(summary, None, None, out)
    assert out.exists()
    text = out.read_text()
    assert "Unknown" in text
