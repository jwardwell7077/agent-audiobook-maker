"""ABM Chapter Selector Component for LangFlow."""

from langflow.custom import Component
from langflow.io import DataInput, IntInput, Output, StrInput
from langflow.schema import Data


class ABMChapterSelector(Component):
    display_name = "ABM Chapter Selector"
    description = "Select a single chapter by index or title match"
    icon = "filter"
    name = "ABMChapterSelector"

    inputs = [
        DataInput(
            name="chapters_data",
            display_name="Chapters Data",
            info="Data containing chapters to select from",
            required=True,
        ),
        IntInput(
            name="chapter_index",
            display_name="Chapter Index",
            info="Exact chapter index to select (optional)",
            required=False,
        ),
        StrInput(
            name="title_contains",
            display_name="Title Contains",
            info="Select chapter if title contains this text (optional)",
            required=False,
        ),
    ]

    outputs = [Output(name="selected_chapter", display_name="Selected Chapter", method="select_chapter")]

    def select_chapter(self) -> Data:
        """Select a single chapter from chapters data."""
        try:
            input_data = self.chapters_data.data
            if "error" in input_data:
                self.status = "Input contains error, passing through"
                return Data(data=input_data)
            chapters = input_data.get("chapters", [])
            if not chapters:
                error_msg = "No chapters provided in input data"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})
            selected = None

            # Try selection by index first
            if self.chapter_index is not None:
                for chapter in chapters:
                    if int(chapter.get("index", -1)) == self.chapter_index:
                        selected = chapter
                        break
            # Try selection by title contains
            elif self.title_contains:
                needle = self.title_contains.lower()
                for chapter in chapters:
                    title = str(chapter.get("title", ""))
                    if needle in title.lower():
                        selected = chapter
                        break
            else:
                # Default to first chapter
                selected = chapters[0]
            if selected is None:
                error_msg = "Chapter not found with given criteria"
                self.status = f"Error: {error_msg}"
                return Data(data={"error": error_msg})

            result_data = {
                "chapters": [selected],
                "book": input_data.get("book"),
                "volume": input_data.get("volume"),
                "total_chapters": 1,
            }

            chapter_title = selected.get("title", "Unknown")
            self.status = f"Selected chapter: {chapter_title}"
            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to select chapter: {str(e)}"
            self.status = f"Error: {error_msg}"
            return Data(data={"error": error_msg})
