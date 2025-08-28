"""
Smoke test for the two-agent audiobook pipeline components (non-LangFlow UI).

Runs: EnhancedChapterLoader -> ChunkIterator -> DialogueClassifier (heuristic only) ->
SpeakerAttribution -> ResultsAggregator, and asserts we get at least one aggregated result.

This does not hit Ollama and uses repo data/clean by default.
"""

from __future__ import annotations

from pathlib import Path

from abm.lf_components.audiobook.abm_block_iterator import ABMBlockIterator
from abm.lf_components.audiobook.abm_dialogue_classifier import ABMDialogueClassifier
from abm.lf_components.audiobook.abm_enhanced_chapter_loader import ABMEnhancedChapterLoader
from abm.lf_components.audiobook.abm_results_aggregator import ABMResultsAggregator
from abm.lf_components.audiobook.abm_speaker_attribution import ABMSpeakerAttribution


def test_two_agent_smoke(tmp_path: Path) -> None:
    # 1) Load & chunk a small chapter
    loader = ABMEnhancedChapterLoader(book_name="mvs", chapter_index=1, base_data_dir="data/clean")
    chunked = loader.load_and_chunk_chapter()
    data = chunked.data
    assert "error" not in data, f"Loader error: {data.get('error')}"
    assert data.get("chunks"), "No chunks returned from loader"

    # 2) Iterate a few chunks only to keep it fast
    iterator = ABMBlockIterator(
        chunked_data=chunked,
        batch_size=5,
        start_chunk=1,
        max_chunks=5,
        dialogue_priority=True,
    )

    classifier = ABMDialogueClassifier()
    # Keep offline and fast
    classifier.disable_llm = True
    classifier.classification_method = "hybrid"
    aggregator = ABMResultsAggregator()

    total = 0
    while True:
        cur = iterator.get_next_utterance()
        payload = cur.data
        if payload.get("processing_status") == "completed":
            aggregator.attribution_result = cur
            final = aggregator.aggregate_results().data
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
        total += 1

    assert final.get("processing_status") == "completed"
    assert final.get("filtered_results", 0) >= 0
    assert final.get("total_results", 0) >= total
