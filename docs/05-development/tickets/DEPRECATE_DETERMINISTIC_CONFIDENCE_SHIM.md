# Ticket: Deprecate legacy deterministic_confidence import path

Status: Open
Owner: Upstream Attribution
Created: 2025-09-02

## Context

A compatibility shim was added at `src/abm/lf_components/audiobook/deterministic_confidence.py` to re-export `DeterministicConfidenceScorer` and `DeterministicConfidenceConfig` from `abm.helpers.deterministic_confidence`. This unblocks tests and downstream code still importing the legacy path.

We should migrate all imports to the new canonical module (`abm.helpers.deterministic_confidence`) and remove the shim after a short deprecation period.

## Tasks

- [ ] Code migration: Replace imports of `abm.lf_components.audiobook.deterministic_confidence` with `abm.helpers.deterministic_confidence` across repo (src, tests, scripts, docs).
- [ ] Deprecation notice: Add a `warnings.warn` in the shim on import (Pending until migration PR lands, then keep warning for one release cycle).
- [ ] Docs update: Update any references in docs and READMEs to point to `abm.helpers.deterministic_confidence`.
- [ ] Lint/guardrail: Add a check (ruff rule or simple CI grep) preventing new uses of the legacy path.
- [ ] Removal: Delete the shim after deprecation window; ensure tests pass.

## Acceptance Criteria

- All internal imports use `abm.helpers.deterministic_confidence`.
- Shim emits a deprecation warning (for one release cycle), then is removed.
- CI guard prevents regressions to the legacy path.
- Docs reflect the new path.

## Notes

- Coordinate with any external consumers (flows/components) if applicable.
- The canonical implementation resides in `src/abm/helpers/deterministic_confidence.py`.
