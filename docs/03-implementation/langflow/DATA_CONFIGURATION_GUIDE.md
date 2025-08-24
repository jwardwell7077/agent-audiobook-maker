# Data Configuration Guide

This guide shows how to configure data paths and work with the ABM data structure in LangFlow workflows.

## Data Structure Overview

The Agent Audiobook Maker uses a standardized directory structure:

```text
data/
├── books/          # Raw book files (PDF, EPUB, etc.)
├── clean/          # Processed text files
│   └── {book_id}/
│       ├── chapters.json    # Structured chapter data
│       └── chapters.txt     # Fallback plain text
└── annotations/    # Generated annotations
    └── {book_id}/
        ├── utterances.jsonl    # Dialogue/narration segments
        └── processed_*.jsonl   # Various processing outputs
```

## Environment Configuration

Set these variables in your `.env` file:

```bash
# Data directories
ABM_DATA_ROOT=/path/to/your/data
ABM_BOOKS_DIR=${ABM_DATA_ROOT}/books
ABM_CLEAN_DIR=${ABM_DATA_ROOT}/clean
ABM_ANNOTATIONS_DIR=${ABM_DATA_ROOT}/annotations

# LangFlow component paths
PYTHONPATH=${PYTHONPATH}:/path/to/audio-book-maker-lg/lf_components
```

## ABMDataConfig Component Usage

The ABMDataConfig component provides standardized data paths for all workflow components.

### Input Configuration

- **Book Name**: The book identifier (e.g., "mvs", "lotr", "pride-prejudice")

### Output Paths

When configured with `book_name="mvs"`, the component provides:

```python
{
    "books_dir": "/home/user/data/books",
    "clean_dir": "/home/user/data/clean", 
    "annotations_dir": "/home/user/data/annotations",
    "book_clean_dir": "/home/user/data/clean/mvs",
    "book_annotations_dir": "/home/user/data/annotations/mvs",
    "chapters_file": "/home/user/data/clean/mvs/chapters.json"
}
```

## Sample Data Flow

A typical processing workflow follows this pattern:

1. **ABMDataConfig** → Provides standardized paths
2. **ABMChapterVolumeLoader** → Loads `chapters.json` or falls back to `.txt`
3. **ABMChapterSelector** → Selects specific chapters for processing
4. **ABMSegmentDialogueNarration** → Segments text into dialogue/narration
5. **ABMUtteranceFilter** → Applies quality filters
6. **ABMUtteranceJsonlWriter** → Outputs to annotation directory

## Working with Sample Data

### MVS Sample Dataset

The "mvs" (sample fantasy novel) dataset includes:

- **chapters.json**: 9 chapters with rich metadata (4900+ lines)
- **segments_test.jsonl**: 703 pre-processed segments
- **Mixed content**: Dialogue, narration, chapter transitions

Perfect for testing the complete pipeline with realistic data.

### Loading Sample Data

```python
# In LangFlow workflow:
# 1. Set ABMDataConfig book_name = "mvs"
# 2. Connect to ABMChapterVolumeLoader
# 3. Component automatically loads /data/clean/mvs/chapters.json
```

## Data Path Best Practices

### Directory Organization

- Keep book identifiers short and filesystem-safe
- Use consistent naming across clean and annotations directories
- Maintain fallback .txt files for debugging

### File Naming Conventions

- `chapters.json` - Structured chapter data with metadata
- `chapters.txt` - Plain text fallback for testing
- `utterances.jsonl` - Standard segmentation output
- `processed_*.jsonl` - Component-specific outputs

### Environment Setup

- Set environment variables in `.env` file at project root
- Use absolute paths to avoid configuration issues
- Test path resolution with sample data first

## Troubleshooting

### Common Path Issues

**Component not finding data files:**

1. Verify `.env` file exists and paths are correct
2. Check file permissions on data directories
3. Confirm book identifier matches directory name

**LangFlow can't discover components:**

1. Verify `PYTHONPATH` includes `lf_components` directory
2. Restart LangFlow after environment changes
3. Check component loading in LangFlow logs

### Testing Configuration

Use the ABMDataConfig component output to verify paths:

1. Add component to workflow
2. Set book_name to known sample (e.g., "mvs")
3. Run workflow and check output paths
4. Verify files exist at reported paths

## Related Documentation

- [Setup Guide](SETUP_GUIDE.md) - Environment and LangFlow setup
- [Workflows Guide](WORKFLOWS.md) - Pre-built workflow examples
- [Component Success](LANGFLOW_COMPONENT_SUCCESS.md) - Component testing results
