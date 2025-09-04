# LangFlow Component Discovery Fix

## Problem

Custom LangFlow components were not appearing in the UI despite being correctly structured and importable.

## Root Cause

The `LANGFLOW_COMPONENTS_PATH` environment variable was not properly exported during LangFlow startup. The launch script was only passing the path via command-line argument (`--components-path`), but LangFlow's auto-discovery mechanism requires the environment variable to be set.

## Solution

1. **Directory Structure** (example):

   ```
   /src/abm/lf_components/
   ├── __init__.py
   └── audiobook/
      ├── __init__.py
      ├── abm_chapter_loader.py
      ├── abm_block_schema_validator.py
      ├── abm_mixed_block_resolver.py
      ├── abm_span_classifier.py
      ├── abm_span_iterator.py
      ├── abm_span_attribution.py
      └── abm_artifact_orchestrator.py
   ```

1. **Environment Variable Export**:

   - Export `LANGFLOW_COMPONENTS_PATH` before launching LangFlow
   - Pass both environment variable AND command-line argument for maximum compatibility

1. **Updated Launch Script**:

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
1. ✅ **Inheritance**: All components must inherit from `langflow.custom.Component`
1. ✅ **Environment Variable**: `LANGFLOW_COMPONENTS_PATH` must be exported
1. ✅ **Python Path**: Components directory must be in Python path
1. ✅ **Package Structure**: Proper `__init__.py` files for Python imports

## Verification

After the fix, LangFlow startup shows:

````text
- LANGFLOW_COMPONENTS_PATH: /home/jon/repos/audio-book-maker-lg/src/abm/lf_components
```text

And the "Audiobook" category appears in the LangFlow UI with the ABM components visible.

## Components Now Available in UI (examples)

- ABMChapterLoader
- ABMBlockSchemaValidator
- ABMMixedBlockResolver
- ABMSpanClassifier
- ABMSpanIterator
- ABMArtifactOrchestrator
````
