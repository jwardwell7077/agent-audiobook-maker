"""ABM Segment Dialogue Narration Component for LangFlow."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema import Data


class ABMSegmentDialogueNarration(Component):
    display_name = "ABM Segment Dialogue Narration"
    description = "Segment chapter text into dialogue and narration parts"
    icon = "message-square"
    name = "ABMSegmentDialogueNarration"

    inputs = [
        DataInput(
            name="chapters_data",
            display_name="Chapters Data",
            info="Data containing chapters to segment",
            required=True,
        )
    ]

    outputs = [Output(name="segmented_data", display_name="Segmented Data", method="segment_chapters")]

    def segment_chapters(self) -> Data:
        """Segment chapter text into dialogue and narration."""
        try:
            input_data = self.chapters_data.data

            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)

            chapters = input_data.get("chapters", [])
            if not chapters:
                self.status = "No chapters to segment"
                return Data(data=input_data)

            segmented_chapters = []
            total_segments = 0

            for chapter in chapters:
                # Require paragraphs[] schema
                if not isinstance(chapter.get("paragraphs"), list):
                    continue
                para_list = [p for p in chapter.get("paragraphs") if isinstance(p, str) and p.strip()]
                body_text = "\n\n".join(para_list)

                # Advanced segmentation: accumulate lines until blank line
                chapter_segments = []
                buf = []
                buf_has_quote = False

                def flush_segment(segments_list, buffer, has_quote):
                    """Flush accumulated buffer to segments list."""
                    if not buffer:
                        return [], False
                    chunk = "\n".join(buffer).strip()
                    if chunk:
                        segment = {
                            "text": chunk,
                            "type": ("dialogue" if has_quote else "narration"),
                            "length": len(chunk),
                        }
                        segments_list.append(segment)
                    return [], False

                for raw_line in body_text.splitlines():
                    line = raw_line.rstrip()
                    if not line:
                        buf, buf_has_quote = flush_segment(chapter_segments, buf, buf_has_quote)
                        continue
                    buf.append(line)
                    if '"' in line:
                        buf_has_quote = True

                # Don't forget final segment
                buf, buf_has_quote = flush_segment(chapter_segments, buf, buf_has_quote)

                # Fallback: if no segments were created by line-based logic, use paragraphs as segments
                if not chapter_segments:
                    for p in para_list:
                        p_text = p.strip()
                        if not p_text:
                            continue
                        chapter_segments.append(
                            {
                                "text": p_text,
                                "type": ("dialogue" if '"' in p_text else "narration"),
                                "length": len(p_text),
                            }
                        )

                segmented_chapter = {
                    "chapter_index": chapter.get("index"),
                    "chapter_title": chapter.get("title"),
                    "segments": chapter_segments,
                    "total_segments": len(chapter_segments),
                }
                segmented_chapters.append(segmented_chapter)
                total_segments += len(chapter_segments)

            result_data = {
                "segmented_chapters": segmented_chapters,
                "total_chapters": len(segmented_chapters),
                "total_segments": total_segments,
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
            }

            self.status = f"Segmented {len(segmented_chapters)} chapters into {total_segments} segments"
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to segment chapters: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})


def run(chapters_data: dict) -> dict:
    """Convenience wrapper to segment using plain dict input.

    Expects data exactly as produced by chapter_volume_loader.run(...).
    """
    comp = ABMSegmentDialogueNarration()
    comp.chapters_data = Data(data=chapters_data)
    return comp.segment_chapters().data
