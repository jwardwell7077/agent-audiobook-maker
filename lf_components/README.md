# LangFlow Custom Components

Drop custom Python components here to use in LangFlow via the "Custom Component" loader. Suggested modules:

- chapter_volume_loader.py
- segment_dialogue_narration.py
- utterance_jsonl_writer.py

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
