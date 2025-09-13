---
name: Backlog seed (meta)
about: Suggested backlog items to create
title: ''
labels: [type:doc]
assignees: ''
---

Create these issues and assign milestone/labels:

1. Docs: Remove two-agent from README and site-wide (this PR)

   - Acceptance: root README updated; legacy docs moved to docs/\_deprecated; link check passes

1. Docs: KISS quickstart refresh (remove LangFlow)

   - Acceptance: KISS.md reflects Python 3.11; no LangFlow references remain

1. CI: add workflow + smoke test for ABM components

   - Acceptance: CI runs on 3.11/3.12; tests include component import smoke

1. Makefile: dev_setup / test_quick targets (remove deprecated LangFlow targets)

   - Acceptance: LangFlow targets removed; CI/local docs updated

1. Casting design note stub (future milestone), no code

   - Acceptance: stub doc under docs/02-specifications/components/ casting note
