---
description: Review changes using code reviewer agent
---

You are orchestrating the review phase of a development workflow.

## Parse Arguments

Check if user passed a model argument:
- `/review opus` or `/review --model opus` → use **opus**
- `/review sonnet` or `/review --model sonnet` → use **sonnet**
- `/review` (no argument) → use **opus** (default)

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

### 2. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

### 3. Gather Review Context

```bash
git diff $DEFAULT_BRANCH...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill)

### 4. Run Appropriate Agent

Based on detected language:
- **Go**: Use `code-reviewer-go` agent
- **Python**: Use `code-reviewer-python` agent

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly (or the user-specified model).

Example Task invocation:
```
Task(
  subagent_type: "code-reviewer-go",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\n{task description}"
)
```

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
> Cleanup: `claude-wt rm $BRANCH` (if using worktrees)
