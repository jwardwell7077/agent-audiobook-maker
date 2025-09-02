"""ABM Span Attribution (LangFlow Component).

Attributes speakers for dialogue spans using simple local heuristics on nearby
 narration spans within the same block. Produces spans_attr records and meta;
 optionally writes JSONL + meta to disk.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, FloatInput, Output, StrInput
from langflow.schema import Data

_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]{3,})\b")
_TAG_PATTERNS = [
    # "...", Quinn said / Quinn replied / Quinn asked
    r'"[^\"]*"\s*,?\s*([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|exclaimed)\b',
    # said Quinn / asked Quinn
    r"(?:said|asked|replied|whispered|shouted|exclaimed)\s+([A-Z][a-z]+)\b",
    # Quinn said / Quinn asked (without preceding quotes)
    r"\b([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|exclaimed)\b",
]


@dataclass
class _AttrResult:
    spans_attr: list[dict[str, Any]]
    meta: dict[str, Any]


class ABMSpanAttribution(Component):
    display_name = "ABM Span Attribution"
    description = "Attribute dialogue spans to likely speakers with heuristics"
    icon = "user"
    name = "ABMSpanAttribution"

    inputs = [
        DataInput(
            name="spans_cls",
            display_name="Classified Spans",
            info="Data payload from ABMSpanClassifier.spans_cls (contains spans_cls)",
            required=True,
        ),
        FloatInput(
            name="base_confidence",
            display_name="Base Confidence",
            info="Confidence when a likely speaker is found",
            value=0.75,
            required=False,
        ),
        FloatInput(
            name="unknown_confidence",
            display_name="Unknown Confidence",
            info="Confidence when no reliable speaker found",
            value=0.35,
            required=False,
        ),
        FloatInput(
            name="system_confidence",
            display_name="System Confidence",
            info="Confidence assigned to detected system/meta lines",
            value=0.95,
            required=False,
        ),
        StrInput(
            name="system_name",
            display_name="System Speaker Name",
            info="Character name to use for system/meta lines",
            value="System",
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
            display_name="Attribution Version",
            value="1.0",
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Attributed Spans", name="spans_attr", method="attribute_spans"),
        Output(display_name="Attribution Meta", name="spans_attr_meta", method="get_meta"),
    ]

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._last: _AttrResult | None = None

    def attribute_spans(self) -> Data:
        res = self._ensure_attributed()
        if bool(getattr(self, "write_to_disk", False)):
            self._write_artifacts(res)
        return Data(data={"spans_attr": res.spans_attr})

    def get_meta(self) -> Data:
        res = self._ensure_attributed()
        return Data(data=res.meta)

    # Internal
    def _ensure_attributed(self) -> _AttrResult:
        if self._last is not None:
            return self._last

        src = getattr(self, "spans_cls", None)
        if src is None:
            raise TypeError("spans_cls input is required")
        if hasattr(src, "data"):
            payload = src.data
        elif isinstance(src, dict):
            payload = src
        else:
            raise TypeError("spans_cls must be a Data or dict payload")

        spans = payload.get("spans_cls") or payload.get("spans") or []
        if not isinstance(spans, list):
            raise TypeError("spans_cls.data['spans_cls'] must be a list")

        # Group by (book, chapter, block) and sort by segment
        groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = defaultdict(list)
        for s in spans:
            k = (s.get("book_id"), s.get("chapter_index"), s.get("block_id"))
            groups[k].append(s)
        for k in groups:
            groups[k].sort(key=lambda r: int(r.get("segment_id") or 0))

        out: list[dict[str, Any]] = []
        c_dialogue = 0
        c_narration = 0
        c_unknown = 0
        c_system = 0
        errors: list[str] = []

        for key, seq in groups.items():
            for idx, s in enumerate(seq):
                try:
                    label = (s.get("type") or s.get("role") or "").lower()
                    text = s.get("text_norm") or s.get("text_raw") or ""
                    book_id, chapter_index, block_id = key

                    if label == "system":
                        # Map system to a dedicated speaker
                        c_system += 1
                        result = self._record(
                            s,
                            speaker=str(getattr(self, "system_name", "System")),
                            confidence=float(getattr(self, "system_confidence", 0.95)),
                            method="system_detected",
                            evidence={"hint": "type==system"},
                        )
                        out.append(result)
                        continue

                    if label != "dialogue":
                        # Narration: keep as Narrator, not counted as unknown
                        c_narration += 1
                        result = self._record(
                            s,
                            speaker=None,
                            confidence=float(getattr(self, "unknown_confidence", 0.35)),
                            method="non_dialogue",
                            evidence={},
                        )
                        out.append(result)
                        continue

                    # Look around for speaker tags in adjacent narration spans
                    before = seq[idx - 1] if idx - 1 >= 0 else None
                    after = seq[idx + 1] if idx + 1 < len(seq) else None

                    speaker, evidence, method = self._infer_speaker(text, before, after)
                    if speaker:
                        conf = float(getattr(self, "base_confidence", 0.75))
                        c_dialogue += 1
                    else:
                        conf = float(getattr(self, "unknown_confidence", 0.35))
                        c_unknown += 1
                        speaker = None
                        method = method or "unknown"
                        evidence = evidence or {}

                    result = self._record(s, speaker, conf, method=method or "unknown", evidence=evidence)
                    out.append(result)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"block={key[2]} seg=? error={e}")

        meta = {
            "component": self.name,
            "version": getattr(self, "version", "1.0"),
            "dialogue_attributed": c_dialogue,
            "narration": c_narration,
            "unknown_dialogue": c_unknown,
            "system": c_system,
            "total": len(out),
            "errors": errors,
            "valid": len(errors) == 0,
        }
        self._last = _AttrResult(spans_attr=out, meta=meta)
        return self._last

    def _infer_speaker(
        self,
        dialogue_text: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, Any] | None, str | None]:
        """Infer speaker name using tags in nearby narration spans or proximity.

        Returns (speaker_name_or_None, evidence_dict_or_None, method_str_or_None)
        """
        # 1) Explicit tag patterns in adjacent narration spans
        for loc, span in (("before", before), ("after", after)):
            if span and (span.get("type") == "narration" or span.get("role") == "narration"):
                text = str(span.get("text_norm") or span.get("text_raw") or "")
                for pat in _TAG_PATTERNS:
                    m = re.search(pat, text)
                    if m:
                        name = m.group(1)
                        return name, {"location": loc, "pattern": pat, "excerpt": text[:120]}, "dialogue_tag"

        # 2) Proper noun proximity: choose first proper noun in adjacent narration
        for loc, span in (("before", before), ("after", after)):
            if span and (span.get("type") == "narration" or span.get("role") == "narration"):
                text = str(span.get("text_norm") or span.get("text_raw") or "")
                m = _PROPER_NOUN_RE.search(text)
                if m:
                    return (
                        m.group(1),
                        {"location": loc, "method": "proper_noun_proximity", "excerpt": text[:120]},
                        "proper_noun_proximity",
                    )

        return None, None, None

    def _record(
        self,
        s: dict[str, Any],
        speaker: str | None,
        confidence: float,
        *,
        method: str,
        evidence: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if speaker:
            character_name = speaker
            character_id = speaker.lower()
        else:
            # Narration gets Narrator; dialogue with unknown becomes Unknown/None id
            if (s.get("type") or s.get("role")) == "narration":
                character_name = "Narrator"
                character_id = "narrator"
            else:
                character_name = "Unknown"
                character_id = None

        return {
            "span_uid": s.get("span_uid"),
            "book_id": s.get("book_id"),
            "chapter_index": s.get("chapter_index"),
            "chapter_number": s.get("chapter_number"),
            "block_id": s.get("block_id"),
            "segment_id": s.get("segment_id"),
            "type": s.get("type"),
            "role": s.get("role"),
            "text_norm": s.get("text_norm"),
            "character_name": character_name,
            "character_id": character_id,
            "attribution": {
                "confidence": float(confidence),
                "method": method,
                "evidence": evidence or {},
            },
            "provenance": {
                "rules": "adjacent_narration_tag_or_proper_noun",
                "version": getattr(self, "version", "1.0"),
            },
        }

    def _write_artifacts(self, res: _AttrResult) -> None:
        # Determine output dir from first span or fallback
        outdir = (getattr(self, "output_dir", "") or "").strip()
        if not outdir:
            if res.spans_attr:
                s0 = res.spans_attr[0]
                book_id = s0.get("book_id", "UNKNOWN_BOOK")
                chnum = int(s0.get("chapter_number", 0))
            else:
                book_id = "UNKNOWN_BOOK"
                chnum = 0
            outdir = os.path.join("output", str(book_id), f"ch{chnum:02d}")
        Path(outdir).mkdir(parents=True, exist_ok=True)
        path = Path(outdir) / "spans_attr.jsonl"
        meta_path = Path(outdir) / "spans_attr.meta.json"
        with path.open("w", encoding="utf-8") as f:
            for rec in res.spans_attr:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(res.meta, f, ensure_ascii=False, indent=2)
