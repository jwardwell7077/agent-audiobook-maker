# Seed pack overview (context only)

Purpose
- Provide a code-grounded snapshot for documentation and quick orientation: modules, CLI entry points, env vars, configs, and basic graphs.
- Keep docs accurate by linking to machine-generated sources rather than duplicating details.

What it contains
- A generated snapshot of:
	- CLI entry points grouped by module
	- Environment variables and common config artifacts
	- Lightweight import graph for orientation
	- Module summaries (key classes, surfaces, and dependencies)
	- Minimal JSON schemas for core artifacts

How it’s generated
- Run scripts/generate_seed_pack.py to rebuild a fresh snapshot locally.

Versioning
- Treat generated snapshots as ephemeral developer aids. This documentation is self-contained and does not rely on them.
