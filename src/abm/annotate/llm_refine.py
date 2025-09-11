from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests  # OpenAI-compatible HTTP client

from abm.annotate.review import make_review_markdown


@dataclass
class LLMRefineConfig:
    """Configuration for LLM refinement."""

    endpoint: str = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
    api_key: str = os.environ.get("OPENAI_API_KEY", "EMPTY")
    model: str = os.environ.get("OPENAI_MODEL", "local-model")
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 128
    votes: int = 3
    accept_margin: float = 0.05
    per_request_timeout: float = 60.0
    cache_path: Path | None = Path("data/llm_cache.json")
    retry: int = 2
    sleep_between: float = 0.2


class LLMRefiner:
    """Run a separate LLM pass over low-confidence spans and merge results."""

    def __init__(self, cfg: LLMRefineConfig | None = None) -> None:
        self.cfg = cfg or LLMRefineConfig()
        self._session = requests.Session()
        self._cache: dict[str, dict[str, Any]] = {}
        if self.cfg.cache_path and self.cfg.cache_path.exists():
            try:
                self._cache = json.loads(self.cfg.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    # --------------------------- Public API ---------------------------

    def refine(
        self,
        chapters_tagged_path: Path,
        candidates_jsonl: Path,
        out_json: Path,
        out_md: Path | None = None,
    ) -> None:
        """Refine chapters_tagged.json in place using LLM candidates from JSONL."""
        doc = json.loads(chapters_tagged_path.read_text(encoding="utf-8"))
        cands = [
            json.loads(line)
            for line in candidates_jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"[LLM] Loaded {len(cands)} candidates")

        index: dict[tuple[int, int], dict[str, Any]] = {}
        for ch in doc.get("chapters", []):
            ci = int(ch.get("chapter_index", -1))
            for s in ch.get("spans", []):
                index[(ci, int(s.get("id", 0)))] = s

        updated = 0
        for cand in cands:
            key = (int(cand["chapter_index"]), int(cand["span_id"]))
            span = index.get(key)
            if not span:
                continue

            baseline_speaker = str(span.get("speaker") or "Unknown")
            baseline_conf = float(span.get("confidence", 0.0))

            speaker, conf = self._consensus(cand)
            if self._accept(baseline_speaker, baseline_conf, speaker, conf):
                span["speaker"] = speaker
                span["confidence"] = float(conf)
                span["method"] = "llm:consensus"
                updated += 1

        out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[LLM] Updated {updated} spans → {out_json}")

        if out_md:
            out_md.write_text(make_review_markdown(doc["chapters"]), encoding="utf-8")
            print(f"[LLM] Wrote review → {out_md}")

        if self.cfg.cache_path:
            self.cfg.cache_path.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # --------------------------- Internals ---------------------------

    def _accept(
        self,
        base_speaker: str,
        base_conf: float,
        llm_speaker: str,
        llm_conf: float,
    ) -> bool:
        if base_speaker == "Unknown":
            return True
        if llm_speaker and llm_speaker != base_speaker and llm_conf >= base_conf + self.cfg.accept_margin:
            return True
        return False

    def _consensus(self, cand: dict[str, Any]) -> tuple[str, float]:
        """Call the LLM `votes` times with small context variations and combine."""
        votes: list[tuple[str, float]] = []
        for i in range(self.cfg.votes):
            speaker, conf = self._ask_llm(cand, variant=i)
            if speaker:
                votes.append((speaker, conf))

        if not votes:
            return "Unknown", 0.0

        counts: dict[str, float] = {}
        for spk, _c in votes:
            counts[spk] = counts.get(spk, 0.0) + 1.0
        best_label = max(counts.items(), key=lambda kv: kv[1])[0]
        best_conf = max(_c for (s, _c) in votes if s == best_label)
        return best_label, best_conf

    def _ask_llm(self, cand: dict[str, Any], variant: int = 0) -> tuple[str, float]:
        """Single call to your local LLM (OpenAI-compatible or Ollama)."""
        fp = self._key_for_cache(cand, variant)
        if fp in self._cache:
            r = self._cache[fp]
            return str(r.get("speaker") or "Unknown"), float(r.get("confidence") or 0.0)

        prompt = self._build_prompt(cand, variant)
        body = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": "You are a precise literary annotator. Always return strict JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.cfg.temperature,
            "top_p": self.cfg.top_p,
            "max_tokens": self.cfg.max_tokens,
        }

        for attempt in range(self.cfg.retry + 1):
            try:
                resp = self._session.post(
                    f"{self.cfg.endpoint}/chat/completions",
                    headers={"Authorization": f"Bearer {self.cfg.api_key}"},
                    json=body,
                    timeout=self.cfg.per_request_timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                speaker, conf = self._parse_json(content)
                self._cache[fp] = {"speaker": speaker, "confidence": conf}
                time.sleep(self.cfg.sleep_between)
                return speaker, conf
            except Exception:
                if attempt >= self.cfg.retry:
                    break
                time.sleep(0.5)
        return "Unknown", 0.0

    @staticmethod
    def _parse_json(s: str) -> tuple[str, float]:
        """Parse assistant content as JSON, fallback to Unknown on errors."""
        try:
            obj = json.loads(s.strip())
            spk = str(obj.get("speaker") or "Unknown")
            conf = float(obj.get("confidence") or 0.0)
            return spk, conf
        except Exception:
            return "Unknown", 0.0

    def _build_prompt(self, c: dict[str, Any], variant: int) -> str:
        """Compose a strict, deterministic prompt with roster & context."""
        before = str(c.get("context_before") or "")
        after = str(c.get("context_after") or "")
        if variant == 1:
            before = before[-240:]
            after = after[:200]
        elif variant == 2:
            before = before[-180:]
            after = after[:280]

        roster = ", ".join(c.get("roster") or [])
        baseline = (
            f'{c.get("baseline_speaker")} '
            f'({c.get("baseline_confidence"):.2f}, {c.get("baseline_method")})'
        )
        quote = c.get("text") or ""
        stype = c.get("span_type") or "Dialogue"
        notes = c.get("notes") or ""

        return (
            "You are given a short excerpt from a novel. Identify the most likely SPEAKER of the quoted span.\n"
            "Rules:\n"
            "1) Only choose a name from the roster if plausible; otherwise return \"Unknown\".\n"
            "2) If the span is a Thought, the speaker is the thinker.\n"
            "3) Use nearby attributions (e.g., 'X said', 'said X'), pronouns, and turn-taking cues.\n"
            "4) Return STRICT JSON: {\"speaker\": \"NameOrUnknown\", \"confidence\": 0.0-1.0} with no extra text.\n\n"
            f"SpanType: {stype}\n"
            f"Quote: {quote}\n"
            f"Roster: [{roster}]\n"
            f"Baseline: {baseline}\n"
            f"Notes: {notes}\n\n"
            f"Before:\n{before}\n\nAfter:\n{after}\n\n"
            "Respond with only a JSON object."
        )

    @staticmethod
    def _key_for_cache(c: dict[str, Any], variant: int) -> str:
        """Stable cache key based on candidate content and variant."""
        h = hashlib.sha256()
        key = {
            "span_id": c.get("span_id"),
            "text": c.get("text"),
            "before": (c.get("context_before") or "")[-240:],
            "after": (c.get("context_after") or "")[:240],
            "roster": c.get("roster"),
            "variant": variant,
        }
        h.update(json.dumps(key, sort_keys=True).encode("utf-8"))
        return h.hexdigest()


# ------------------------------ CLI ------------------------------ #


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Refine low-confidence spans with a local LLM.")
    ap.add_argument("--tagged", required=True, help="Path to chapters_tagged.json")
    ap.add_argument("--candidates", required=True, help="Path to spans_for_llm.jsonl")
    ap.add_argument("--out-json", required=True, help="Path to write chapters_tagged_refined.json")
    ap.add_argument("--out-md", default=None, help="Optional path to write refreshed review.md")
    ap.add_argument("--endpoint", default=None, help="OpenAI-compatible base URL (default env OPENAI_BASE_URL)")
    ap.add_argument("--api-key", default=None, help="API key (default env OPENAI_API_KEY)")
    ap.add_argument("--model", default=None, help="Model name (default env OPENAI_MODEL)")
    ap.add_argument("--votes", type=int, default=None, help="Number of consensus votes (default 3)")
    ap.add_argument(
        "--accept-margin", type=float, default=None, help="Min conf improvement to override (default 0.05)"
    )
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = LLMRefineConfig()
    if args.endpoint:
        cfg.endpoint = args.endpoint
    if args.api_key:
        cfg.api_key = args.api_key
    if args.model:
        cfg.model = args.model
    if args.votes is not None:
        cfg.votes = args.votes
    if args.accept_margin is not None:
        cfg.accept_margin = args.accept_margin

    ref = LLMRefiner(cfg)
    ref.refine(
        chapters_tagged_path=Path(args.tagged),
        candidates_jsonl=Path(args.candidates),
        out_json=Path(args.out_json),
        out_md=Path(args.out_md) if args.out_md else None,
    )


if __name__ == "__main__":
    main()
