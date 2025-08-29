"""ABM Results Aggregator for Two-Agent Pipeline Output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, FloatInput, Output
from langflow.schema import Data


class ABMResultsAggregator(Component):
    display_name = "ABM Results Aggregator"
    description = "Aggregate and validate two-agent processing results"
    icon = "database"
    name = "ABMResultsAggregator"

    inputs = [
        DataInput(
            name="attribution_result",
            display_name="Attribution Result",
            info="Output from Agent 2 (Speaker Attribution)",
            required=True,
        ),
        FloatInput(
            name="min_confidence_threshold",
            display_name="Minimum Confidence Threshold",
            info="Filter results below this confidence",
            value=0.3,
            required=False,
        ),
        BoolInput(
            name="include_metadata",
            display_name="Include Processing Metadata",
            info="Add detailed processing information to output",
            value=True,
            required=False,
        ),
        BoolInput(
            name="validate_results",
            display_name="Validate Results",
            info="Run quality validation on aggregated results",
            value=True,
            required=False,
        ),
    ]

    outputs = [
        Output(display_name="Aggregated Results", name="aggregated_results", method="aggregate_results"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self._accumulated_results: list[dict[str, Any]] = []
        self._processing_stats = _Stats()

    def aggregate_results(self) -> Data:
        """Aggregate results from two-agent processing pipeline."""
        try:
            input_data = self.attribution_result.data

            # Handle completion summary (when all chunks processed)
            if input_data.get("processing_status") == "completed":
                return self._finalize_aggregation(input_data)

            # Handle errors
            if "error" in input_data:
                self.status = f"Input error: {input_data['error']}"
                return Data(data=input_data)

            # Process attribution result
            processed_result = self._process_attribution_result(input_data)

            # Add to accumulated results
            self._accumulated_results.append(processed_result)
            self._update_stats(processed_result)

            # Update status
            self.status = f"Aggregated {len(self._accumulated_results)} results"

            # Return current result (for debugging/monitoring)
            return Data(
                data={
                    "current_result": processed_result,
                    "aggregation_status": "accumulating",
                    "total_accumulated": len(self._accumulated_results),
                    "current_stats": asdict(self._processing_stats),
                }
            )

        except Exception as e:
            error_msg = f"Failed to aggregate results: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})

    def _process_attribution_result(self, attribution_data: dict[str, Any]) -> dict[str, Any]:
        """Process and standardize attribution result."""

        # Extract core attribution data
        character_id = attribution_data.get("character_id")
        character_name = attribution_data.get("character_name")
        dialogue_text = attribution_data.get("dialogue_text", "")

        # Get speaker attribution details
        speaker_attribution = attribution_data.get("speaker_attribution", {})
        confidence = speaker_attribution.get("confidence", 0.0)
        method = speaker_attribution.get("method", "unknown")
        reasoning = speaker_attribution.get("reasoning", "")

        # Get original classification info
        original_classification = attribution_data.get("original_classification", "unknown")

        # Prefer dialogue text, but fall back to full/utterance text
        text_value = (
            attribution_data.get("dialogue_text")
            or attribution_data.get("full_text")
            or attribution_data.get("utterance_text", "")
        )

        full_text_value = (
            attribution_data.get("full_text") or attribution_data.get("utterance_text") or dialogue_text or ""
        )

        # Sensible speaker fallback for narration
        if (not character_name) and (original_classification or "").lower() == "narration":
            character_name = "Narrator"
            character_id = character_id or "narrator"

        # Create standardized result
        processed_result = {
            # Identification
            "book_id": attribution_data.get("book_id", ""),
            "chapter_id": attribution_data.get("chapter_id", ""),
            "utterance_idx": attribution_data.get("utterance_idx", 0),
            # Content
            "text": text_value,
            "full_text": full_text_value,
            "classification": original_classification,
            # Speaker Attribution
            "character_id": character_id,
            "character_name": character_name or "Unknown Speaker",
            "attribution_confidence": confidence,
            "attribution_method": method,
            "attribution_reasoning": reasoning,
            # Quality Metrics
            "confidence_level": self._categorize_confidence(confidence),
            "processing_quality": self._assess_processing_quality(attribution_data),
            # Context
            "context_before": attribution_data.get("context_before", ""),
            "context_after": attribution_data.get("context_after", ""),
            # Speech Analysis
            "speech_patterns": attribution_data.get("speech_patterns", {}),
            # Metadata
            "processing_metadata": attribution_data.get("processing_info", {}) if self.include_metadata else {},
            "aggregated_at": datetime.utcnow().isoformat(),
        }

        return processed_result

    def _update_stats(self, result: dict[str, Any]) -> None:
        """Update processing statistics."""
        self._processing_stats.total_processed += 1

        # Count by classification
        classification = result.get("classification", "").lower()
        if "dialogue" in classification:
            self._processing_stats.dialogue_count += 1
        elif "narration" in classification:
            self._processing_stats.narration_count += 1

        # Count attributed speakers
        if result.get("character_id"):
            self._processing_stats.attributed_speakers += 1
            character_name = result.get("character_name", "")
            if character_name and character_name != "Unknown Speaker":
                self._processing_stats.characters_identified.add(character_name)

        # Count by confidence
        confidence = float(result.get("attribution_confidence", 0.0))
        if confidence >= 0.7:
            self._processing_stats.high_confidence_count += 1
        elif confidence < self.min_confidence_threshold:
            self._processing_stats.low_confidence_count += 1

    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence level."""
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"

    def _assess_processing_quality(self, attribution_data: dict[str, Any]) -> dict[str, Any]:
        """Assess the quality of processing for this utterance."""
        quality_metrics = {
            "has_character_attribution": bool(attribution_data.get("character_id")),
            "has_dialogue_text": bool(attribution_data.get("dialogue_text", "").strip()),
            "has_context": bool(
                attribution_data.get("context_before", "") or attribution_data.get("context_after", "")
            ),
            "confidence_acceptable": attribution_data.get("speaker_attribution", {}).get("confidence", 0)
            >= self.min_confidence_threshold,
        }

        # Calculate overall quality score
        quality_score = sum(quality_metrics.values()) / len(quality_metrics)
        quality_metrics["overall_score"] = quality_score
        quality_metrics["quality_level"] = (
            "high" if quality_score >= 0.8 else "medium" if quality_score >= 0.6 else "low"
        )

        return quality_metrics

    def _finalize_aggregation(self, completion_data: dict[str, Any]) -> Data:
        """Create final aggregated results."""
        # Filter results by confidence if needed
        filtered_results: list[dict[str, Any]] = (
            [
                result
                for result in self._accumulated_results
                if result.get("attribution_confidence", 0) >= self.min_confidence_threshold
            ]
            if self.min_confidence_threshold > 0
            else self._accumulated_results
        )

        # Run validation if enabled
        validation_results = self._validate_results(filtered_results) if self.validate_results else {}

        # Create final statistics
        final_stats = asdict(self._processing_stats)
        final_stats["characters_identified"] = list(final_stats["characters_identified"])
        final_stats["filtered_results_count"] = len(filtered_results)
        final_stats["processing_completion_time"] = datetime.utcnow().isoformat()

        # Create final aggregated data
        aggregated_data = {
            "processing_status": "completed",
            "total_results": len(self._accumulated_results),
            "filtered_results": len(filtered_results),
            "results": filtered_results,
            "statistics": final_stats,
            "validation": validation_results,
            "chapter_info": completion_data.get("summary", {}).get("chapter_info", {}),
            "aggregation_metadata": {
                "min_confidence_threshold": self.min_confidence_threshold,
                "include_metadata": self.include_metadata,
                "validation_enabled": self.validate_results,
                "aggregated_at": datetime.utcnow().isoformat(),
            },
        }

        self.status = f"Aggregation completed: {len(filtered_results)} results ready"

        # Reset for next chapter
        self._reset_aggregator()

        return Data(data=aggregated_data)

    def _validate_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Run quality validation on aggregated results."""
        if not results:
            return {"status": "no_results_to_validate"}

        validation: dict[str, Any] = {
            "total_validated": len(results),
            "dialogue_attribution_rate": 0.0,
            "high_confidence_rate": 0.0,
            "character_consistency": [],
            "quality_issues": [],
        }

        # Calculate dialogue attribution rate
        dialogue_results = [r for r in results if "dialogue" in r.get("classification", "").lower()]
        attributed_dialogue = [r for r in dialogue_results if r.get("character_id")]
        validation["dialogue_attribution_rate"] = (
            len(attributed_dialogue) / len(dialogue_results) if dialogue_results else 0.0
        )

        # Calculate high confidence rate
        high_confidence_results = [r for r in results if r.get("attribution_confidence", 0) >= 0.7]
        validation["high_confidence_rate"] = len(high_confidence_results) / len(results)

        # Check character consistency
        character_names: dict[str, set[str]] = {}
        for result in results:
            char_name = result.get("character_name", "")
            char_id = result.get("character_id", "")
            if char_name and char_id:
                if char_name not in character_names:
                    character_names[char_name] = set()
                character_names[char_name].add(char_id)

        validation["character_consistency"] = [
            {"character": name, "character_ids": list(ids), "consistent": len(ids) == 1}
            for name, ids in character_names.items()
        ]

        # Identify quality issues
        if validation["dialogue_attribution_rate"] < 0.7:
            validation["quality_issues"].append("Low dialogue attribution rate")
        if validation["high_confidence_rate"] < 0.6:
            validation["quality_issues"].append("Low high-confidence attribution rate")

        validation["status"] = "passed" if not validation["quality_issues"] else "issues_detected"

        return validation

    def _reset_aggregator(self) -> None:
        """Reset aggregator state for next processing batch."""
        self._accumulated_results = []
        self._processing_stats = _Stats()


@dataclass
class _Stats:
    total_processed: int = 0
    dialogue_count: int = 0
    narration_count: int = 0
    attributed_speakers: int = 0
    high_confidence_count: int = 0
    low_confidence_count: int = 0
    characters_identified: set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.characters_identified is None:
            self.characters_identified = set()
