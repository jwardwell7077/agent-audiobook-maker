"""
End-to-end smoke test: EnhancedLoader -> ChunkIterator -> DialogueClassifier (heuristic only)
-> SpeakerAttribution -> ResultsAggregator -> Results→Utterances -> Aggregated JSONL Writer.

Writes to a temp directory and asserts JSONL exists and has records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from abm.lf_components.audiobook.abm_aggregated_jsonl_writer import ABMAggregatedJsonlWriter
from abm.lf_components.audiobook.abm_block_iterator import ABMBlockIterator
from abm.lf_components.audiobook.abm_dialogue_classifier import ABMDialogueClassifier
from abm.lf_components.audiobook.abm_chapter_loader import ABMChapterLoader
from abm.lf_components.audiobook.abm_results_aggregator import ABMResultsAggregator
from abm.lf_components.audiobook.abm_results_to_utterances import ABMResultsToUtterances
from abm.lf_components.audiobook.abm_speaker_attribution import ABMSpeakerAttribution


def test_end_to_end_jsonl(tmp_path: Path) -> None:
    # 1) Load & blocks
    loader = ABMChapterLoader(book_name="mvs", chapter_index=1, base_data_dir="data/clean")
    blocks = loader.load_and_blocks()
    data = blocks.data
    assert "error" not in data

    # 2) Iterate a handful for speed
    iterator = cast(Any, ABMBlockIterator)(
        blocks_data=blocks,
        batch_size=5,
        start_block=1,
        max_blocks=5,
        dialogue_priority=True,
    )

    classifier = ABMDialogueClassifier()
    classifier.disable_llm = True
    classifier.classification_method = "hybrid"
    aggregator = ABMResultsAggregator()

    while True:
        cur = iterator.get_next_utterance()
        payload = cur.data
        if payload.get("processing_status") == "completed":
            aggregator.attribution_result = cur
            aggregated = aggregator.aggregate_results()
            break
        if "error" in payload:
            raise AssertionError(f"Iterator error: {payload['error']}")

        classifier.utterance_text = payload.get("utterance_text", "")
        classifier.book_id = payload.get("book_id", "")
        classifier.chapter_id = payload.get("chapter_id", "")
        classifier.utterance_idx = payload.get("utterance_idx", 0)
        classifier.context_before = payload.get("context_before", "")
        classifier.context_after = payload.get("context_after", "")
        classified = classifier.classify_utterance()

        attribution = ABMSpeakerAttribution(classified_utterance=classified).attribute_speaker()
        aggregator.attribution_result = attribution
        aggregator.aggregate_results()

    agg_data = aggregated.data
    assert agg_data.get("processing_status") == "completed"

    # 3) Normalize to utterances
    normalizer = ABMResultsToUtterances(aggregated_results=aggregated)
    utterances_data = normalizer.to_utterances()
    u_payload = utterances_data.data
    assert u_payload.get("count", 0) >= 1
    assert isinstance(u_payload.get("utterances", []), list)

    # 4) Write JSONL in tmp_path
    out_path = tmp_path / "utterances.jsonl"
    writer = ABMAggregatedJsonlWriter(utterances_data=utterances_data, output_path=str(out_path))
    write_result = writer.write().data

    assert out_path.exists()
    assert write_result.get("utterances_written", 0) == u_payload.get("count", 0)

    # Sanity: parse a few records
    with out_path.open("r", encoding="utf-8") as f:
        first_lines = [next(f) for _ in range(min(3, write_result.get("utterances_written", 0)))]
    for line in first_lines:
        obj = json.loads(line)
        assert "text" in obj and "role" in obj
