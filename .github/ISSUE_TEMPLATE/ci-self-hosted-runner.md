---
name: Investigate self-hosted runner
about: Explore enabling a secure self-hosted runner to reduce Actions cost
title: "Investigate self-hosted runner"
labels: ci, cost-optimization
assignees: ''
---

Context
- Actions minutes today were high. We paused self-hosted due to security concerns.

Goals
- Evaluate security model (least-privilege user, firewall, repo access)
- Decide scope (which workflows, labels, concurrency)
- Draft hardening checklist (auto-updates, isolation, secrets)

Deliverables
- Proposal PR with runner label plan and opt-in toggle
- Runbook to rotate tokens and patch the host

Risks
- Privilege escalation from untrusted PRs (mitigate with `pull_request_target` avoidance and labels)
- Secrets exposure on self-hosted (mitigate via restricted repo access and no org-wide secrets)
