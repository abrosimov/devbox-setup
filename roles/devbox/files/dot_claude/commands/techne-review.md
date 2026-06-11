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

### 0. Read Workflow Config

```bash
cat .claude/workflow.json 2>/dev/null || echo '{}'
```

Parse the JSON. Extract flags (default to `true` if key is missing):

| Flag | Default | Effect |
|------|---------|--------|
| `auto_commit` | `true` | If `false`, skip auto-commit of review fixes |

### 1. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
RC=$?
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

Store these values — pass to agent, do not re-compute.

### 2. Gather Review Context

```bash
git diff $DEFAULT_BRANCH...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill).

Language detection is the agent's responsibility — `code-reviewer` runs `git diff --name-only` in its Step 1, classifies files by extension, and loads only the relevant `{lang}-engineer`/`{lang}-testing` skills. Polyglot diffs (e.g. Go backend + frontend) are reviewed stack-by-stack within a single invocation.

### 3. Run code-reviewer Agent

The unified `code-reviewer` agent handles Go, Python and TypeScript/React/Next.js. No language-specific routing required.

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly (or the user-specified model).

Example Task invocation:
```
Task(
  subagent_type: "code-reviewer",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\n{task description}"
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

If blocking issues:
> Say **'fix'** to have SE address issues, or provide specific instructions.

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
# Ensure all changes are committed first
if ! git diff --quiet || ! git diff --cached --quiet; then
  # If auto_commit is false, warn user about uncommitted changes
  # and ask them to commit before pushing. Do NOT auto-commit.
  # If auto_commit is true (default):
  .claude/bin/git-safe-commit -m "chore($JIRA_ISSUE): final changes after review"
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
