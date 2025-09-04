# GitHub Projects Policy

Keep ceremony minimal. Use only GitHub-native features (Issues, PRs, Labels, Milestones, Projects v2). No artifacts or secrets in git.

## Kanban board (5 columns)

- Backlog: idea pool; rough and unsized; default landing for new issues.
- Ready: scoped tickets with acceptance criteria; unblocked and actionable.
- In progress: actively worked items; WIP limit: 3.
- In review: PRs open or awaiting review/merge; WIP limit: 5.
- Done: merged and accepted; close the issue.

Default board: <https://github.com/users/jwardwell7077/projects/3>

## Labels

- Type: `type:feature`, `type:bug`, `type:infra`, `type:doc`
- Priority: `prio:high`, `prio:med`, `prio:low`
- Flow: `agent-task`, `blocked`
- Scope (parallelization): `scope:ingestion`, `scope:langflow`, `scope:tests`, `scope:docs`, `scope:infra`

Guidance:

- Each issue gets exactly one Type, one Priority, and one Scope label (plus `agent-task` where relevant).
- Use `blocked` when waiting on dependency; add a short note on the blocker.

## Milestones (phase gates)

- `v0.1 KISS` (current)
- `v0.2 Casting & SSML`
- `v0.3 TTS + E2E Demo`

Tie each PR/issue to a milestone. Keep PRs < 300 LOC when possible and green on CI.

## Ticket quality bar (for Ready)

- Clear Goal and Scope.
- Acceptance Criteria (observable/testable).
- References (docs, code, examples).
- If agent-executable, add `agent-task` and simple step checklist.

## WIP and automation

- Auto-add newly opened issues to Backlog.
- When `agent-task` is added and the ticket is fully scoped, move to Ready.
- Warn if >3 items in In progress or >5 in In review; avoid starting new work until within limits.

## PR policy

- Link the issue ("Fixes #ID").
- Sections: What changed, How verified, Risks & rollout, Screenshots/logs if relevant.
- Must pass CI (pre-commit + pytest) across Python 3.11/3.12.

## Parallelization via scopes

Use scopes to run work in parallel without collisions:

- `scope:ingestion`: CLI, meta sidecars, converters.
- `scope:langflow`: custom components and example flows.
- `scope:tests`: unit/integration tests and fixtures.
- `scope:docs`: docs, diagrams, policies.
- `scope:infra`: CI, automation, linting, dependencies.
