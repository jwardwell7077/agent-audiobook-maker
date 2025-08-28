"""ABM Results → Utterances normalizer for LangFlow.

Takes aggregated two-agent results and emits a normalized `utterances` list with
v0.2 fields used by writers and the Character Data Collector.
"""

from __future__ import annotations

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema import Data


class ABMResultsToUtterances(Component):
    display_name = "ABM Results → Utterances"
    description = "Normalize aggregated results into standard utterances schema"
    icon = "table"
    name = "ABMResultsToUtterances"

    inputs = [
        DataInput(
            name="aggregated_results",
            display_name="Aggregated Results",
            info="Output from ABMResultsAggregator (processing_status=completed)",
            required=True,
        )
    ]

    outputs = [
        Output(display_name="Utterances Data", name="utterances_data", method="to_utterances"),
    ]

    def to_utterances(self) -> Data:
        data = self.aggregated_results.data
        if "error" in data:
            self.status = "Input contains error, passing through"
            return Data(data=data)

        results = data.get("results") or []
        utterances = [
            {
                "book_id": r.get("book_id", ""),
                "chapter_id": r.get("chapter_id", ""),
                "utterance_idx": r.get("utterance_idx", 0),
                "role": r.get("classification", "unknown"),
                "text": r.get("text") or r.get("full_text", ""),
                "speaker": r.get("character_name"),
                "speaker_confidence": r.get("attribution_confidence"),
                "context_before": r.get("context_before", ""),
                "context_after": r.get("context_after", ""),
            }
            for r in results
        ]

        payload = {
            "utterances": utterances,
            "count": len(utterances),
            "chapter_info": data.get("chapter_info", {}),
        }

        self.status = f"Normalized {len(utterances)} utterances"
        return Data(data=payload)
