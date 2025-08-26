# LangFlow Prototype Pipeline

This project uses LangFlow to rapidly prototype the annotation pipeline before migrating to CrewAI and LangGraph. This page documents the current working setup so contributors can run and iterate quickly.

## What’s included

- Custom components (discovery via `LANGFLOW_COMPONENTS_PATH`):
  - `components/helpers/master_example.py` (demo component)
  - `lf_components/` (category: Audiobook) – add new components here
- Helper to call a LangFlow REST flow: `tools/run_flow.py`
- Sample flow to import: `tools/sample_master_example.flow.json`

## Run LangFlow with ABM components

Preferred: use the helper script which wires env vars and PYTHONPATH.

- `scripts/run_langflow.sh` – launches LangFlow and exposes custom components

If you launch manually, set component discovery explicitly (example):

- `LANGFLOW_COMPONENTS_PATH="$(pwd)/lf_components:$(pwd)/components"`  
- Ensure your venv is active and `langflow` is installed in it

Then start LangFlow and import the sample flow from the UI.

## Component contract (I/O)

- All component outputs are plain Python types (dict/list/str/float/bool) or LangFlow `Message`/`Data` wrappers so they interoperate with CrewAI/LangGraph later.
- Current utterance JSONL schema (minimal):
  - `book_id` (str), `chapter_id` (str), `utterance_idx` (int), `text` (str), `is_dialogue` (bool)

Future expansions will version the schema to add: `speaker`, `emotion`, `prosody`, `ssml`, `tts_refs`.

## Testing a flow via REST

- Export the flow, note its `flow_id` (from the LangFlow UI)  
- Call it with `tools/run_flow.py` (uses `LANGFLOW_URL`, `LANGFLOW_FLOW_ID`)

This returns status + JSON body so you can script quick checks.

## Next steps (migration path)

- Add `ABM Chapter Volume Loader`, `Segment Dialogue/Narration`, and `Utterance JSONL Writer` under `lf_components/audiobook/`
- Keep inputs/outputs as simple Python payloads
- Snapshot minimal utterance schema as v0.1; add `speaker` in v0.2

If components aren’t visible:

- Verify `LANGFLOW_COMPONENTS_PATH` includes both `lf_components` and `components`  
- Restart LangFlow after editing components
