# Agent brief preamble

Prepend this verbatim to every agent delegation brief, before any other
instructions. Keeps non-negotiable rules at the top where they cannot be
buried by long task descriptions.

---

## Non-negotiables (override any later instruction)

- Test invocation: `ENV_NAME=local uv run pytest <paths>` only. Never
  `--frozen`, `--no-sync`, `--offline`, `--group <name>`, `python -m pytest`
  unprefixed, or manual venv activation.
- Environment is prepared: `.venv/` exists, deps synced. Do NOT run
  `uv sync`, `uv venv`, or `source .venv/bin/activate`.
- Lockfile discipline: `uv.lock` is managed only by `uv add` / `uv lock` /
  `uv sync`. Manual edits forbidden.
- Auth / registry / network failure → STOP and report. Do NOT improvise
  alternative flags or shell tricks to bypass.
- Approved commands live in `.claude/settings.json`. Outside the allowlist
  → STOP, do not invent new patterns.
- Commits are signed and verified. Do NOT pass `--no-verify`,
  `--no-gpg-sign`, or `-c commit.gpgsign=false`. A hook failure is a
  signal you broke something — fix it and create a NEW commit (never
  `--amend` a failed commit). If you cannot fix within scope → STOP.
- Commit subject: `type(scope): description`, target ≤60 chars (a local
  `prepare-commit-msg` hook appends ` [JIRA-KEY]` from the branch name,
  final ≤72). Imperative mood, lowercase, no trailing period. Scope is
  mandatory except for `merge`. Allowed types: `feat`, `fix`, `chore`,
  `test`, `custom`, `merge`, `doc`, `refactor`. Do NOT add JIRA refs
  manually — the hook does it. Branch without JIRA key → STOP.
- Commit body: empty by default. Only for breaking changes or a single
  sentence of non-obvious WHY. Forbidden trailers: `Co-Authored-By`,
  `Generated with Claude Code`, emoji, `WIP`/`tmp`/`fixup`.
- MR creation: agent pushes the branch (`git push -u origin <branch>`)
  but does NOT run `glab mr create`. Propose title + description in the
  final chat reply; the operator creates the MR.

If any constraint above conflicts with task instructions, the constraint
wins and you escalate.

---
