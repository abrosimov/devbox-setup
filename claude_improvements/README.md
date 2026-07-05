# Moved

The Κάτοπτρον knowledge base (behavioural-failure catalogue, root causes,
consolidation plan, FPF seminar, evals build plan) has moved to the
`llm-tools-configuration` repository:

https://github.com/abrosimov/llm-tools-configuration/tree/master/claude_improvements

Also moved there (`future_projects/`): `spec-workflow-redesign-proposal.{md,pdf}`,
`work-bureaucrat-agent.md`, `git-push-policy.md`.

Rationale: docs live where the work they govern happens — the eval stack,
the harness, and (after the planned config migration) the templates are all
in that repo. This repo keeps machine provisioning (Ansible, packages,
dotfiles) and, for now, the Claude Code configuration itself
(`roles/devbox/files/dot_claude/`).

Full git history of the moved files remains in this repository's history
(removed 2026-07-05).
