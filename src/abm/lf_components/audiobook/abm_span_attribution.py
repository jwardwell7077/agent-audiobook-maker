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

from abm.helpers.deterministic_confidence import DeterministicConfidenceScorer

_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]{3,})\b")
_TAG_PATTERNS = [
    # "...", Quinn said / Quinn replied / Quinn asked
    r'"[^\"]*"\s*,?\s*([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|exclaimed)\b',
    # said Quinn / asked Quinn
    r"(?:said|asked|replied|whispered|shouted|exclaimed)\s+([A-Z][a-z]+)\b",
    # Quinn said / Quinn asked (without preceding quotes)
    r"\b([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|exclaimed)\b",
]

# Words that must never be treated as speaker names when captured by patterns
_PRONOUN_BLOCKLIST = {
    "He",
    "She",
    "They",
    "We",
    "I",
    "You",
    "It",
    "Him",
    "Her",
    "Them",
    "Us",
    "Me",
}


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
            name="search_radius_spans",
            display_name="Search Radius (spans)",
            info=("How many narration spans before/after to scan for tags/proper nouns. 0 = only immediate neighbors"),
            value=4.0,
            required=False,
        ),
        FloatInput(
            name="narration_confidence",
            display_name="Narration Confidence",
            info="Confidence assigned to non-dialogue (Narrator) spans",
            value=0.95,
            required=False,
        ),
        BoolInput(
            name="use_deterministic_confidence",
            display_name="Use Deterministic Confidence",
            info=(
                "If true, compute dialogue confidence via deterministic_v1 scorer; otherwise use base/unknown constants"
            ),
            value=True,
            required=False,
        ),
        BoolInput(
            name="write_to_disk",
            display_name="Write JSONL + meta to disk",
            value=False,
            required=False,
        ),
        BoolInput(
            name="use_narration_confidence_evidence",
            display_name="Use Evidence for Narration Confidence",
            info=(
                "If true, compute narration confidence via deterministic_narration_v1; "
                "otherwise use narration_confidence"
            ),
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
        # Optional continuity fallback (conservative, opt-in)
        BoolInput(
            name="enable_continuity_prev",
            display_name="Enable continuity_prev (opt-in)",
            info=(
                "If true, when no speaker is detected from narration, attribute to the previous "
                "dialogue speaker within a small span window"
            ),
            value=False,
            required=False,
        ),
        FloatInput(
            name="continuity_max_distance_spans",
            display_name="continuity_prev max distance (spans)",
            info="Max span distance to previous dialogue to allow continuity_prev fallback (same block only)",
            value=2.0,
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Attributed Spans", name="spans_attr", method="attribute_spans"),
        Output(display_name="Attribution Meta", name="spans_attr_meta", method="get_meta"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last: _AttrResult | None = None
        self._scorer = DeterministicConfidenceScorer()

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
            payload = src.data  # type: ignore[attr-defined]
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
        errors: list[str] = []

        for key, seq in groups.items():
            prev_dialogue_speaker: str | None = None
            prev_dialogue_idx: int | None = None
            for idx, s in enumerate(seq):
                try:
                    label = (s.get("type") or s.get("role") or "").lower()
                    text = s.get("text_norm") or s.get("text_raw") or ""
                    book_id, chapter_index, block_id = key

                    # Look around once so both dialogue and narration can use context
                    before = seq[idx - 1] if idx - 1 >= 0 else None
                    after = seq[idx + 1] if idx + 1 < len(seq) else None

                    if label != "dialogue":
                        # Narration: either evidence-based scoring or fixed knob
                        c_narration += 1
                        use_ev = bool(getattr(self, "use_narration_confidence_evidence", False))
                        if use_ev:
                            btxt = str(before.get("text_norm") or before.get("text_raw")) if before else None
                            atxt = str(after.get("text_norm") or after.get("text_raw")) if after else None
                            b_is_dial = (
                                (before or {}).get("type") or (before or {}).get("role") or ""
                            ).lower() == "dialogue"
                            a_is_dial = (
                                (after or {}).get("type") or (after or {}).get("role") or ""
                            ).lower() == "dialogue"
                            conf, conf_ev, conf_method = self._scorer.score_narration(
                                narration_text=str(text),
                                before_text=btxt,
                                after_text=atxt,
                                before_is_dialogue=b_is_dial,
                                after_is_dialogue=a_is_dial,
                            )
                            result = self._record(
                                s,
                                speaker=None,
                                confidence=conf,
                                method=conf_method,
                                evidence=conf_ev,
                            )
                        else:
                            result = self._record(
                                s,
                                speaker=None,
                                confidence=float(getattr(self, "narration_confidence", 0.95)),
                                method="narration_rule",
                                evidence={},
                            )
                        out.append(result)
                        continue

                    # Look around for speaker tags in adjacent narration spans

                    # Find likely speaker scanning up to N narration spans around
                    radius = int(float(getattr(self, "search_radius_spans", 0.0) or 0.0))
                    speaker, det_evidence, method, distance = self._infer_speaker_window(seq, idx, radius)
                    use_det = bool(getattr(self, "use_deterministic_confidence", True))
                    # Defaults in case no detection applies; will be overridden when detection or continuity applies
                    conf = float(getattr(self, "unknown_confidence", 0.35))
                    merged_evidence = det_evidence or {}
                    if speaker:
                        if use_det:
                            before_text = str(before.get("text_norm") or before.get("text_raw")) if before else None
                            after_text = str(after.get("text_norm") or after.get("text_raw")) if after else None
                            conf, conf_ev, conf_method = self._scorer.score(
                                dialogue_text=str(text),
                                before_text=before_text,
                                after_text=after_text,
                                detected_method=method,
                                detected_speaker=speaker,
                                prev_dialogue_speaker=prev_dialogue_speaker,
                                detection_distance=distance,
                            )
                            merged_evidence = {"detection": det_evidence or {}, "confidence": conf_ev}
                        else:
                            conf = float(getattr(self, "base_confidence", 0.75))
                            merged_evidence = det_evidence or {}
                        c_dialogue += 1
                        prev_dialogue_speaker = speaker
                        prev_dialogue_idx = idx
                    else:
                        # No detection from narration context; optionally apply conservative continuity_prev
                        applied_continuity = False
                        if bool(getattr(self, "enable_continuity_prev", False)) and prev_dialogue_speaker:
                            try:
                                max_d = int(float(getattr(self, "continuity_max_distance_spans", 2.0) or 2.0))
                            except Exception:
                                max_d = 2
                            d_spans = (idx - prev_dialogue_idx) if prev_dialogue_idx is not None else None
                            if d_spans is not None and d_spans <= max_d:
                                # Attribute to previous speaker conservatively
                                speaker = prev_dialogue_speaker
                                method = "continuity_prev"
                                if use_det:
                                    before_text = (
                                        str(before.get("text_norm") or before.get("text_raw")) if before else None
                                    )
                                    after_text = (
                                        str(after.get("text_norm") or after.get("text_raw")) if after else None
                                    )
                                    conf, conf_ev, conf_method = self._scorer.score(
                                        dialogue_text=str(text),
                                        before_text=before_text,
                                        after_text=after_text,
                                        detected_method=None,
                                        detected_speaker=speaker,
                                        prev_dialogue_speaker=prev_dialogue_speaker,
                                        detection_distance=d_spans,
                                    )
                                    merged_evidence = {
                                        "detection": {"method": "continuity_prev", "distance": d_spans},
                                        "confidence": conf_ev,
                                    }
                                else:
                                    conf = float(getattr(self, "base_confidence", 0.75))
                                    merged_evidence = {"method": "continuity_prev", "distance": d_spans}
                                c_dialogue += 1
                                # prev_dialogue_speaker remains the same; prev_dialogue_idx unchanged
                                applied_continuity = True
                        if not applied_continuity:
                            conf = float(getattr(self, "unknown_confidence", 0.35))
                            c_unknown += 1
                            speaker = None
                            method = method or "unknown"
                            merged_evidence = det_evidence or {}

                    result = self._record(s, speaker, conf, method=method or "unknown", evidence=merged_evidence)
                    out.append(result)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"block={key[2]} seg=? error={e}")

        meta = {
            "component": self.name,
            "version": getattr(self, "version", "1.0"),
            "dialogue_attributed": c_dialogue,
            "narration": c_narration,
            "unknown_dialogue": c_unknown,
            "total": len(out),
            "errors": errors,
            "valid": len(errors) == 0,
        }
        self._last = _AttrResult(spans_attr=out, meta=meta)
        return self._last

    def _infer_speaker_window(
        self,
        seq: list[dict[str, Any]],
        idx: int,
        radius: int,
    ) -> tuple[str | None, dict[str, Any] | None, str | None, int | None]:
        """Infer speaker using a window of narration spans around the dialogue index.

        Searches up to `radius` narration spans before and after. Priority order by distance:
        1) dialogue tag match, 2) proper-noun proximity. Returns (speaker, evidence, method, distance).
        distance = 1 means immediate neighbor.
        """
        n = len(seq)

        # Helper to check if record is narration
        def is_narr(s: dict[str, Any]) -> bool:
            lab = (s.get("type") or s.get("role") or "").lower()
            return lab == "narration"

        # Scan ring by increasing distance
        for d in range(1, max(1, radius) + 1):
            candidates: list[tuple[str, dict[str, Any]]] = []
            if idx - d >= 0:
                candidates.append(("before", seq[idx - d]))
            if idx + d < n:
                candidates.append(("after", seq[idx + d]))
            # First pass: dialogue tag pattern
            for loc, span in candidates:
                if is_narr(span):
                    t = str(span.get("text_norm") or span.get("text_raw") or "")
                    for pat in _TAG_PATTERNS:
                        m = re.search(pat, t)
                        if m:
                            name = m.group(1)
                            # Skip pronouns and generic non-names
                            if name in _PRONOUN_BLOCKLIST:
                                continue
                            return (
                                name,
                                {"location": loc, "pattern": pat, "excerpt": t[:120], "distance": d},
                                "dialogue_tag",
                                d,
                            )
            # Second pass: proper noun proximity
            for loc, span in candidates:
                if is_narr(span):
                    t = str(span.get("text_norm") or span.get("text_raw") or "")
                    m = _PROPER_NOUN_RE.search(t)
                    if m:
                        name = m.group(1)
                        if name in _PRONOUN_BLOCKLIST:
                            continue
                        return (
                            name,
                            {
                                "location": loc,
                                "method": "proper_noun_proximity",
                                "excerpt": t[:120],
                                "distance": d,
                            },
                            "proper_noun_proximity",
                            d,
                        )

        return None, None, None, None

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
