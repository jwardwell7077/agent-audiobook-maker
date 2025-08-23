"""ABM Utterance Filter Component for LangFlow."""

from langflow.custom import Component
from langflow.io import DataInput, IntInput, Output, StrInput
from langflow.schema import Data


class ABMUtteranceFilter(Component):
    display_name = "ABM Utterance Filter"
    description = "Filter utterances by role, length, and content"
    icon = "filter"
    name = "ABMUtteranceFilter"

    inputs = [
        DataInput(
            name="segmented_data",
            display_name="Segmented Data",
            info="Data containing utterances to filter",
            required=True,
        ),
        StrInput(
            name="role_filter",
            display_name="Role Filter",
            info="Filter by role: 'dialogue' or 'narration' (optional)",
            required=False,
        ),
        IntInput(
            name="min_length",
            display_name="Minimum Length",
            info="Minimum text length in characters (optional)",
            required=False,
        ),
        IntInput(
            name="max_length",
            display_name="Maximum Length",
            info="Maximum text length in characters (optional)",
            required=False,
        ),
        StrInput(
            name="contains_text",
            display_name="Contains Text",
            info="Filter utterances containing this text (optional)",
            required=False,
        ),
    ]

    outputs = [Output(name="filtered_data", display_name="Filtered Data", method="filter_utterances")]

    def filter_utterances(self) -> Data:
        """Filter utterances by specified criteria."""
        try:
            input_data = self.segmented_data.data

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            segmented_chapters = input_data.get("segmented_chapters", [])
            if not segmented_chapters:
                self.status = "No segmented chapters to filter"
                return Data(data=input_data)

            # Normalize filter criteria
            role_norm = self.role_filter.lower() if self.role_filter else None
            contains_norm = self.contains_text.lower() if self.contains_text else None

            filtered_chapters = []
            total_original = 0
            total_filtered = 0

            for chapter in segmented_chapters:
                filtered_segments = []

                for segment in chapter.get("segments", []):
                    total_original += 1
                    text = str(segment.get("text", ""))
                    segment_type = str(segment.get("type", ""))

                    # Apply filters
                    if role_norm and segment_type.lower() != role_norm:
                        continue

                    if self.min_length is not None and len(text) < self.min_length:
                        continue

                    if self.max_length is not None and len(text) > self.max_length:
                        continue

                    if contains_norm and contains_norm not in text.lower():
                        continue

                    filtered_segments.append(segment)
                    total_filtered += 1

                if filtered_segments:  # Only include chapters with segments
                    filtered_chapter = {
                        "chapter_index": chapter.get("chapter_index"),
                        "chapter_title": chapter.get("chapter_title"),
                        "segments": filtered_segments,
                        "total_segments": len(filtered_segments),
                    }
                    filtered_chapters.append(filtered_chapter)

            result_data = {
                "segmented_chapters": filtered_chapters,
                "total_chapters": len(filtered_chapters),
                "total_segments": total_filtered,
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
            }

            self.status = f"Filtered {total_original} → {total_filtered} utterances"
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to filter utterances: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})
