# gh CLI workflows: Issues, PRs, Projects (routable Copilot context)

Purpose

- One place for our standard terminal flows using `gh` in this repo.
- Optimized for our guardrails: single linked issue per PR, branch naming, and Projects usage.

Pre-reqs

- gh installed and authed: `gh auth status`; if needed `gh auth login`.
- Ensure repo remote is set (origin) and you’re on a feature branch per naming rules.
- Token scopes for Projects: run `gh auth refresh -s project` if you need to add items or edit fields in Projects.

Branch and commit guardrails

- Branch format: \<type>/#\<issue>-\<kebab-desc> e.g., `fix/#18-ingest-tests`
- Exactly one linked issue per PR via "Fixes #\<n>" in the PR description (and preferably in the commit subject for traceability).

Issues

- List: `gh issue list --limit 50 --json number,title,labels --jq '.[] | {number,title,labels: ([.labels[].name] // [])}'`
- Create: `gh issue create --title "Title" --body "Body" --label type:bug --label prio:high`
- Comment: `gh issue comment \<n> --body "update"`
- Close: `gh issue close \<n>`

PRs

- Create: `gh pr create --base main --head \<branch> --title "Title" --body "Fixes #\<n> ..."`
- Status: `gh pr view --json number,state,mergeable,mergeStateStatus,statusCheckRollup --jq '.'`
- Auto-merge: `gh pr merge \<n> --squash --auto`
- Admin override (use sparingly): `gh pr merge \<n> --squash --admin`
- After merge: `git checkout main && git pull && git branch -d \<branch>`

Projects (user project)

- Add item to project (requires project scope): `gh project item-add \<project-number> --owner "@me" --url https://github.com/\<owner>/\<repo>/issues/\<n>`
- Move item (set Status field):
  1) Get project ID and fields (GraphQL or `gh project view --format json`)
  2) Get item ID (`gh project item-list <number> --owner "@me" --format json | jq ...`)
  3) Edit field: `gh project item-edit --id \<item-id> --project-id \<proj-id> --field-id \<status-field-id> --single-select-option-id \<option-id>`
- Tip: You may need to first run: `gh auth refresh -s project`

Common errors and fixes

- "Your token has not been granted the required scopes ... 'read:project'": run `gh auth refresh -s project` (or login with a PAT with project scope).
- "unknown command 'project'": ensure you’re using core `gh project` commands (extension is deprecated). Use `gh project ...`, not `gh projects ...`.
- PR merge shows MERGEABLE but won’t merge: use `gh pr view` to confirm status checks; enable `--auto` or, if policy allows, `--admin`.
- Branch name check failing: rename branch to conform or adjust temporary allowance (see `.github/workflows/branch-and-pr-guardrails.yml`).

Quick recipes

- Link an issue and open a PR from current branch:
  `gh pr create --base main --title "Short title" --body "Fixes #\<n>\nDetails ..."`
- Auto-merge when checks pass and delete the branch:
  `gh pr merge \<n> --squash --delete-branch --auto`
- Add issue #18 to Project 3 and set Status to In Progress:
  `gh auth refresh -s project`
  `gh project item-add 3 --owner "@me" --url https://github.com/\<owner>/\<repo>/issues/18`
  Then use `gh project item-list` / `gh project item-edit` to update Status (requires field IDs).

References

- gh manual: <https://cli.github.com/manual/>
- gh issue: <https://cli.github.com/manual/gh_issue>
- gh pr create: <https://cli.github.com/manual/gh_pr_create>
- gh pr merge: <https://cli.github.com/manual/gh_pr_merge>
- gh api: <https://cli.github.com/manual/gh_api>
- gh project item-add: <https://cli.github.com/manual/gh_project_item-add>
- gh project item-edit: <https://cli.github.com/manual/gh_project_item-edit>
