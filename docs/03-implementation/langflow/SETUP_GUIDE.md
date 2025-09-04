# LangFlow Setup and Usage Guide

> **Purpose**: Complete guide for setting up and using LangFlow components for audiobook processing workflows.

This guide covers everything needed to set up, configure, and run LangFlow workflows for the Agent Audiobook Maker project.

## Prerequisites

### System Requirements

- Python 3.11+
- Active virtual environment with project dependencies
- LangFlow v1.5.0.post2 or compatible version

### Project Setup

```bash
# Ensure you're in the project directory
cd /path/to/audio-book-maker-lg

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements-dev.txt
```

## Environment Configuration

### Required Environment Variables

Create or update `.env` file in project root:

```bash
# Core data directories
ABM_DATA_ROOT=/home/jon/repos/audio-book-maker-lg/data
ABM_BOOKS_DIR=/home/jon/repos/audio-book-maker-lg/data/books
ABM_CLEAN_DIR=/home/jon/repos/audio-book-maker-lg/data/clean
ABM_ANNOTATIONS_DIR=/home/jon/repos/audio-book-maker-lg/data/annotations

# LangFlow component path
LANGFLOW_COMPONENTS_PATH=/home/jon/repos/audio-book-maker-lg/src/abm/lf_components
```

### Component Discovery

LangFlow automatically discovers components from:

- Path: `src/abm/lf_components/audiobook/`
- Category: "Audiobook" in LangFlow UI
- Requirements: Must inherit from `langflow.custom.Component`

## Starting LangFlow

### Launch Server

```bash
# Use the provided script (recommended)
./scripts/run_langflow.sh

# Server will start at http://localhost:7860
```

### Verify Component Loading

Check terminal output for:

```text
✓ Loading Components...
[run_langflow] Components directory tree:
  audiobook/abm_chapter_volume_loader.py
  audiobook/abm_chapter_selector.py
  audiobook/abm_data_config.py
  audiobook/abm_segment_dialogue_narration.py
  audiobook/abm_utterance_filter.py
  audiobook/abm_utterance_jsonl_writer.py
```

## Component Configuration

### ABM Data Config

**Purpose**: Provides standardized data paths for all components

**Configuration**:

- `data_root`: Root directory for all data (uses ABM_DATA_ROOT env var)
- `book_id`: Book identifier (e.g., "mvs")
- `validate_paths`: Whether to validate that paths exist

**Outputs**:

```python
{
    "books_dir": "/path/to/data/books",
    "clean_dir": "/path/to/data/clean",
    "annotations_dir": "/path/to/data/annotations",
    "book_clean_dir": "/path/to/data/clean/mvs",
    "book_annotations_dir": "/path/to/data/annotations/mvs",
    "chapters_file": "/path/to/data/clean/mvs/chapters.json"
}
```

### ABM Chapter Volume Loader

**Purpose**: Loads chapter data from JSON files

**Configuration**:

- `book_name`: Book identifier (e.g., "mvs")
- `volume_number`: Volume to load (default: 1)
- `base_data_dir`: Base directory for book data

**Sample Data**: Uses MVS sample data with 9 chapters

### ABM Chapter Selector

**Purpose**: Selects specific chapters for processing

**Configuration**:

- `selection_mode`: "all", "range", or "specific"
- `chapter_range`: Range like "1-3" (for range mode)
- `specific_chapters`: Comma-separated indices (for specific mode)

### ABM Segment Dialogue Narration

**Purpose**: Segments chapters into dialogue and narration

**Algorithm**: Quote-based detection using paragraph structure **Configuration**:

- `min_segment_length`: Minimum segment length in characters
- `dialogue_markers`: Characters indicating dialogue (default: quotation marks)

### ABM Utterance Filter

**Purpose**: Filters utterances based on quality criteria

**Configuration**:

- `min_length`: Minimum utterance length (default: 50)
- `max_length`: Maximum utterance length (default: 5000)
- `filter_empty`: Remove empty utterances (default: true)
- `preserve_dialogue`: Keep dialogue even if it fails other filters

### ABM Utterance JSONL Writer

**Purpose**: Exports processed utterances to JSONL format

**Configuration**:

- `output_file`: Path for output JSONL file
- `include_metadata`: Whether to include chapter metadata

## Building Workflows

### Basic Flow Pattern

Standard audiobook processing workflow:

1. **ABM Data Config** → Configure paths
1. **ABM Chapter Volume Loader** → Load chapter data
1. **ABM Chapter Selector** → Select chapters to process
1. **ABM Segment Dialogue Narration** → Create segments
1. **ABM Utterance Filter** → Filter by quality
1. **ABM Utterance JSONL Writer** → Export results

### Connecting Components

1. **Add Components**: Drag from "Audiobook" category
1. **Connect Outputs to Inputs**: Link compatible data types
1. **Configure Parameters**: Set component-specific values
1. **Test Connections**: Verify data flows correctly

## Sample Workflows

### MVP Processing Flow

Pre-built workflow available at: `examples/langflow/mvp_audiobook_processing_flow.json`

**Features**:

- Processes first 3 chapters of MVS sample data
- Filters utterances by length and quality
- Outputs structured JSONL for audio generation

**To Import**:

1. Open LangFlow UI
1. Look for import/upload functionality
1. Select the MVP flow JSON file
1. Configure output paths as needed

### Testing with Sample Data

**Available Sample Data**:

- Book: "mvs" (fantasy novel)
- Chapters: 9 available (4900+ lines of JSON)
- Content: Rich dialogue and narration
- Location: `data/clean/mvs/chapters.json`

**Quick Test**:

1. Use ABMChapterVolumeLoader with book_name="mvs"
1. Set ABMChapterSelector to range="1-2" for quick test
1. Configure output path for results
1. Run workflow and verify JSONL output

## Troubleshooting

### Components Not Visible

**Issue**: Components don't appear in LangFlow UI **Solution**:

1. Check LANGFLOW_COMPONENTS_PATH environment variable
1. Restart LangFlow server
1. Verify .env file is loaded correctly

### Data Path Errors

**Issue**: Components can't find data files **Solution**:

1. Verify ABM_DATA_ROOT and related paths in .env
1. Check that sample data exists at expected locations
1. Use ABMDataConfig component to validate paths

### Connection Errors

**Issue**: Components won't connect properly **Solution**:

1. Verify compatible data types between components
1. Check component input/output specifications
1. Ensure components are properly configured

## Performance Tips

### Development Workflow

1. **Start Small**: Test with 1-2 chapters initially
1. **Iterative Testing**: Run individual components to debug
1. **Monitor Memory**: Large texts can consume significant memory
1. **Save Frequently**: Export working workflows as JSON

### Production Considerations

- This is Phase 1 prototyping - not production ready
- For production loads, consider the multi-agent approach
- Monitor component execution times for performance optimization

## Related Documentation

- [LangFlow Components](../../02-specifications/components/README.md) - Component specifications
- [Data Schemas](../../02-specifications/data-schemas/README.md) - Data structure definitions
- [Multi-Agent Roadmap](../../05-development/planning/MULTI_AGENT_ROADMAP.md) - Future implementation

______________________________________________________________________

*Part of [LangFlow Implementation](README.md) | [Implementation Guide](../README.md)*
