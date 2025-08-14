from __future__ import annotations
import regex as re
from typing import List, Dict, Any
from langflow.custom import Component
from langflow.io import Output, IntInput, BoolInput, DictInput

QUOTE_CHARS = "“”\"'‘’"
DIALOGUE_PAT = re.compile(
    rf"[{QUOTE_CHARS}].*?[{QUOTE_CHARS}]|—\s*[^.?!]+[.?!]?",
    re.DOTALL,
)

SENT_SPLIT = re.compile(r"(?<=\.|\?|!|…)\s+")  # naive sentence split

class SegmentDialogueNarration(Component):
    display_name = "Segment (Dialogue/Narration)"
    description = "Split text into utterances; tag dialogue vs narration."
    icon = "scissors"
    name = "SegmentDialogueNarration"

    inputs = [
        DictInput(name="chapter", display_name="Selected Chapter"),
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
        # quick heuristic: quoted text OR em-dash dialogue start
        t = text.strip()
        return bool(DIALOGUE_PAT.search(t)) or (
            t.startswith("—") or t.startswith("- ")
        )

    def build(self):  # returns plain dict
        chapter: Dict[str, Any] = self.chapter
        if not chapter or "text" not in chapter:
            raise ValueError("Expected ChapterArtifact with 'text'.")

        text = chapter["text"]
        # naive sentence split with character offsets
        spans: List[Dict[str, int]] = []
        start = 0
        for part in SENT_SPLIT.split(text):
            if not part:
                continue
            end = start + len(part)
            spans.append({"start": start, "end": end})
            # approximate: splitter consumed trailing spaces
            # (SENT_SPLIT consumes trailing spaces)
            start = end + 1  # approximate; good enough for first pass

        # fallback: if the splitter miscounted, ensure we cover full text once
        if not spans:
            spans = [{"start": 0, "end": len(text)}]

        # build utterances
        out: List[Dict[str, Any]] = []
        uid_counter = 1
        for sp in spans:
            seg = text[sp["start"]:sp["end"]].strip()
            if len(seg) < self.min_len_to_keep:
                continue
            utype = "dialogue" if self._is_dialogue(seg) else "narration"
            out.append({
                "uid": f"ch{chapter['index']}:u:{uid_counter:04d}",
                "chapter_id": int(chapter["index"]) + 1,
                "span": sp,
                "text": seg,
                "type": utype,
            })
            uid_counter += 1

        if self.merge_short_sentences and len(out) > 1:
            merged: List[Dict[str, Any]] = []
            buf = out[0]
            for cur in out[1:]:
                if len(buf["text"]) < 40 and buf["type"] == cur["type"]:
                    buf["text"] = (
                        (buf["text"].rstrip() + " " + cur["text"].lstrip())
                        .strip()
                    )
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
