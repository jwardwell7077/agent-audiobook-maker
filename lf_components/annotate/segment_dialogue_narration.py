"""Segment chapter text into dialogue vs narration utterances for LangFlow."""

from __future__ import annotations

from typing import Any

import regex as re
from langflow.custom import Component
from langflow.io import BoolInput, DictInput, IntInput, Output

QUOTE_CHARS = "“”\"'‘’"
# Merge adjacent same-type sentences below this char length.
SHORT_SENTENCE_MERGE_THRESHOLD = 40
DIALOGUE_PAT = re.compile(
    rf"[{QUOTE_CHARS}].*?[{QUOTE_CHARS}]|—\s*[^.?!]+[.?!]?",
    re.DOTALL,
)

SENT_SPLIT = re.compile(r"(?<=\.|\?|!|…)\s+")  # naive sentence split


class SegmentDialogueNarration(Component):
    """Split chapter text into utterances tagged as dialogue or narration.

    Attributes declared explicitly for static type checkers (Pylance/pyright):
        selected_chapter: Injected by LangFlow runtime from input mapping.
        merge_short_sentences: Whether to merge adjacent short
            same‑type sentences.
        min_len_to_keep: Minimum character length to retain a segment.
    """

    # Runtime-injected by LangFlow based on `inputs` definitions.
    selected_chapter: dict[str, Any]
    merge_short_sentences: bool
    min_len_to_keep: int

    display_name = "Segment (Dialogue/Narration)"
    description = "Split text into utterances; tag dialogue vs narration."
    icon = "scissors"
    name = "SegmentDialogueNarration"

    inputs = [
        DictInput(name="selected_chapter", display_name="Selected Chapter"),
        BoolInput(
            name="merge_short_sentences",
            display_name="Merge very short sentences",
            value=True,
        ),
        IntInput(
            name="min_len_to_keep",
            display_name="Min chars to keep",
            value=2,
        ),
    ]

    outputs = [
        Output(
            name="utterances_payload",
            display_name="Utterances Payload",
            method="build",
        ),
    ]

    def _is_dialogue(self, text: str) -> bool:
        t = text.strip()
        # Consider a line dialogue if it matches pattern or starts with
        # an em-dash/dash lead.
        return bool(DIALOGUE_PAT.search(t)) or t.startswith("—") or t.startswith("- ")

    def build(self) -> dict[str, Any]:  # returns plain dict
        """Construct the utterances payload for downstream components.

        Returns:
            dict[str, Any]: Mapping containing utterances list + chapter_meta.

        Raises:
            ValueError: If required chapter text not present.
        """
        chapter: dict[str, Any] = self.selected_chapter
        if not chapter or "text" not in chapter:
            raise ValueError("Expected ChapterArtifact with 'text'.")

        text = chapter["text"]
        spans: list[dict[str, int]] = []
        start = 0
        for part in SENT_SPLIT.split(text):
            if not part:
                continue
            end = start + len(part)
            spans.append({"start": start, "end": end})
            start = end + 1

        if not spans:
            spans = [{"start": 0, "end": len(text)}]

        out: list[dict[str, Any]] = []
        uid_counter = 1
        for sp in spans:
            seg = text[sp["start"] : sp["end"]].strip()
            if len(seg) < self.min_len_to_keep:
                continue
            utype = "dialogue" if self._is_dialogue(seg) else "narration"
            out.append(
                {
                    "uid": f"ch{chapter['index']}:u:{uid_counter:04d}",
                    "chapter_id": int(chapter["index"]) + 1,
                    "span": sp,
                    "text": seg,
                    "type": utype,
                }
            )
            uid_counter += 1

        if self.merge_short_sentences and len(out) > 1:
            merged: list[dict[str, Any]] = []
            buf = out[0]
            for cur in out[1:]:
                if len(buf["text"]) < SHORT_SENTENCE_MERGE_THRESHOLD and buf["type"] == cur["type"]:  # noqa: PLR2004 (named constant documents intent)
                    buf["text"] = (buf["text"].rstrip() + " " + cur["text"].lstrip()).strip()
                    buf["span"]["end"] = cur["span"]["end"]
                else:
                    merged.append(buf)
                    buf = cur
            merged.append(buf)
            out = merged

        return {
            "utterances": out,
            "chapter_meta": {
                "book_id": chapter["book_id"],
                "chapter_id": chapter["chapter_id"],
                "index": chapter["index"],
                "title": chapter["title"],
                "text_sha256": chapter["text_sha256"],
            },
        }
