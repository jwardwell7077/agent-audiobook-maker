# LangFlow Workflow Examples

> **Purpose**: Pre-built workflows and usage examples for audiobook processing components.

This document provides working examples of LangFlow workflows for different audiobook processing scenarios.

## MVP Processing Workflow

### Overview

The MVP workflow demonstrates the complete audiobook processing pipeline using sample data.

**Components**: DataConfig → ChapterLoader → ChapterSelector → DialogueSegmentation → UtteranceFilter → JSONLWriter

### Pre-built Flow

**Location**: `examples/langflow/mvp_audiobook_processing_flow.json`

**Features**:

- Processes first 3 chapters of MVS sample data
- Filters utterances by length and quality criteria
- Outputs structured JSONL for audio generation pipeline
- Includes error handling and validation

### Manual Setup

If building from scratch in LangFlow UI:

1. **Add ABMDataConfig Component**
   - Set book_id: "mvs"
   - Enable validate_paths

2. **Add ABMChapterVolumeLoader Component**
   - Set book_name: "mvs"
   - Set volume_number: 1
   - Connect to data config if needed

3. **Add ABMChapterSelector Component**
   - Set selection_mode: "range"
   - Set chapter_range: "1-3"
   - Connect to chapter loader output

4. **Add ABMSegmentDialogueNarration Component**
   - Use default dialogue markers
   - Connect to chapter selector output

5. **Add ABMUtteranceFilter Component**
   - Set min_length: 50
   - Set max_length: 5000
   - Enable preserve_dialogue
   - Connect to segmentation output

6. **Add ABMUtteranceJsonlWriter Component**
   - Set output_file path
   - Enable include_metadata
   - Connect to filter output

### Expected Results

**Processing Stats**:

- Input: ~9 chapters available, 3 processed
- Output: Filtered utterances in JSONL format
- Types: Dialogue and narration segments
- Quality: Length and content filtering applied

## Sample Data Workflows

### Full Book Processing

For processing all available chapters:

**Configuration Changes**:

- ABMChapterSelector: selection_mode="all"
- Increase filter limits for full content
- Adjust output file naming for full dataset

### Single Chapter Testing

For development and testing:

**Configuration Changes**:

- ABMChapterSelector: selection_mode="specific", specific_chapters="1"
- Reduce processing time for quick iteration
- Enable verbose logging for debugging

### Quality Filtering Variations

Different filtering approaches:

**Strict Filtering**:

- min_length: 100
- max_length: 2000
- Enable all quality filters

**Permissive Filtering**:

- min_length: 10
- max_length: 10000
- Preserve all dialogue

## Advanced Workflows

### Character-Specific Processing

Future enhancement for speaker identification:

**Planned Components**:

- Speaker identification component
- Character voice mapping
- Dialogue attribution validation

### Multi-Book Processing

Batch processing multiple books:

**Planned Enhancements**:

- Book enumeration component
- Batch processing orchestration
- Cross-book quality normalization

## Troubleshooting Workflows

### Common Issues

**Component Connection Problems**:

- Verify data type compatibility
- Check component configuration
- Ensure proper input/output mapping

**Data Path Issues**:

- Verify environment variables
- Check file permissions
- Validate sample data existence

**Performance Issues**:

- Reduce chapter count for testing
- Monitor memory usage
- Check component execution times

### Debugging Steps

1. **Test Individual Components**
   - Run components separately
   - Verify input/output data
   - Check component logs

2. **Validate Data Flow**
   - Inspect intermediate outputs
   - Verify data transformations
   - Check component status indicators

3. **Check Configuration**
   - Verify parameter settings
   - Test with minimal configuration
   - Compare with working examples

## Related Documentation

- [Setup Guide](SETUP_GUIDE.md) - Component installation and configuration
- [Component Specifications](../../02-specifications/components/README.md) - Detailed component requirements
- [Data Schemas](../../02-specifications/data-schemas/README.md) - Data structure definitions

---

*Part of [LangFlow Implementation](README.md) | [Implementation Guide](../README.md)*
