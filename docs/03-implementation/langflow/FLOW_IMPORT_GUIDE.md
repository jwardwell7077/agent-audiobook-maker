# Flow Import Guide

This guide explains how to import and use pre-built LangFlow workflows for audiobook processing.

## Available Workflows

### MVP Processing Flow

The MVP (Minimum Viable Product) flow demonstrates the complete audiobook annotation pipeline:

**Components**: DataConfig → VolumeLoader → ChapterSelector → SegmentDialogueNarration → UtteranceFilter → JSONLWriter

**Purpose**: Process sample chapters from raw text to annotated utterances

**File**: `mvp_audiobook_processing_flow.json` (when available)

## Import Process

### Step 1: Launch LangFlow

```bash
# From project root
./scripts/run_langflow.sh
```

Wait for LangFlow to start and open your browser to `http://localhost:7860`

### Step 2: Import Workflow

1. **Create New Flow**:
   - Click "New Flow" or the "+" button
   - Select "Import Flow" from the menu

2. **Select Flow File**:
   - Navigate to the flow JSON file
   - Choose the MVP or other pre-built flow

3. **Verify Import**:
   - Components should appear connected in the workflow canvas
   - Check that all components are from the "Audiobook" category

### Step 3: Component Configuration

The imported workflow includes default configuration, but you may need to adjust:

#### ABMDataConfig Settings

- **Book Name**: `mvs` (sample data) or your book identifier
- **Validate Paths**: `true` (ensures data files exist)
- **Custom Data Root**: Leave empty to use environment variables

#### ABMChapterVolumeLoader Settings

- **Chapters File**: Auto-populated from ABMDataConfig
- **Load Full Content**: `true` (includes complete text)
- **Max Chapters**: `3` (limit for testing)

#### ABMChapterSelector Settings

- **Selection Mode**: `range` (select multiple chapters)
- **Chapter Range**: `1-3` (process chapters 1-3)
- Alternative: `single` mode for individual chapters

#### ABMSegmentDialogueNarration Settings

- **Min Segment Length**: `100` characters
- **Dialogue Markers**: `"\"\"''"` (various quotation marks)
- **Include Metadata**: `true` (adds processing info)

#### ABMUtteranceFilter Settings

- **Min Length**: `50` characters (filter very short utterances)
- **Max Length**: `5000` characters (filter very long ones)
- **Filter Empty**: `true` (remove empty segments)
- **Preserve Dialogue**: `true` (keep dialogue even if short)

#### ABMUtteranceJsonlWriter Settings

- **Output File**: Set your desired output path
- **Include Metadata**: `true` (adds chapter/book info)
- **Overwrite Existing**: `false` (safety setting)

## Running Workflows

### Full Workflow Execution

1. **Configure Output**: Set the final output path in JSONLWriter
2. **Run Complete Flow**: Click the "Run Flow" button
3. **Monitor Progress**: Watch component status indicators
4. **Check Results**: Verify output files are created

### Component-by-Component Testing

1. **Test Data Config**: Run ABMDataConfig first to verify paths
2. **Test Loading**: Run VolumeLoader to confirm data loading
3. **Test Selection**: Run ChapterSelector to verify chapter filtering
4. **Test Segmentation**: Run Segmenter to check dialogue detection
5. **Test Filtering**: Run Filter to verify quality criteria
6. **Test Output**: Run Writer to create final output

### Debugging Failed Runs

**Component Shows Error**:

1. Check the component logs in LangFlow
2. Verify input data is properly formatted
3. Ensure file paths exist and are accessible
4. Review component configuration settings

**Pipeline Stops Mid-Flow**:

1. Run components individually to isolate the issue
2. Check data compatibility between components
3. Verify environment variables are set correctly

## Creating Custom Workflows

### Manual Component Assembly

1. **Drag Components**: From "Audiobook" category to canvas
2. **Connect Outputs to Inputs**: Match data types correctly
3. **Configure Each Component**: Set appropriate parameters
4. **Test Connections**: Run individual components first
5. **Save Workflow**: Export as JSON for reuse

### Component Connection Guide

**Valid Connections**:

- ABMDataConfig → ABMChapterVolumeLoader (paths)
- ABMChapterVolumeLoader → ABMChapterSelector (chapters)
- ABMChapterSelector → ABMSegmentDialogueNarration (chapter)
- ABMSegmentDialogueNarration → ABMUtteranceFilter (utterances)
- ABMUtteranceFilter → ABMUtteranceJsonlWriter (utterances)

**Data Flow Validation**:

Each component expects specific data formats. Check output schemas match input requirements.

## Workflow Best Practices

### Testing Strategy

- Start with small datasets (1-3 chapters)
- Test each component individually before full pipeline
- Verify outputs at each stage meet expectations

### Configuration Management

- Export working configurations as JSON files
- Document parameter changes and their effects
- Version control workflow files alongside code

### Performance Optimization

- Use chapter limits for initial testing
- Monitor component execution times
- Consider parallel processing for large books

## Troubleshooting

### Common Import Issues

**Components Not Found**:

1. Verify LangFlow was started with correct PYTHONPATH
2. Check that components are properly installed
3. Restart LangFlow if components were recently added

**Invalid Connections**:

1. Check component output/input data types match
2. Verify components are compatible versions
3. Review component documentation for requirements

### File Path Issues

**Cannot Find Data Files**:

1. Verify environment variables are set correctly
2. Check file permissions on data directories
3. Confirm book identifier matches directory structure

## Related Documentation

- [Setup Guide](SETUP_GUIDE.md) - Environment configuration
- [Data Configuration Guide](DATA_CONFIGURATION_GUIDE.md) - Working with data paths
- [Workflows Guide](WORKFLOWS.md) - Usage patterns and examples
