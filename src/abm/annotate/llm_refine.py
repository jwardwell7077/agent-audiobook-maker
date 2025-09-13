from __future__ import annotations

import argparse
import concurrent.futures as futures
import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from abm.annotate.llm_cache import LLMCache
from abm.annotate.llm_prep import LLMCandidateConfig, LLMCandidatePreparer
from abm.annotate.progress import ProgressReporter
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
    max_concurrency: int = 4
    verbose: bool = False


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

    return (
        text[max(0, start - n) : start],
        text[start:end],
        text[end : min(len(text), end + n)],
    )


def _fuzzy_match(name: str, roster: dict[str, list[str]]) -> str | None:
    """Return canonical roster name if ``name`` or any alias matches ≥ 0.92.

    Args:
        name: Proposed speaker name from the LLM.
        roster: Mapping canonical -> aliases list.
    Returns:
        Canonical name if a match is found, else ``None``.
    """

    if not name or not roster:
        return None
    target = name.lower().strip()
    for canon, aliases in roster.items():
        for opt in [canon] + list(aliases or []):
            if difflib.SequenceMatcher(a=target, b=str(opt).lower().strip()).ratio() >= 0.92:
                return canon
    return None


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
        # Ensure local service is running and the model is available.
        svc.ensure_up(timeout_s=45.0)
        try:
            svc.pull_model(backend.model)
        except Exception:
            # Pull may fail if the model is already present or the backend isn't Ollama.
            pass

    client = OpenAICompatClient(base_url=backend.endpoint, model=backend.model)
    cache = LLMCache(cache_path or out_json.with_suffix(".cache.sqlite"))

    doc = json.loads(tagged_path.read_text(encoding="utf-8"))
    # Policy: only Unknown or conf < 0.85 are candidates regardless of skip-threshold.
    cand = LLMCandidatePreparer(LLMCandidateConfig(conf_threshold=0.85)).prepare(doc)
    if cfg.verbose:
        print(f"[llm] candidates selected: {len(cand)} (Unknown or conf<0.85)")

    changed = 0
    total = 0

    # Index chapters by idx for quick lookup
    chapters_by_idx: dict[int, dict[str, Any]] = {
        int(ch["chapter_index"]): ch for ch in doc.get("chapters", []) if "chapter_index" in ch
    }

    def process_one(c: dict[str, Any]) -> tuple[int, int, dict[str, Any] | None]:
        ch = chapters_by_idx.get(int(c["chapter_index"]))
        if not ch:
            return (-1, -1, None)
        text: str = ch.get("text", "") or ""
        roster: dict[str, list[str]] = c.get("roster") or {}
        left, mid, right = _ctx(text, c["start"], c["end"], cfg.context_chars)

        cached = cache.get(
            roster=roster,
            left=left,
            mid=mid,
            right=right,
            span_type=c["type"],
            model=backend.model,
        )
        if cached is None:
            votes_map: dict[str, float] = {}
            uprompt = speaker_user_prompt(roster, left, mid, right, c["type"])
            # Continuation bias: look back one span
            prev_speaker = None
            try:
                spans = ch.get("spans", []) or []
                idx = next(i for i, s in enumerate(spans) if s.get("start") == c["start"] and s.get("end") == c["end"])
                if idx > 0:
                    ps = spans[idx - 1]
                    if ps.get("speaker") not in (None, "Unknown") and float(ps.get("confidence", 0.0)) >= 0.90:
                        prev_speaker = str(ps.get("speaker"))
            except Exception:
                pass

            for _ in range(cfg.votes):
                obj = cast(
                    dict[str, Any],
                    client.chat_json(
                        system_prompt=SYSTEM_SPEAKER,
                        user_prompt=uprompt,
                        temperature=cfg.temperature,
                        top_p=cfg.top_p,
                        max_tokens=cfg.max_tokens,
                    ),
                )
                spk = str(obj.get("speaker", "Unknown")).strip() or "Unknown"
                # Enforce roster + fuzzy match
                canon = _fuzzy_match(spk, roster)
                spk = canon or ("Unknown" if spk.lower() != "unknown" else "Unknown")
                conf = float(obj.get("confidence", 0.0))
                votes_map[spk] = max(votes_map.get(spk, 0.0), conf)
            # Continuation bias: slight boost
            if prev_speaker and prev_speaker in votes_map:
                votes_map[prev_speaker] = max(votes_map[prev_speaker], min(0.96, votes_map[prev_speaker] + 0.03))

            speaker, conf = max(votes_map.items(), key=lambda kv: kv[1])
            cached = {"speaker": speaker, "confidence": conf}
            cache.set(
                cached,
                roster=roster,
                left=left,
                mid=mid,
                right=right,
                span_type=c["type"],
                model=backend.model,
            )
        return (int(c["start"]), int(c["end"]), cached)

    results: list[tuple[int, int, dict[str, Any] | None]] = []
    status_mode = getattr(cfg, "status_mode", "auto")  # for forward-compat
    with ProgressReporter(total=len(cand), mode=status_mode, title="Stage B · LLM refine") as pr:
        if cfg.max_concurrency <= 1:
            for c in cand:
                res = process_one(c)
                results.append(res)
                total += 1
                pr.advance(
                    1,
                    text=f"ch {c.get('chapter_index')} @ {c.get('start')}-{c.get('end')}",
                )
        else:
            with futures.ThreadPoolExecutor(max_workers=int(cfg.max_concurrency)) as ex:
                futs = [ex.submit(process_one, c) for c in cand]
                for f in futures.as_completed(futs):
                    results.append(f.result())
                    total += 1
                    pr.advance(1)

    # Apply updates back into doc
    by_span = {(s, e): obj for (s, e, obj) in results if obj is not None and s >= 0}
    for ch in doc.get("chapters", []) or []:
        for s in ch.get("spans", []) or []:
            key = (int(s.get("start", -1)), int(s.get("end", -1)))
            if key in by_span:
                cached = by_span[key]
                if not cached:
                    continue
                old_conf = float(s.get("confidence", 0.0))
                if cached["speaker"] != s.get("speaker") or cached["confidence"] > old_conf:
                    s["speaker"] = cached["speaker"]
                    s["method"] = "llm"
                    s["confidence"] = max(
                        cached["confidence"],
                        (cfg.accept_min_conf if cached["speaker"] != "Unknown" else cfg.unknown_min_conf),
                    )
                    changed += 1

    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    if out_md:
        lines = [
            "# LLM refinement summary",
            "",
            f"- candidates processed: {total}",
            f"- spans modified: {changed}",
            "",
        ]
        for ch in doc.get("chapters", []) or []:
            ds = [s for s in (ch.get("spans", []) or []) if s.get("type") in {"Dialogue", "Thought"}]
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
    ap.add_argument(
        "--endpoint",
        default="http://127.0.0.1:11434/v1",
        help="OpenAI-compatible base URL",
    )
    ap.add_argument("--model", default="llama3.1:8b-instruct-q6_K", help="Model id/name")
    ap.add_argument(
        "--manage-llm",
        action="store_true",
        help="Start/stop local LLM service automatically (Ollama)",
    )
    ap.add_argument(
        "--skip-threshold",
        type=float,
        default=0.90,
        help="Skip spans with conf >= this",
    )
    ap.add_argument("--votes", type=int, default=3, help="Majority vote count per span")
    ap.add_argument("--cache", default=None, help="Optional path to SQLite cache file")
    ap.add_argument("--max-concurrency", type=int, default=4, help="Max parallel LLM requests")
    ap.add_argument("--cache-dir", default=None, help="Directory for cache DB (overrides --cache)")
    ap.add_argument("--verbose", action="store_true", help="Verbose refinement logs")
    ap.add_argument(
        "--status",
        choices=["auto", "rich", "tqdm", "none"],
        default="auto",
        help="Live status renderer",
    )
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
    cfg = LLMRefineConfig(
        min_conf_for_skip=args.skip_threshold,
        votes=args.votes,
        max_concurrency=args.max_concurrency,
        verbose=args.verbose,
    )
    refine_document(
        tagged_path=Path(args.tagged),
        out_json=Path(args.out_json),
        out_md=Path(args.out_md) if args.out_md else None,
        backend=backend,
        cfg=cfg,
        manage_service=args.manage_llm,
        cache_path=(
            Path(args.cache) if args.cache else (Path(args.cache_dir) / "llm.cache.sqlite" if args.cache_dir else None)
        ),
    )


if __name__ == "__main__":
    main()
