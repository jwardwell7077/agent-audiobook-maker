# Chat Seeding — Quick Start

## Stable Manifest (always latest on main)
- Manifest:
  `https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest/index.json`

- Zips (generated on every main commit):
  **MIN**: `https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/chat_min.zip`
  **FULL**: `https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest.zip`

> Replace `<YOUR_GH_USER>` with the correct user/org.

---

## Copy–Paste (MIN)
> Use this when context is tight.

1) Load this manifest and initialize with the `chat_min` list:


https://raw.githubusercontent.com/
<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest/index.json

2) Use:
- `pipelines.json` for ready-to-run commands (plan/render ch_0001 with Parler)
- `voices.json` for casting (Parler catalog + mapping)
- `schemas_index.json` for plan/QC/profile schemas

---

## Copy–Paste (MAX)
> Use this when you want full repo context.

1) Download and expand:


https://raw.githubusercontent.com/
<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest.zip

2) Start with `index.json` then follow:
- `modules/*.json` for package summaries
- `files/*.json` for per-file API surfaces
- `graphs/*` for imports/calls
- `voices.json`, `pipelines.json` for Parler presets

---

## Load into multiple ChatGPT windows

Method A: Link-based bootstrap (NOT READY)

- Status: Not fully supported yet. Some assistants don’t follow multi-file JSON indices reliably.
- TODO: sanatize and implimented automated CIs

Method B: Upload zip (Preferred)

1) Generate the seed pack locally (script: scripts/generate_seed_pack.py).
2) Upload seed_pack/latest.zip (or seed_pack/chat_min.zip) into each ChatGPT window.
3) Prompt: “Extract the archive, open index.json, and load referenced modules/files. Use this seed to answer project questions with citations.”
