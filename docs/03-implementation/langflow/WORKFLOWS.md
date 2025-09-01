# LangFlow Workflow Examples

> **Purpose**: Pre-built workflows and usage examples for audiobook processing components.

This document provides working examples of LangFlow workflows for different audiobook processing scenarios.

## Two-Agent Processing Workflow (Unified)

### Overview

The MVP workflow demonstrates the complete audiobook processing pipeline using sample data.

**Components**: ABMChapterLoader → ABMBlockSchemaValidator → ABMMixedBlockResolver → ABMSpanClassifier → ABMSpanAttribution → (optional) ABMStylePlanner → ABMSpanIterator → ABM Results → Utterances → ABMAggregatedJsonlWriter

### Pre-built Flow

**Location**: `examples/langflow/abm_spans_first_pipeline.v15.json`

**Features**:

- Processes first 3 chapters of MVS sample data
- Filters utterances by length and quality criteria
- Outputs structured JSONL for audio generation pipeline
- Includes error handling and validation

### Manual Setup

If building from scratch in LangFlow UI:

1. **Add ABMChapterLoader**
   - Set book_name: "mvs"
   - Set chapter_index: 1
   - Set base_data_dir: absolute path to `data/clean`

2. **Add ABMSpanIterator**
   - Connect Chapter Loader `blocks_data` → Iterator `blocks_data`
   - Use defaults for batch and priority

3. **Add Classifier → Attribution → (Optional) Style Planner → Aggregator**
   - Connect in series
   - Disable LLMs for deterministic offline tests (if available)
   - If including Style Planner, connect `ABMStylePlanner.spans_style` to downstream nodes; enable its disk writes to produce `spans_style.jsonl`.

4. **Add Results → Utterances → Aggregated JSONL Writer**
   - Set writer `output_path`
   - Connect outputs in series

### Expected Results

**Processing Stats**:

- Input: 1 chapter (configurable)
- Output: Normalized utterances v0.2 JSONL + sidecar meta
- Types: Dialogue, narration, mixed; speaker attribution applied

## Sample Data Workflows

### Full Book Processing

- Loop chapter_index across chapters or extend loader to selection ranges
- Adjust writer output path per chapter/book

### Single Chapter Testing

- Use chapter_index=1
- Reduce max_blocks in iterator for quick iteration
- Enable verbose logging for debugging

### Optional Filtering

- If you need post-normalization filtering, add a simple Data Transformer or custom filter after Results → Utterances

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
