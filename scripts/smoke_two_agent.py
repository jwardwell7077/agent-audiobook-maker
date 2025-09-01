from __future__ import annotations

import json

from abm.lf_components.audiobook.abm_block_iterator import ABMBlockIterator
from abm.lf_components.audiobook.abm_chapter_loader import ABMChapterLoader
from abm.lf_components.audiobook.abm_dialogue_classifier import ABMDialogueClassifier
from abm.lf_components.audiobook.abm_results_aggregator import ABMResultsAggregator
from abm.lf_components.audiobook.abm_speaker_attribution import ABMSpeakerAttribution


def main() -> None:
    # 1) Load + blocks
    loader = ABMChapterLoader(book_name="SAMPLE_BOOK", base_data_dir="data/clean", chapter_index=1)
    blocks = loader.load_and_blocks()
    if "error" in blocks.data:
        raise SystemExit(f"Loader error: {blocks.data['error']}")

    # 2) Iterate and process with two agents
    iterator = ABMBlockIterator(blocks_data=blocks, batch_size=5, max_blocks=0)
    classifier = ABMDialogueClassifier(disable_llm=True)
    attributor = ABMSpeakerAttribution()
    aggregator = ABMResultsAggregator()

    while True:
        nxt = iterator.get_next_utterance()
        payload = nxt.data
        if payload.get("processing_status") == "completed":
            aggregator.attribution_result = nxt
            final = aggregator.aggregate_results()
            print(json.dumps(final.data, ensure_ascii=False, indent=2))
            break
        if "error" in payload:
            raise SystemExit(f"Iterator error: {payload['error']}")
        classifier.utterance_data = nxt
        classified = classifier.classify_utterance()
        attributor.classified_utterance = classified
        attributed = attributor.attribute_speaker()
        aggregator.attribution_result = attributed
        aggregator.aggregate_results()


if __name__ == "__main__":
    main()
