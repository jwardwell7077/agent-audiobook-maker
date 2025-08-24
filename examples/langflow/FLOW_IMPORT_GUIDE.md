# LangFlow MVP Flow Import Guide

## How to Import the MVP Flow

1. **Open LangFlow**: Launch LangFlow using `./scripts/run_langflow.sh`

2. **Import Flow**: In the LangFlow UI
   - Click "New Flow" or the "+" button
   - Select "Import Flow"
   - Choose the file: `examples/langflow/mvp_audiobook_processing_flow.json`

3. **Configure Components**: The flow will load with these components connected:
   - **ABMDataConfig** → **ABMChapterVolumeLoader** → **ABMChapterSelector** → **ABMSegmentDialogueNarration** → **ABMUtteranceFilter** → **ABMUtteranceJsonlWriter**

## Flow Configuration

### ABMDataConfig Settings

- **Book Name**: `mvs` (uses sample data)
- **Validate Paths**: `true` (ensures data exists)
- **Custom Data Root**: leave empty (uses environment variable)

### ABMChapterVolumeLoader Settings

- **Chapters File**: Auto-populated from ABMDataConfig
- **Load Full Content**: `true` (includes complete chapter text)
- **Max Chapters**: `3` (limits to first 3 chapters for demo)

### ABMChapterSelector Settings

- **Selection Mode**: `range`
- **Chapter Range**: `1-3` (processes chapters 1-3)

### ABMSegmentDialogueNarration Settings

- **Min Segment Length**: `100` characters
- **Dialogue Markers**: `"\"\"''"` (quotation marks)

### ABMUtteranceFilter Settings

- **Min Length**: `50` characters
- **Max Length**: `5000` characters
- **Filter Empty**: `true`
- **Preserve Dialogue**: `true`

### ABMUtteranceJsonlWriter Settings

- **Output File**: Set to desired output path (e.g., `/home/jon/repos/audio-book-maker-lg/data/annotations/mvs/mvp_output.jsonl`)
- **Include Metadata**: `true`

## Running the Flow

1. **Configure Output**: Set the output file path in the ABMUtteranceJsonlWriter component
2. **Run Flow**: Click the "Run" button or execute individual components
3. **Monitor Progress**: Watch the component status indicators
4. **Check Results**: Verify the output JSONL file is created with processed utterances

## Expected Results

The flow will process the first 3 chapters of the MVS sample data and produce:

- Dialogue and narration segments
- Filtered utterances meeting quality criteria  
- JSONL output ready for audio generation pipeline

## Troubleshooting

- **Component Not Found**: Ensure LangFlow started with correct `LANGFLOW_COMPONENTS_PATH`
- **Data Path Errors**: Verify `.env` file has correct `ABM_DATA_ROOT`, `ABM_BOOKS_DIR`, `ABM_CLEAN_DIR`
- **No Output**: Check output file permissions and directory exists
- **Component Errors**: Check component logs in LangFlow UI for detailed error messages

## Next Steps

After successful MVP flow execution:

1. Experiment with different chapter ranges
2. Adjust filtering parameters
3. Test with other book data
4. Integrate with audio generation components (future development)
