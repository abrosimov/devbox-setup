---
description: Review changes using code reviewer agent
---

You are orchestrating the review phase of a development workflow.

## Parse Arguments

Check if user passed a model argument:
- `/techne-review opus` or `/techne-review --model opus` → use **opus**
- `/techne-review sonnet` or `/techne-review --model sonnet` → use **sonnet**
- `/techne-review` (no argument) → use **opus** (default)

## Steps

### 1. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py)
RC=$?
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

**If exit 0** — parse JSON fields: `PROFILE`, `VAULT`, `BRANCH`, `JIRA_ISSUE` (null when the
branch carries none), `BRANCH_NAME`. Artefacts are notes in `VAULT` (see `config` skill).
**If exit 1** — stderr names what is missing (the profile variable, `.vault-root`, or the vault
directory it names). Relay that line and stop; do not guess a location.

Store these values — pass to agent, do not re-compute.

### 2. Gather Review Context

```bash
git diff $DEFAULT_BRANCH...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill).

Language detection is the agent's responsibility — `code-reviewer` runs `git diff --name-only` in its Step 1, classifies files by extension, and loads only the relevant `{lang}-engineer`/`{lang}-testing` skills. Polyglot diffs (e.g. Go backend + frontend) are reviewed stack-by-stack within a single invocation.

### 3. Run code-reviewer Agent

The unified `code-reviewer` agent handles Go, Python and TypeScript/React/Next.js. No language-specific routing required.

When invoking the Task tool, pass `model: "opus"` explicitly (or the user-specified model).

Example Task invocation:
```
Task(
  subagent_type: "code-reviewer",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\nUser's ask: {the user's request}\nDecisions already made: {decisions, or none}\nIn scope: {files/areas}\nOut of scope: {files/areas}"
)
```

If `JIRA_ISSUE` was resolved to `"none"` in Step 1, pass it through unchanged — the agent will skip Jira fetching and review the diff only.

The agent will:
- Analyze code against requirements
- Check for issues (errors, tests, patterns)
- Provide structured feedback with severity levels

### 5. After Completion

Present the structured feedback:
- Must Fix (Blocking)
- Should Fix (Important)
- Consider (Optional)

Must Fix is limited to defects in what was asked — correctness and the stated requirements — and to changes made outside the task's scope. Should Fix and Consider items are suggestions: they are reported to the user and are not routed to the engineer unless the user picks them (core §6).

If blocking issues:
> Say **'fix'** to have SE address the Must Fix items, or name the other items you also want addressed.

If no blocking issues, offer options:

> Review passed. Options:
>
> - **'pr'** — push and create pull request against `$DEFAULT_BRANCH`
> - **'done'** — finish without git operations
>
> Say your choice.

### 6. Push + PR (if requested)

When user says **'pr'**:

```bash
# Ensure all changes are committed first. If there are uncommitted changes,
# warn the user and ask them to commit before pushing. Do NOT auto-commit.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Uncommitted changes detected. Please commit them before pushing."
  exit 1
fi

# Push and create PR
git push -u origin $BRANCH
gh pr create --title "feat($JIRA_ISSUE): $BRANCH_NAME" --body "$(cat <<EOF
## Summary
[Review-verified changes]

## Test plan
- [ ] All tests pass
- [ ] Review feedback addressed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

If push/PR succeeds:
> PR created for `$BRANCH` against `$DEFAULT_BRANCH`.
>
> Cleanup: `proj wt rm $BRANCH` (if using worktrees)
