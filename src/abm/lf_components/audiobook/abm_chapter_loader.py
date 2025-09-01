"""Unified ABM Chapter Loader for LangFlow.

Provides three outputs:
    - chapters_data: full chapters.json content with basic stats
    - chapter_data: a single chapter by 0-based index
    - blocks_data: paragraph-level blocks with light metadata and context

This consolidates the earlier Chapter Volume Loader and Enhanced Chapter Loader.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import IntInput, Output, StrInput
from langflow.schema import Data


class ABMChapterLoader(Component):
    display_name = "ABM Chapter Loader"
    description = "Load chapters.json, select a chapter, and/or emit paragraph blocks"
    icon = "book-open"
    name = "ABMChapterLoader"

    inputs = [
        StrInput(
            name="book_name",
            display_name="Book Name",
            info="Book key under data/clean/<book>",
            value="SAMPLE_BOOK",
            required=True,
        ),
        StrInput(
            name="base_data_dir",
            display_name="Data Root",
            info="Path to data/clean directory",
            value="data/clean",
            required=False,
        ),
        StrInput(
            name="subdir",
            display_name="Subdirectory (optional)",
            info="Optional subfolder under the book directory, e.g. 'classified' or 'classified_jsonl'",
            value="",
            required=False,
        ),
        StrInput(
            name="chapters_file",
            display_name="Chapters File Override",
            info="Optional explicit path to chapters.json",
            value="",
            required=False,
        ),
        IntInput(
            name="chapter_index",
            display_name="Chapter Index (0-based)",
            info="Select a specific chapter (0-based) for chapter_data/blocks_data",
            value=0,
            required=False,
        ),
        IntInput(
            name="context_sentences",
            display_name="Context Sentences",
            info="Number of sentences before/after for block context",
            value=2,
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Chapters Data", name="chapters_data", method="load_chapters"),
        Output(display_name="Chapter Data", name="chapter_data", method="select_chapter"),
        Output(display_name="Blocks Data", name="blocks_data", method="load_and_blocks"),
    ]

    # --- Public output methods ---
    def load_chapters(self) -> Data:
        ok, payload = self._read_chapters()
        if not ok:
            return Data(data=payload)
        chapters = payload["chapters"]
        stats = {
            "book_name": payload.get("book_name"),
            "chapter_count": len(chapters),
            "titles": [c.get("title", "") for c in chapters[:10]],
        }
        return Data(data={"chapters": chapters, "stats": stats})

    def select_chapter(self) -> Data:
        ok, payload = self._read_chapters()
        if not ok:
            return Data(data=payload)
        idx = int(getattr(self, "chapter_index", 0))
        chapter = self._get_by_index(payload["chapters"], idx)
        if not chapter:
            return Data(data={"error": f"Chapter {idx} not found"})
        return Data(data={"chapter": chapter})

    def load_and_blocks(self) -> Data:
        ok, payload = self._read_chapters()
        if not ok:
            return Data(data=payload)
        idx = int(getattr(self, "chapter_index", 0))
        chapter = self._get_by_index(payload["chapters"], idx)
        if not chapter:
            return Data(data={"error": f"Chapter {idx} not found"})
        paragraphs = chapter.get("paragraphs") or []
        if not isinstance(paragraphs, list) or not paragraphs:
            return Data(data={"error": f"Chapter {idx} missing paragraphs[]"})
        blocks = self._blocks_from_paragraphs(paragraphs, chapter.get("title", f"Chapter {idx}"))
        meta = {
            "book_name": payload.get("book_name"),
            "chapter_index": idx,
            "chapter_title": chapter.get("title", ""),
            "total_blocks": len(blocks),
            "total_words": sum(c["word_count"] for c in blocks),
        }
        return Data(data={"blocks": blocks, **meta})

    # --- Internal helpers ---
    def _read_chapters(self) -> tuple[bool, dict[str, Any]]:
        override = getattr(self, "chapters_file", "")
        candidates: list[Path] = []
        book: str

        if override:
            p = Path(override)
            candidates.append(p)
            # Try sibling classified dir as well
            candidates.append(p.parent / "classified" / p.name)
            candidates.append(p.parent / "classified_jsonl" / p.name)
            parent_name = p.parent.name
            # If file is inside a classified-like subfolder, the book folder is one level up
            if parent_name in {"classified", "classified_jsonl"} and p.parent.parent.name:
                book = p.parent.parent.name
            else:
                book = parent_name
        else:
            # Primary from inputs
            root = Path(getattr(self, "base_data_dir", "data/clean"))
            book = getattr(self, "book_name", "SAMPLE_BOOK")
            subdir = (getattr(self, "subdir", "") or "").strip("/ ")
            # If user specified a subdir, prioritize it
            if subdir:
                candidates.append(root / book / subdir / "chapters.json")
            # Common defaults
            candidates.append(root / book / "chapters.json")
            candidates.append(root / book / "classified" / "chapters.json")
            candidates.append(root / book / "classified_jsonl" / "chapters.json")

            # Environment overrides
            env_clean = os.getenv("ABM_CLEAN_DIR")
            if env_clean:
                env_root = Path(env_clean)
                if subdir:
                    candidates.append(env_root / book / subdir / "chapters.json")
                candidates.append(env_root / book / "chapters.json")
                candidates.append(env_root / book / "classified" / "chapters.json")
                candidates.append(env_root / book / "classified_jsonl" / "chapters.json")

            # Workspace-relative fallbacks
            cwd_root = Path.cwd() / "data" / "clean"
            if subdir:
                candidates.append(cwd_root / book / subdir / "chapters.json")
            candidates.append(cwd_root / book / "chapters.json")
            candidates.append(cwd_root / book / "classified" / "chapters.json")
            candidates.append(cwd_root / book / "classified_jsonl" / "chapters.json")

        # Pick the first existing path
        path: Path | None = next((c for c in candidates if c.exists()), None)
        if path is None:
            tried = "\n - ".join(str(c) for c in candidates)
            return False, {
                "error": "Chapters file not found",
                "details": {
                    "book_name": book,
                    "base_data_dir": str(getattr(self, "base_data_dir", "data/clean")),
                    "subdir": getattr(self, "subdir", ""),
                    "override": override,
                    "tried": tried,
                },
            }
        try:
            text = Path(path).read_text(encoding="utf-8")
            raw = json.loads(text)
            # Normalize into { chapters: [...] } with resilience to string-encoded JSON
            chapters: list[Any]
            if isinstance(raw, str):
                # Entire file is a JSON string; try decoding once more
                raw2 = json.loads(raw)
                raw = raw2
            if isinstance(raw, list):
                chapters = raw
            elif isinstance(raw, dict):
                ch_val = raw.get("chapters")
                if isinstance(ch_val, list):
                    chapters = ch_val
                elif isinstance(ch_val, str):
                    # Some exporters embed chapters JSON as a string
                    ch2 = json.loads(ch_val)
                    if not isinstance(ch2, list):
                        return False, {
                            "error": (f"Invalid chapters schema in {path}: 'chapters' string did not decode to list")
                        }
                    chapters = ch2
                else:
                    return False, {"error": f"Invalid chapters schema in {path}: missing or wrong 'chapters' type"}
            else:
                return False, {"error": f"Invalid chapters schema in {path}: not list or object"}

            # Validate basic element type to avoid downstream attribute errors
            if not all(isinstance(c, dict) for c in chapters):
                return False, {"error": f"Invalid chapters items in {path}: expected list[object]"}

            result = {"chapters": chapters, "book_name": book}
            return True, result
        except Exception as e:
            return False, {"error": f"Failed to load {path}: {e}"}

    def _get_by_index(self, chapters: list[dict[str, Any]], zero_based_idx: int) -> dict[str, Any] | None:
        """Return chapter by zero-based index.

        Honors either 'chapter_index' (assumed 0-based in file) or 'index' fields when present.
        Falls back to list position.
        """
        for ch in chapters:
            idx0 = ch.get("chapter_index")
            idx1 = ch.get("index")
            if isinstance(idx0, int) and idx0 == zero_based_idx:
                return ch
            if isinstance(idx1, int) and idx1 == zero_based_idx:
                return ch
        # Fallback to list position if no explicit index fields
        if 0 <= zero_based_idx < len(chapters):
            return chapters[zero_based_idx]
        return None

    def _split_into_sentences(self, text: str) -> list[str]:
        sentences: list[str] = []
        cur = ""
        in_quote = False
        q = None
        for ch in text:
            cur += ch
            if ch in ['"', "'"] and not in_quote:
                in_quote = True
                q = ch
            elif q and ch == q and in_quote:
                in_quote = False
                q = None
            if ch in ".!?" and not in_quote:
                if not re.search(r"\b(Mr|Mrs|Dr|Prof|Inc|Ltd)\.$", cur):
                    sentences.append(cur.strip())
                    cur = ""
        if cur.strip():
            sentences.append(cur.strip())
        return [s for s in sentences if s]

    def _create_block(
        self,
        block_text: str,
        block_id: int,
        all_sentences: list[str],
        current_index: int,
        current_block: list[str],
        chapter_title: str,
    ) -> dict[str, Any]:
        block_type = self._classify_block_type(block_text)
        before = self._ctx_before(all_sentences, current_index - len(current_block))
        after = self._ctx_after(all_sentences, current_index)
        dialogue = self._extract_dialogue(block_text) if block_type in ("dialogue", "mixed") else ""
        return {
            "block_id": block_id,
            "text": block_text,
            "type": block_type,
            "word_count": len(block_text.split()),
            "char_count": len(block_text),
            "sentence_count": len(current_block),
            "dialogue_text": dialogue,
            "context_before": before,
            "context_after": after,
            "chapter_title": chapter_title,
        }

    def _blocks_from_paragraphs(self, paragraphs: list[str], chapter_title: str) -> list[dict[str, Any]]:
        sents_by_par = [self._split_into_sentences(p or "") for p in paragraphs]
        all_sents = [s for sl in sents_by_par for s in sl]
        blocks: list[dict[str, Any]] = []
        offset = 0
        bid = 0
        for cur_sents, para_text in zip(sents_by_par, paragraphs, strict=True):
            cur_idx = offset + len(cur_sents)
            blocks.append(self._create_block(para_text.strip(), bid, all_sents, cur_idx, cur_sents, chapter_title))
            bid += 1
            offset = cur_idx
        return blocks

    def _classify_block_type(self, text: str) -> str:
        has_quotes = bool(re.search(r'"[^"]*"|\'[^\']*\'', text))
        has_attrib = bool(re.search(r"\b(\w+)\s+(said|asked|replied|whispered|shouted|exclaimed)\b", text, re.I))
        has_narr = bool(re.search(r"\b(The|A|An|Meanwhile|However|Then|After|Before)\b", text))
        if has_quotes and (has_attrib or len(re.findall(r'"[^"]*"', text)) > 0):
            return "dialogue" if not has_narr else "mixed"
        return "narration" if (has_narr and not has_quotes) else "mixed"

    def _ctx_before(self, s: list[str], i: int) -> str:
        n = max(0, int(getattr(self, "context_sentences", 2)))
        start = max(0, i - n)
        return " ".join(s[start:i])

    def _ctx_after(self, s: list[str], i: int) -> str:
        n = max(0, int(getattr(self, "context_sentences", 2)))
        end = min(len(s), i + n)
        return " ".join(s[i:end])

    def _extract_dialogue(self, text: str) -> str:
        quotes = re.findall(r'"[^"]*"|\'[^\']*\'', text)
        return " ".join(quotes)

    def _find_attribution_clues(self, text: str) -> list[str]:
        matches = re.findall(r"\b(\w+)\s+(said|asked|replied|shouted|whispered|exclaimed)\b", text, re.I)
        return [" ".join(m) for m in matches]

    def _assess_complexity(self, text: str) -> str:
        word_count = len(text.split())
        sentence_count = text.count(".") + text.count("!") + text.count("?")
        avg = word_count / max(1, sentence_count)
        if avg > 25 or word_count > 400:
            return "high"
        if avg > 15 or word_count > 200:
            return "medium"
        return "low"


# --- Convenience runner for simple pipelines/tests ---
def run(book: str, base_dir: str | None = None, chapters_file: str | None = None) -> dict:
    """Load chapters for a book and return a minimal payload.

    Returns a dict with at least keys: 'book', 'chapters'.
    """
    comp = ABMChapterLoader()
    comp.book_name = book
    if base_dir:
        comp.base_data_dir = base_dir.rstrip("/")
    if chapters_file:
        comp.chapters_file = chapters_file
    data = comp.load_chapters().data
    chapters = data.get("chapters") or []
    # Normalize structure similar to legacy caller expectations
    return {"book": book, "chapters": chapters}
