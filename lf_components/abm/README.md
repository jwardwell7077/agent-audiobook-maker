# ABM LangFlow Components

These are class-based custom components auto-loaded by LangFlow when launched with:

- scripts/run_langflow.sh (already passes --components-path lf_components)

They appear under the "abm" category in the sidebar.

Components:

- Chapter Volume Loader: load book chapters from data/books.
- Chapter Selector: pick one chapter by index or title substring.
- Segment Dialogue/Narration: naive line-based segmentation.
- Utterance Filter: filter by role/length/contains.
- Utterance JSONL Writer: write utterances to JSONL.
