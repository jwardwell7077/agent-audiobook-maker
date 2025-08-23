# LangFlow Custom Components

Drop custom Python components here to use in LangFlow via the "Custom Component" loader. Available modules:

- chapter_volume_loader.py — load `data/clean/<book>/chapters.json`
- chapter_selector.py — pick one chapter by index or title substring
- segment_dialogue_narration.py — deterministic dialogue/narration split
- utterance_filter.py — filter utterances by role/length/substring
- payload_logger.py — log + pass-through for easy debugging in flows
- utterance_jsonl_writer.py — write `data/annotations/<book>/<stem>.jsonl`

Naming convention: each file should expose a `run(**kwargs)` function.

Example stub:

```python
# lf_components/chapter_volume_loader.py
from pathlib import Path
import json

def run(data_root: str, book_id: str, pdf_stem: str, chapter_index: int):
    # Locate and load chapter JSON; return selected chapter dict and index list
    # This is a stub: replace with real loader.
    return {
        "chapters_index": [0],
        "selected_chapter": {
            "book_id": book_id,
            "pdf_stem": pdf_stem,
            "chapter_index": chapter_index,
            "title": "Stub Chapter",
            "body": "Hello world"
        }
    }
```

Quick wiring in LangFlow:

- Use Python Function blocks and select these files; the `run(...)` function will appear. Wire:
    1) chapter_volume_loader.run(book="mvs") → 2) chapter_selector.run(index=0)
    → 3) segment_dialogue_narration.run(...) → 4) utterance_filter.run(role="dialogue")
    → 5) payload_logger.run(preview_key="utterances") → 6) utterance_jsonl_writer.run(stem="segments_dev")
