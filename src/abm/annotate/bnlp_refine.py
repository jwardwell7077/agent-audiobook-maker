from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abm.sidecar.booknlp_adapter import BookNLPAdapter, BookNLPConfig


@dataclass
class BNLPRefinePolicy:
    """Policy to accept or fuse BookNLP attribution."""

    accept_when_rule_unknown_min_prob: float = 0.70
    boost_when_agree_to_conf: float = 0.97
    max_char_gap: int = 40  # allow small offset drift when matching quotes


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _match_quotes(
    spans: list[dict[str, Any]],
    bnlp: list[dict[str, Any]],
    max_char_gap: int,
) -> dict[tuple[int, int], dict[str, Any]]:
    """Greedy match BookNLP quotes to our spans by max char overlap / small gap."""
    index: dict[tuple[int, int], dict[str, Any]] = {}
    bnlp_sorted = sorted(bnlp, key=lambda q: (q["start"], q["end"]))
    for s in spans:
        if s.get("type") not in {"Dialogue", "Thought"}:
            continue
        a = (int(s["start"]), int(s["end"]))
        best: dict[str, Any] | None = None
        best_ol = 0
        for q in bnlp_sorted:
            b = (int(q["start"]), int(q["end"]))
            ol = _overlap(a, b)
            if ol > best_ol or (ol == 0 and abs(a[0] - b[0]) <= max_char_gap):
                best = q
                best_ol = ol
        if best is not None:
            index[a] = best
    return index


def refine_with_bnlp(
    tagged_path: Path,
    out_path: Path,
    *,
    policy: BNLPRefinePolicy,
    verbose: bool = False,
    max_chapters: int | None = None,
    bnlp_pipeline: str = "entity,quote",
    bnlp_size: str = "small",
    bnlp_gate_threshold: float | None = 0.20,
    bnlp_top_n: int = 0,
    bnlp_try_big: bool = False,
    bnlp_tmp_dir: str | None = None,
) -> None:
    import time

    start_time = time.time()
    doc = json.loads(tagged_path.read_text(encoding="utf-8"))

    # Keep tmp artifacts when verbose so we can inspect BNLP outputs
    adapter = BookNLPAdapter(BookNLPConfig(size=bnlp_size, pipeline=bnlp_pipeline, keep_tmp=verbose), verbose=verbose)
    if not adapter.enabled():
        if verbose:
            print("[bnlp] BookNLP not available; copying input → output")
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    changed = 0
    total = 0
    per_ch_changes: list[tuple[int, int]] = []  # (chapter_index, changed_count)
    per_ch_time: list[tuple[int, float, str]] = []  # (chapter_index, seconds, size_used)

    processed = 0
    chapters = doc.get("chapters", [])

    # Gate: select only hard chapters (Unknown% >= threshold) or top-N worst by Unknown%
    def _ch_stats(ch: dict[str, Any]) -> tuple[int, int]:
        ds = [s for s in ch.get("spans", []) if s.get("type") in {"Dialogue", "Thought"}]
        u = sum(1 for s in ds if (s.get("speaker") == "Unknown"))
        return len(ds), u

    eligible_idx: set[int] = set()
    ratios: list[tuple[float, int, int]] = []  # (ratio, idx, unknown)
    for ch in chapters:
        idx = int(ch.get("chapter_index", -1))
        n, u = _ch_stats(ch)
        if n <= 0:
            continue
        r = (u / n) if n else 0.0
        ratios.append((r, idx, u))
        if bnlp_gate_threshold is None or r >= float(bnlp_gate_threshold):
            eligible_idx.add(idx)
    if bnlp_top_n and ratios:
        # add top-N by ratio (then by unknown count)
        for _r, idx, _u in sorted(ratios, key=lambda t: (t[0], t[2]), reverse=True)[:bnlp_top_n]:
            eligible_idx.add(idx)

    if verbose:
        thr_s = "disabled" if bnlp_gate_threshold is None else f">= {bnlp_gate_threshold:.0%}"
        chosen = sorted([i for i in eligible_idx if i != -1])
        print(
            f"[bnlp] gate: threshold {thr_s}, topN={bnlp_top_n} → {len(chosen)} chapters selected: "
            f"{chosen[:12]}{' …' if len(chosen) > 12 else ''}"
        )
    # Try to keep a hot BookNLP instance in-process for speed
    bnlp = None
    try:
        import importlib

        booknlp_mod = importlib.import_module("booknlp.booknlp")
        BookNLP = booknlp_mod.BookNLP
        params = {"pipeline": bnlp_pipeline, "model": bnlp_size}
        bnlp = BookNLP("en", params)
        if verbose:
            print(f"[bnlp] hot BookNLP session: pipeline={bnlp_pipeline}, size={bnlp_size}")
    except Exception as e:
        if verbose:
            print(f"[bnlp] hot session unavailable, using adapter per-chapter: {e}")

    # temp workspace reused when hot
    tmp_base: Path | None = None
    if bnlp is not None:
        import tempfile
        from pathlib import Path as _P

        if bnlp_tmp_dir:
            base = _P(bnlp_tmp_dir)
            base.mkdir(parents=True, exist_ok=True)
            import uuid as _uuid

            tmp_base = base / f"run_{_uuid.uuid4().hex[:8]}"
            tmp_base.mkdir(parents=True, exist_ok=True)
        else:
            tmp_base = _P(tempfile.mkdtemp(prefix="abm_bnlp_hot_"))

    try:
        for ch in chapters:
            idx = int(ch.get("chapter_index", -1))
            if idx not in eligible_idx:
                continue
            if max_chapters is not None and processed >= max_chapters:
                break
            text = ch.get("text", "") or "\n".join(ch.get("paragraphs", []))
            import time as _t

            _t0 = _t.time()
            work_id = f"ch_{ch.get('chapter_index', 'x')}"
            if bnlp is None:
                bnlp_quotes = adapter.annotate_text(text, work_id=work_id)
                size_used = adapter.cfg.size
            else:
                # write once per chapter into the hot workspace
                if tmp_base is None:
                    # extremely unlikely, but create a per-run base if missing
                    import tempfile as _tf
                    from pathlib import Path as _P

                    tmp_base = _P(_tf.mkdtemp(prefix="abm_bnlp_hot_fallback_"))
                in_txt = tmp_base / f"{work_id}.txt"
                out_dir = tmp_base / "out"
                out_dir.mkdir(parents=True, exist_ok=True)
                in_txt.write_text(text, encoding="utf-8")
                # process
                bnlp.process(str(in_txt), str(out_dir), work_id)
                # parse outputs using adapter's loader
                bnlp_quotes = adapter._load_quotes(out_dir, work_id)
                size_used = bnlp_size

            mapping = _match_quotes(ch.get("spans", []), bnlp_quotes, policy.max_char_gap)

            ch_changed = 0
            for s in ch.get("spans", []):
                if s.get("type") not in {"Dialogue", "Thought"}:
                    continue
                total += 1
                key = (int(s["start"]), int(s["end"]))
                q = mapping.get(key)
                if not q:
                    continue

                b_speaker = (q.get("speaker") or "Unknown").strip() or "Unknown"
                b_prob = float(q.get("prob") or 0.0)

                rule_speaker = s.get("speaker", "Unknown")
                rule_conf = float(s.get("confidence", 0.0))

                if (
                    rule_speaker == "Unknown"
                    and b_speaker != "Unknown"
                    and b_prob >= policy.accept_when_rule_unknown_min_prob
                ):
                    s["speaker"] = b_speaker
                    s["method"] = "neural:booknlp"
                    s["confidence"] = max(rule_conf, min(0.90, b_prob))
                    changed += 1
                    ch_changed += 1
                elif rule_speaker == b_speaker and b_speaker != "Unknown":
                    # agree → boost confidence (cap to 0.97)
                    if rule_conf < policy.boost_when_agree_to_conf:
                        s["method"] = "fuse:rule+booknlp"
                        s["confidence"] = policy.boost_when_agree_to_conf
                        changed += 1
                        ch_changed += 1
                # else: keep rule; Stage B (LLM) will arbitrate

            # If stubborn and allowed, retry with big model just for this chapter
            if ch_changed == 0 and bnlp_try_big and bnlp_size != "big":
                if verbose:
                    print(f"[bnlp] ch {idx}: no changes with size={bnlp_size}; retrying size=big")
                big_adapter = BookNLPAdapter(
                    BookNLPConfig(size="big", pipeline=bnlp_pipeline, keep_tmp=verbose), verbose=verbose
                )
                bnlp_quotes_big = big_adapter.annotate_text(text, work_id=work_id)
                mapping_big = _match_quotes(ch.get("spans", []), bnlp_quotes_big, policy.max_char_gap)
                for s in ch.get("spans", []):
                    if s.get("type") not in {"Dialogue", "Thought"}:
                        continue
                    key = (int(s["start"]), int(s["end"]))
                    q = mapping_big.get(key)
                    if not q:
                        continue
                    b_speaker = (q.get("speaker") or "Unknown").strip() or "Unknown"
                    b_prob = float(q.get("prob") or 0.0)
                    rule_speaker = s.get("speaker", "Unknown")
                    rule_conf = float(s.get("confidence", 0.0))
                    if (
                        rule_speaker == "Unknown"
                        and b_speaker != "Unknown"
                        and b_prob >= policy.accept_when_rule_unknown_min_prob
                    ):
                        s["speaker"] = b_speaker
                        s["method"] = "neural:booknlp"
                        s["confidence"] = max(rule_conf, min(0.90, b_prob))
                        changed += 1
                        ch_changed += 1
                    elif rule_speaker == b_speaker and b_speaker != "Unknown":
                        if rule_conf < policy.boost_when_agree_to_conf:
                            s["method"] = "fuse:rule+booknlp"
                            s["confidence"] = policy.boost_when_agree_to_conf
                            changed += 1
                            ch_changed += 1
                if ch_changed > 0:
                    size_used = "big"

            dt = _t.time() - _t0
            per_ch_changes.append((idx, ch_changed))
            per_ch_time.append((idx, dt, size_used))
            if verbose:
                print(f"[bnlp] ch {idx}: changed {ch_changed} spans (size={size_used}, {dt:.2f}s)")
            processed += 1
    finally:
        # cleanup temp workspace for hot mode if not in verbose keep_tmp mode
        if bnlp is not None and not adapter.cfg.keep_tmp and tmp_base is not None:
            import shutil

            try:
                shutil.rmtree(tmp_base, ignore_errors=True)
            except Exception:
                pass

    # Persist BNLP impact summary into document meta for downstream analysis
    try:
        bmeta = {
            "pipeline": bnlp_pipeline,
            "default_size": bnlp_size,
            "gate_threshold": bnlp_gate_threshold,
            "top_n": bnlp_top_n,
            "try_big": bnlp_try_big,
            "total_changed": changed,
            "total_spans": total,
            "changes_by_chapter": [
                {"chapter_index": i, "changed": c} for i, c in sorted(per_ch_changes, key=lambda t: t[0])
            ],
            "time_by_chapter": [{"chapter_index": i, "seconds": round(dt, 3), "size": sz} for i, dt, sz in per_ch_time],
        }
        # attach under a stable key at doc root
        doc.setdefault("meta", {})["bnlp"] = bmeta
    except Exception:
        pass

    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if verbose:
        elapsed = time.time() - start_time
        limit_str = f", limited to {max_chapters} chapters" if max_chapters else ""
        print(
            f"[bnlp] modified spans: {changed}/{total}{limit_str} in {elapsed:.1f}s "
            f"(pipeline={bnlp_pipeline}, size={bnlp_size})"
        )
        # Show top chapter improvements
        if per_ch_changes:
            top = sorted(per_ch_changes, key=lambda t: t[1], reverse=True)[:8]
            msg = ", ".join([f"ch {i}: +{c}" for i, c in top if c > 0]) or "none"
            print(f"[bnlp] chapter gains: {msg}")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fuse BookNLP quote attribution into Stage-A combined.json.")
    ap.add_argument("--tagged", required=True, help="Path to Stage-A combined.json")
    ap.add_argument("--out", required=True, help="Path to write BNLP-fused JSON")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--max-chapters", type=int, default=None, help="Only process the first N chapters")
    ap.add_argument("--bnlp-pipeline", default="entity,quote", help="BookNLP pipeline steps, e.g., 'entity,quote'")
    ap.add_argument("--bnlp-size", default="small", choices=["small", "big"], help="BookNLP model size")
    ap.add_argument(
        "--bnlp-gate-threshold",
        type=float,
        default=0.20,
        help="Only run BNLP when Unknown% >= threshold; set to -1 to disable",
    )
    ap.add_argument("--bnlp-top-n", type=int, default=0, help="Always include top-N worst chapters by Unknown%")
    ap.add_argument(
        "--bnlp-try-big",
        action="store_true",
        help="If a chapter sees no changes, retry with size=big just for that chapter",
    )
    ap.add_argument("--bnlp-tmp-dir", default=None, help="Optional temp directory base (e.g., /dev/shm/abm_bnlp)")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    refine_with_bnlp(
        Path(args.tagged),
        Path(args.out),
        policy=BNLPRefinePolicy(),
        verbose=args.verbose,
        max_chapters=args.max_chapters,
        bnlp_pipeline=args.bnlp_pipeline,
        bnlp_size=args.bnlp_size,
        bnlp_gate_threshold=(
            None
            if (args.bnlp_gate_threshold is not None and args.bnlp_gate_threshold < 0)
            else args.bnlp_gate_threshold
        ),
        bnlp_top_n=args.bnlp_top_n,
        bnlp_try_big=args.bnlp_try_big,
        bnlp_tmp_dir=args.bnlp_tmp_dir,
    )


if __name__ == "__main__":
    main()
