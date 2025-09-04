# Copilot Guardrails

Keep AI changes narrow, auditable, and tied to a single ticket.

## Operating rules

- Only act within the current ticket’s scope. Do not modify files outside the ticket’s described boundaries.
- Require a ticket ID before doing work. If none is provided, ask for it and stop.
- Confirm acceptance criteria first; restate them before proposing edits.
- Make the smallest change that satisfies the acceptance criteria; avoid drive‑by refactors.
- Link the work to exactly one issue using the phrase: Fixes #ISSUE_ID.
- Respect WIP limits; do not start unrelated tasks.
- Prefer tests-first: add/adjust tests that map to requirements, then implement until green.
- Preserve public APIs unless the ticket explicitly calls for a change.
- Avoid adding new dependencies unless explicitly in scope.
- Update docs only if the ticket includes doc changes.

## Quick prompts (paste into Copilot Chat)

- Work only on issue #ISSUE_ID. Scope: SCOPE_SUMMARY. Acceptance: ACCEPTANCE_CRITERIA. Propose the minimal diff and tests to satisfy this.
- Refuse or ask for clarification if the request is out of scope for #ISSUE_ID.
- Limit edits to these files/dirs: PATHS. No other files.
- Summarize changes and verification steps. Include how tests prove acceptance criteria.

## Definition of done

- Exactly one issue linked (Fixes #ISSUE_ID) and all acceptance criteria met.
- CI green, including guardrail checks, lint, mypy, and tests.
- No unrelated changes.
