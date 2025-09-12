"""Stage B LLM refinement CLI and helper functions."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abm.annotate.llm_cache import LLMCache
from abm.annotate.llm_prep import LLMCandidateConfig, LLMCandidatePreparer
from abm.annotate.prompts import SYSTEM_SPEAKER, speaker_user_prompt
from abm.llm.client import OpenAICompatClient
from abm.llm.manager import LLMBackend, LLMService


@dataclass
class LLMRefineConfig:
    """Policy for refinement acceptance.

    Attributes:
        min_conf_for_skip: Spans at or above this confidence are not refined.
        accept_min_conf: Minimum confidence to accept a non-``Unknown`` result.
        unknown_min_conf: Minimum confidence assigned when the result speaker is
            ``"Unknown"``.
        votes: Number of LLM queries per span for majority voting.
        context_chars: Characters of left/right context sent to the model.
        temperature: Sampling temperature passed to the LLM.
        top_p: Nucleus sampling parameter.
        max_tokens: Maximum tokens requested from the LLM.
    """

    min_conf_for_skip: float = 0.90
    accept_min_conf: float = 0.70
    unknown_min_conf: float = 0.50
    votes: int = 3
    context_chars: int = 480
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 128


def _ctx(text: str, start: int, end: int, n: int) -> tuple[str, str, str]:
    """Return text surrounding a span with ``n`` characters of context.

    Args:
        text: Source text containing the span.
        start: Index of the first character of the span.
        end: Index one past the last character of the span.
        n: Number of context characters to include on each side.

    Returns:
        Tuple[str, str, str]: Left context, span text, and right context.

    Raises:
        None
    """

    return text[max(0, start - n) : start], text[start:end], text[end : min(len(text), end + n)]


def refine_document(
    tagged_path: Path,
    out_json: Path,
    out_md: Path | None,
    backend: LLMBackend,
    cfg: LLMRefineConfig,
    *,
    manage_service: bool = False,
    cache_path: Path | None = None,
) -> None:
    """Refine low-confidence spans in ``combined.json`` using an LLM.

    Args:
        tagged_path: Input JSON produced by Stage A.
        out_json: Destination for the refined JSON.
        out_md: Optional path for a summary report.
        backend: LLM service configuration.
        cfg: Refinement policy settings.
        manage_service: If ``True``, start/stop the service automatically.
        cache_path: Optional SQLite cache file path.

    Returns:
        None

    Raises:
        TimeoutError: If ``manage_service`` is ``True`` and the service fails to
            start before the timeout.
    """

    svc = LLMService(backend)
    if manage_service:
        svc.ensure_up(timeout_s=45.0)

    client = OpenAICompatClient(base_url=backend.endpoint, model=backend.model)
    cache = LLMCache(cache_path or out_json.with_suffix(".cache.sqlite"))

    doc = json.loads(tagged_path.read_text(encoding="utf-8"))
    cand = LLMCandidatePreparer(LLMCandidateConfig(conf_threshold=cfg.min_conf_for_skip)).prepare(doc)

    changed = 0
    total = 0

    # Index chapters by idx for quick lookup
    chapters_by_idx: dict[int, dict[str, Any]] = {
        int(ch["chapter_index"]): ch for ch in doc.get("chapters", []) if "chapter_index" in ch
    }

    for c in cand:
        total += 1
        ch = chapters_by_idx.get(int(c["chapter_index"]))
        if not ch:
            continue
        text: str = ch.get("text", "")
        roster: dict[str, list[str]] = c["roster"] or {}
        left, mid, right = _ctx(text, c["start"], c["end"], cfg.context_chars)

        # Cache first: avoids re-querying identical contexts.
        cached = cache.get(roster=roster, left=left, mid=mid, right=right, span_type=c["type"], model=backend.model)
        if cached is None:
            # Majority vote
            votes: dict[str, float] = {}
            uprompt = speaker_user_prompt(roster, left, mid, right, c["type"])
            for _ in range(cfg.votes):
                obj = client.chat_json(
                    system_prompt=SYSTEM_SPEAKER,
                    user_prompt=uprompt,
                    temperature=cfg.temperature,
                    top_p=cfg.top_p,
                    max_tokens=cfg.max_tokens,
                )
                spk = str(obj.get("speaker", "Unknown")).strip() or "Unknown"
                conf = float(obj.get("confidence", 0.0))
                votes[spk] = max(votes.get(spk, 0.0), conf)
            # Pick the speaker with highest confidence.
            speaker, conf = max(votes.items(), key=lambda kv: kv[1])
            cached = {"speaker": speaker, "confidence": conf}
            cache.set(cached, roster=roster, left=left, mid=mid, right=right, span_type=c["type"], model=backend.model)

        # Apply if it improves over current annotation.
        for s in ch.get("spans", []):
            if s.get("start") == c["start"] and s.get("end") == c["end"]:
                old_conf = float(s.get("confidence", 0.0))
                if cached["speaker"] != s.get("speaker") or cached["confidence"] > old_conf:
                    s["speaker"] = cached["speaker"]
                    s["method"] = "llm"
                    s["confidence"] = max(
                        cached["confidence"],
                        cfg.accept_min_conf if cached["speaker"] != "Unknown" else cfg.unknown_min_conf,
                    )
                    changed += 1
                break

    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    if out_md:
        lines = [
            "# LLM refinement summary",
            "",
            f"- candidates processed: {total}",
            f"- spans modified: {changed}",
            "",
        ]
        for ch in doc.get("chapters", []):
            ds = [s for s in ch.get("spans", []) if s.get("type") in {"Dialogue", "Thought"}]
            unk = sum(1 for s in ds if s.get("speaker") == "Unknown")
            lines.append(f"- ch {ch.get('chapter_index')}: Unknown {unk}/{len(ds) if ds else 0}")
        out_md.write_text("\n".join(lines), encoding="utf-8")

    cache.close()
    if manage_service:
        svc.stop()


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for :func:`main`.

    Returns:
        argparse.Namespace: Parsed arguments.

    Raises:
        SystemExit: If argument parsing fails.
    """

    ap = argparse.ArgumentParser(description="Stage B: LLM refinement for low-confidence/Unknown spans.")
    ap.add_argument("--tagged", required=True, help="Path to Stage A combined.json")
    ap.add_argument("--out-json", required=True, help="Path to write refined JSON")
    ap.add_argument("--out-md", default=None, help="Optional summary markdown")
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434/v1", help="OpenAI-compatible base URL")
    ap.add_argument("--model", default="llama3.1:8b-instruct-q6_K", help="Model id/name")
    ap.add_argument("--manage-llm", action="store_true", help="Start/stop local LLM service automatically (Ollama)")
    ap.add_argument("--skip-threshold", type=float, default=0.90, help="Skip spans with conf >= this")
    ap.add_argument("--votes", type=int, default=3, help="Majority vote count per span")
    ap.add_argument("--cache", default=None, help="Optional path to SQLite cache file")
    return ap.parse_args()


def main() -> None:
    """Entry point for the ``llm_refine`` command-line interface.

    Returns:
        None

    Raises:
        None
    """

    args = _parse_args()
    backend = LLMBackend(kind="ollama", endpoint=args.endpoint, model=args.model)
    cfg = LLMRefineConfig(min_conf_for_skip=args.skip_threshold, votes=args.votes)
    refine_document(
        tagged_path=Path(args.tagged),
        out_json=Path(args.out_json),
        out_md=Path(args.out_md) if args.out_md else None,
        backend=backend,
        cfg=cfg,
        manage_service=args.manage_llm,
        cache_path=Path(args.cache) if args.cache else None,
    )


if __name__ == "__main__":
    main()
