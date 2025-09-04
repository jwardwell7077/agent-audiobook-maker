"""ABM Block Schema Validator (LangFlow Component).

Validates and normalizes paragraph blocks, enforces 0-based indices,
adds chapter_number (1-based), cleans text, and computes deterministic block_uid.
Optionally writes records-only JSONL (blocks.jsonl) and a sidecar meta JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, IntInput, Output, StrInput
from langflow.schema import Data

_WS_RE = re.compile(r"\s+")


def _norm_text(s: str) -> str:
    # Basic normalization: strip, collapse whitespace, unify quotes
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    s = s.strip()
    s = _WS_RE.sub(" ", s)
    return s


def _hash_sha1(parts: list[str]) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


@dataclass
class _ValidationResult:
    blocks: list[dict[str, Any]]
    meta: dict[str, Any]


class ABMBlockSchemaValidator(Component):
    display_name = "ABM Block Schema Validator"
    description = "Validate and normalize blocks; compute deterministic block_uids; optionally write JSONL + meta"
    icon = "check-circle"
    name = "ABMBlockSchemaValidator"

    inputs = [
        DataInput(
            name="blocks_data",
            display_name="Blocks Data",
            info="Data payload from ABMChapterLoader.blocks_data",
            required=True,
        ),
        StrInput(
            name="book_id",
            display_name="Book ID (override)",
            info="Override book identifier; if empty, inferred from blocks_data.book_name",
            value="",
            required=False,
        ),
        IntInput(
            name="chapter_index",
            display_name="Chapter Index (override, 0-based)",
            info="Override chapter_index; if empty, inferred from blocks_data",
            value=-1,
            required=False,
        ),
        BoolInput(
            name="write_to_disk",
            display_name="Write JSONL + meta to disk",
            value=False,
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            info="If empty, defaults to output/{book_id}/ch{chapter_number:02d}",
            value="",
            required=False,
        ),
        StrInput(
            name="version",
            display_name="Validator Version",
            value="1.0",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Validated Blocks", name="validated_blocks", method="validate_blocks"),
        Output(display_name="Validation Meta", name="validation_meta", method="get_meta"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last: _ValidationResult | None = None

    # Output methods
    def validate_blocks(self) -> Data:
        res = self._ensure_validated()
        # Optionally write to disk
        if bool(getattr(self, "write_to_disk", False)):
            self._write_artifacts(res)
        return Data(data={"blocks": res.blocks})

    def get_meta(self) -> Data:
        res = self._ensure_validated()
        return Data(data=res.meta)

    # Internal
    def _ensure_validated(self) -> _ValidationResult:
        if self._last is not None:
            return self._last
        src = getattr(self, "blocks_data", None)
        if src is None:
            raise TypeError("blocks_data input is required")
        if hasattr(src, "data"):
            payload = src.data  # type: ignore[attr-defined]
        elif isinstance(src, dict):
            payload = src
        else:
            raise TypeError("blocks_data must be a Data or dict payload")

        errors: list[str] = []
        blocks_in = payload.get("blocks") or []
        if not isinstance(blocks_in, list) or not blocks_in:
            errors.append("No blocks provided")

        # Infer metadata
        book_id = (
            (getattr(self, "book_id", "") or "").strip()
            or payload.get("book_name")
            or payload.get("book_id")
            or "UNKNOWN_BOOK"
        )
        ch_idx_attr = int(getattr(self, "chapter_index", -1))
        chapter_index = ch_idx_attr if ch_idx_attr >= 0 else int(payload.get("chapter_index") or 0)
        chapter_number = chapter_index + 1

        normalized: list[dict[str, Any]] = []
        total_words = 0
        for i, blk in enumerate(blocks_in):
            text_raw = blk.get("text") or blk.get("text_raw")
            if not text_raw or not isinstance(text_raw, str):
                errors.append(f"Block {i} missing text")
                continue
            text_norm = _norm_text(text_raw)
            role = blk.get("role") or blk.get("type") or None
            block_id = blk.get("block_id")
            if block_id is None:
                block_id = blk.get("chunk_id")
            try:
                block_id = int(block_id) if block_id is not None else i
            except Exception:  # noqa: BLE001
                errors.append(f"Block {i} has non-integer block_id")
                block_id = i

            wc = len(text_norm.split())
            total_words += wc

            # Deterministic UID
            uid = _hash_sha1([str(book_id), str(chapter_index), str(block_id), text_norm.lower()])

            normalized.append(
                {
                    "book_id": book_id,
                    "chapter_index": chapter_index,
                    "chapter_number": chapter_number,
                    "block_id": block_id,
                    "role": role,
                    "text_raw": text_raw,
                    "text_norm": text_norm,
                    "word_count": wc,
                    "block_uid": uid,
                }
            )

        meta = {
            "component": self.name,
            "version": getattr(self, "version", "1.0"),
            "book_id": book_id,
            "chapter_index": chapter_index,
            "chapter_number": chapter_number,
            "total_blocks": len(normalized),
            "total_words": total_words,
            "errors": errors,
            "valid": len(errors) == 0,
        }
        self._last = _ValidationResult(blocks=normalized, meta=meta)
        return self._last

    def _write_artifacts(self, res: _ValidationResult) -> None:
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir:
            # Default directory: output/{book_id}/ch{NN}
            book_id = res.meta.get("book_id", "UNKNOWN_BOOK")
            chnum = int(res.meta.get("chapter_number", 0))
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")
        Path(outdir).mkdir(parents=True, exist_ok=True)
        blocks_path = Path(outdir) / "blocks.jsonl"
        meta_path = Path(outdir) / "blocks.meta.json"
        # Write records-only JSONL
        with blocks_path.open("w", encoding="utf-8") as f:
            for rec in res.blocks:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # Write meta
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(res.meta, f, ensure_ascii=False, indent=2)
