# Chat seeding — Quick Start

Goal: prime an assistant with a minimal, consistent snapshot of the repo to improve accuracy and reduce drift.

Method A: Link-based bootstrap (NOT READY)
- Status: Not fully supported yet. Some assistants don’t follow multi-file JSON indices reliably.
- TODO: sanitize links and implement CI generation.
 - Example links (replace <YOUR_GH_USER>):
	 - Index: https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest/index.json
	 - Full zip: https://raw.githubusercontent.com/<YOUR_GH_USER>/agent-audiobook-maker/main/seed_pack/latest.zip

Method B: Upload bundle (Preferred)
1) Generate a local snapshot bundle (e.g., via scripts/generate_seed_pack.py).
2) Upload your locally generated zip into each assistant window.
3) Prompt: “Extract the archive, open index.json, and load referenced modules/files. Use this seed to answer project questions with citations.”

Bundle locations
- Local: seed_pack/latest.zip and seed_pack/chat_min.zip in this repo after running the generator
- Remote (fallback): use the raw GitHub URLs above
