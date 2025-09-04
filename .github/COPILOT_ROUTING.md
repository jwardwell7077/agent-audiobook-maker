# Copilot Routing Hints

When the user asks about or performs any of the following topics, include the gh CLI workflows guide in context:

- Project management (Projects, statuses, moving items)
- Commits/branch naming/commit message rules
- Tickets/issues (create, label, comment, close)
- Pull requests (create, merge, auto-merge)

Primary doc:

- docs/05-development/guides/GH_CLI_WORKFLOWS.md

Notes:

- The official guide links to gh manual pages for details.
- Projects actions require token scope `project`; prompt to run `gh auth refresh -s project` if needed.
