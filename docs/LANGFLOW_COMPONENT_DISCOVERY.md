# LangFlow Component Discovery Fix

## Problem

Custom LangFlow components were not appearing in the UI despite being correctly structured and importable.

## Root Cause

The `LANGFLOW_COMPONENTS_PATH` environment variable was not properly exported during LangFlow startup. The launch script was only passing the path via command-line argument (`--components-path`), but LangFlow's auto-discovery mechanism requires the environment variable to be set.

## Solution

1. **Directory Structure** (already correct):

   ```
   /src/abm/lf_components/
   ├── __init__.py
   └── audiobook/
       ├── __init__.py
       ├── abm_chapter_selector.py
       ├── abm_chapter_volume_loader.py
       ├── abm_segment_dialogue_narration.py
       ├── abm_utterance_filter.py
       ├── abm_utterance_jsonl_writer.py
       └── test_component.py
   ```

2. **Environment Variable Export**:
   - Export `LANGFLOW_COMPONENTS_PATH` before launching LangFlow
   - Pass both environment variable AND command-line argument for maximum compatibility

3. **Updated Launch Script**:

   ```bash
   # Export the components path as environment variable for LangFlow
   export LANGFLOW_COMPONENTS_PATH="$COMPONENTS_PATH"
   
   # Launch with both env var and CLI arg
   exec env LANGFLOW_COMPONENTS_PATH="$LANGFLOW_COMPONENTS_PATH" \
     langflow run --host "$HOST" --port "$PORT" \
     --components-path "$COMPONENTS_PATH"
   ```

## Key Requirements for LangFlow Component Discovery

1. ✅ **Directory Structure**: Components must be in category folders (`/components_path/category_name/*.py`)
2. ✅ **Inheritance**: All components must inherit from `langflow.custom.Component`
3. ✅ **Environment Variable**: `LANGFLOW_COMPONENTS_PATH` must be exported
4. ✅ **Python Path**: Components directory must be in Python path
5. ✅ **Package Structure**: Proper `__init__.py` files for Python imports

## Verification

After the fix, LangFlow startup shows:

```
- LANGFLOW_COMPONENTS_PATH: /home/jon/repos/audio-book-maker-lg/src/abm/lf_components
```

And the "Audiobook" category appears in the LangFlow UI with all 6 components visible.

## Components Now Available in UI

1. **ABM Chapter Selector** - Selects chapters from volumes
2. **ABM Chapter Volume Loader** - Loads volume data for processing  
3. **ABM Segment Dialogue Narration** - Segments dialogue and narration
4. **ABM Utterance Filter** - Filters utterances by criteria
5. **ABM Utterance JSONL Writer** - Writes utterances to JSONL format
6. **Test Component** - Minimal test component for validation
