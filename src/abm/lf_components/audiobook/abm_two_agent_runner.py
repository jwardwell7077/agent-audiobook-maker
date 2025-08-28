"""Two-Agent Pipeline Runner (CLI)

Wires audiobook components for an end-to-end run:
Loader -> Block Iterator -> Dialogue Classifier -> Speaker Attribution -> Aggregator
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from abm.lf_components.audiobook.abm_block_iterator import ABMBlockIterator
from abm.lf_components.audiobook.abm_dialogue_classifier import ABMDialogueClassifier
from abm.lf_components.audiobook.abm_enhanced_chapter_loader import ABMEnhancedChapterLoader
from abm.lf_components.audiobook.abm_results_aggregator import ABMResultsAggregator
from abm.lf_components.audiobook.abm_speaker_attribution import ABMSpeakerAttribution


def run(
    *,
    book: str,
    chapter: int,
    base_dir: str | None = None,
    batch_size: int = 10,
    start_chunk: int = 1,
    max_chunks: int = 0,
    dialogue_priority: bool = True,
) -> dict[str, Any]:
    repo_root = Path(base_dir).resolve() if base_dir else Path(__file__).resolve().parents[4]
    data_clean = repo_root / "data" / "clean"

    # 1) Load + chunk
    loader = ABMEnhancedChapterLoader(
        book_name=book,
        chapter_index=chapter,
        base_data_dir=str(data_clean),
    )
    chunked_data = loader.load_and_chunk_chapter()  # Data
    if "error" in chunked_data.data:
        raise RuntimeError(f"Loader error: {chunked_data.data['error']}")

    # 2) Create iterator
    iterator = ABMBlockIterator(
        chunked_data=chunked_data,
        batch_size=batch_size,
        start_chunk=start_chunk,
        max_chunks=max_chunks,
        dialogue_priority=dialogue_priority,
    )

    # 3) Aggregator and classifier/attributor
    classifier = ABMDialogueClassifier()
    aggregator = ABMResultsAggregator()

    results: dict[str, Any] | None = None
    total = 0
    while True:
        nxt = iterator.get_next_utterance()  # Data
        payload = nxt.data

        # Completion signal
        if payload.get("processing_status") == "completed":
            # Finalize using the same aggregator instance to include accumulated state
            aggregator.attribution_result = nxt
            results = aggregator.aggregate_results().data
            break

        if "error" in payload:
            raise RuntimeError(f"Iterator error: {payload['error']}")

        # 3a) Classify
        classifier.utterance_text = payload.get("utterance_text", "")
        classifier.book_id = payload.get("book_id", "")
        classifier.chapter_id = payload.get("chapter_id", "")
        classifier.utterance_idx = payload.get("utterance_idx", 0)
        classifier.context_before = payload.get("context_before", "")
        classifier.context_after = payload.get("context_after", "")
        classified = classifier.classify_utterance()  # Data

        # 3b) Attribute speaker
        attribution = ABMSpeakerAttribution(classified_utterance=classified).attribute_speaker()  # Data

        # 3c) Aggregate (accumulate per utterance)
        aggregator.attribution_result = attribution
        aggregator.aggregate_results()  # accumulate state inside
        total += 1

    assert results is not None
    results["runner_metadata"] = {
        "book": book,
        "chapter": chapter,
        "processed_chunks": total,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return results


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Run two-agent audiobook pipeline on a chapter")
    p.add_argument("--book", default="mvs", help="Book key under data/clean/<book>/chapters.json")
    p.add_argument("--chapter", type=int, default=1, help="Chapter index (1-based)")
    p.add_argument("--base-dir", default=None, help="Repo root directory (auto-detected if omitted)")
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--start-chunk", type=int, default=1)
    p.add_argument("--max-chunks", type=int, default=10, help="Limit number of chunks (0=all)")
    p.add_argument("--no-dialogue-priority", action="store_true", help="Do not prioritize dialogue chunks")
    p.add_argument("--out", default=None, help="Path to write aggregated JSON (optional)")
    args = p.parse_args(argv)

    aggregated = run(
        book=args.book,
        chapter=args.chapter,
        base_dir=args.base_dir,
        batch_size=args.batch_size,
        start_chunk=args.start_chunk,
        max_chunks=args.max_chunks,
        dialogue_priority=not args.no_dialogue_priority,
    )

    out_path: Path
    if args.out:
        out_path = Path(args.out)
    else:
        repo_root = Path(args.base_dir).resolve() if args.base_dir else Path(__file__).resolve().parents[4]
        out_dir = repo_root / "data" / "annotations" / args.book
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"two_agent_results_ch{args.chapter:02d}_{ts}.json"

    out_path.write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
