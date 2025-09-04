# Flow Import Guide

This guide explains how to import and use pre-built LangFlow workflows for audiobook processing.

## Available Workflows

### Two-Agent Processing Flow (Unified)

The unified flow demonstrates the audiobook annotation pipeline using a single loader and the two-agent core:

**Components**: ABMChapterLoader → ABMBlockIterator → ABMDialogueClassifier → ABMSpeakerAttribution → ABMResultsAggregator → ABM Results → Utterances → ABMAggregatedJsonlWriter

**Purpose**: Process a chapter into normalized utterances (v0.2 schema), ready for casting or export

**File**: `abm_full_pipeline.v15.json` (updated to use ABMChapterLoader)

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

1. **Select Flow File**:

   - Navigate to the flow JSON file
   - Choose the MVP or other pre-built flow

1. **Verify Import**:

   - Components should appear connected in the workflow canvas
   - Check that all components are from the "Audiobook" category

### Step 3: Component Configuration

The imported workflow includes defaults; adjust these as needed:

#### ABMChapterLoader

- book_name: e.g., `mvs` (sample data)
- chapter_index: e.g., `1` (0-based index supported by loader)
- base_data_dir: repo `data/clean` absolute path
- context_sentences: `1` or `2` (for surrounding context in blocks)

Outputs available for taps: chapters_data, chapter_data, blocks_data.

#### ABMBlockIterator

- batch_size: `10`
- start_block: `1`
- max_blocks: `0` (all)
- dialogue_priority: `true`

#### ABMDialogueClassifier / ABMSpeakerAttribution

- disable LLMs if you want deterministic offline runs
- set confidence thresholds per your needs

#### ABM Results → Utterances

- normalizes aggregated results to utterances v0.2

#### ABMAggregatedJsonlWriter

- output_path: absolute path to `output/utterances.jsonl`

## Running Workflows

### Full Workflow Execution

1. **Configure Output**: Set the final output path in JSONLWriter
1. **Run Complete Flow**: Click the "Run Flow" button
1. **Monitor Progress**: Watch component status indicators
1. **Check Results**: Verify output files are created

### Component-by-Component Testing

1. Run ABMChapterLoader → verify `blocks_data` has `blocks`
1. Run ABMBlockIterator → verify it emits one `current_utterance` per block
1. Run Dialogue → Attribution → Aggregator → verify completion summary
1. Run Results → Utterances → Writer → verify JSONL is written

### Debugging Failed Runs

**Component Shows Error**:

1. Check the component logs in LangFlow
1. Verify input data is properly formatted
1. Ensure file paths exist and are accessible
1. Review component configuration settings

**Pipeline Stops Mid-Flow**:

1. Run components individually to isolate the issue
1. Check data compatibility between components
1. Verify environment variables are set correctly

## Creating Custom Workflows

### Manual Component Assembly

1. **Drag Components**: From "Audiobook" category to canvas
1. **Connect Outputs to Inputs**: Match data types correctly
1. **Configure Each Component**: Set appropriate parameters
1. **Test Connections**: Run individual components first
1. **Save Workflow**: Export as JSON for reuse

### Component Connection Guide

**Valid Connections**:

- ABMChapterLoader(blocks_data) → ABMBlockIterator(blocks_data)
- ABMBlockIterator(current_utterance) → ABMDialogueClassifier(utterance_data)
- ABMDialogueClassifier(classified_utterance) → ABMSpeakerAttribution(classified_utterance)
- ABMSpeakerAttribution(attribution_result) → ABMResultsAggregator(attribution_result)
- ABMResultsAggregator(aggregated_results) → ABM Results → Utterances(aggregated_results)
- ABM Results → Utterances(utterances_data) → ABMAggregatedJsonlWriter(utterances_data)

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
1. Check that components are properly installed
1. Restart LangFlow if components were recently added

**Invalid Connections**:

1. Check component output/input data types match
1. Verify components are compatible versions
1. Review component documentation for requirements

### File Path Issues

**Cannot Find Data Files**:

1. Use absolute `base_data_dir` for the loader
1. Confirm `data/clean/<book>/chapters.json` exists
1. Check file permissions on data directories

## Related Documentation

- [Setup Guide](SETUP_GUIDE.md) - Environment configuration
- [Workflows Guide](WORKFLOWS.md) - Usage patterns and examples
- Deprecated: older flows using VolumeLoader/Selector/Segmenter/Filter have been removed in favor of ABMChapterLoader
