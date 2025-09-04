---
name: Backlog seed (meta)
about: Suggested backlog items to create
title: ""
labels: ["type:doc"]
assignees: ""
---

Create these issues and assign milestone/labels:

1) Docs: Remove two-agent from README and site-wide (this PR)
   - Acceptance: root README updated; legacy docs moved to docs/_deprecated; link check passes

2) Docs: KISS quickstart + LangFlow how-to refresh
   - Acceptance: KISS.md and LANGFLOW_COMPONENT_DISCOVERY.md reflect Python 3.11, components path, sample flow import

3) CI: add workflow + smoke test for ABM components
   - Acceptance: CI runs on 3.11/3.12; tests include component import smoke

4) Makefile: dev_setup / test_quick / langflow targets
   - Acceptance: targets exist; run in CI or locally documented

5) Casting design note stub (future milestone), no code
   - Acceptance: stub doc under docs/02-specifications/components/ casting note
