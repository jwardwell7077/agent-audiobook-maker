from __future__ import annotations

from pathlib import Path


def md_to_html(md_path: Path, html_path: Path) -> None:
    try:
        import markdown2
    except Exception:  # pragma: no cover - optional dep
        return
    html_path.write_text(markdown2.markdown_path(str(md_path)))
