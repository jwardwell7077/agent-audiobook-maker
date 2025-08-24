# ABM Data Configuration Example

This shows how the ABMDataConfig component provides standardized data paths

## Sample Usage in LangFlow

The ABMDataConfig component provides these data paths when configured with book_name="mvs":

```python
# Outputs from ABMDataConfig component:
{
    "books_dir": "/home/jon/repos/audio-book-maker-lg/data/books",
    "clean_dir": "/home/jon/repos/audio-book-maker-lg/data/clean", 
    "annotations_dir": "/home/jon/repos/audio-book-maker-lg/data/annotations",
    "book_clean_dir": "/home/jon/repos/audio-book-maker-lg/data/clean/mvs",
    "book_annotations_dir": "/home/jon/repos/audio-book-maker-lg/data/annotations/mvs",
    "chapters_file": "/home/jon/repos/audio-book-maker-lg/data/clean/mvs/chapters.json"
}
```

## Environment Variables Used

The component respects these environment variables from the .env file:

- `ABM_DATA_ROOT`: Root directory for all data files
- `ABM_BOOKS_DIR`: Directory containing raw book files
- `ABM_CLEAN_DIR`: Directory containing processed/clean book data
- `ABM_ANNOTATIONS_DIR`: Directory containing annotation data

## Sample Data Flow

1. **ABMDataConfig** → provides paths
2. **ABMChapterVolumeLoader** → loads `/data/clean/mvs/chapters.json`
3. **ABMChapterSelector** → selects chapters 1-3 from loaded data
4. **ABMSegmentDialogueNarration** → segments selected chapters into utterances
5. **ABMUtteranceFilter** → filters utterances by length/quality
6. **ABMUtteranceJsonlWriter** → outputs to `/data/annotations/mvs/processed_utterances.jsonl`

## Testing with Sample Data

The MVS sample data includes:

- 9 chapters in `chapters.json` (over 4900 lines of JSON)
- 703 existing segments in `segments_test.jsonl`
- Rich dialogue and narration content from fantasy novel

Perfect for testing the complete audiobook processing pipeline!
