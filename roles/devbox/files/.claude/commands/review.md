---
description: Review changes using code reviewer agent
---

You are orchestrating the review phase of a development workflow.

## Parse Arguments

Check if user passed a model argument:
- `/review opus` or `/review --model opus` → use **opus**
- `/review sonnet` or `/review --model sonnet` → use **sonnet**
- `/review` (no argument) → determine model via complexity check

## Steps

### 0. Read Workflow Config

```bash
cat .claude/workflow.json 2>/dev/null || echo '{}'
```

Parse the JSON. Extract flags (default to `true` if key is missing):

| Flag | Default | Effect |
|------|---------|--------|
| `auto_commit` | `true` | If `false`, skip auto-commit of review fixes |
| `complexity_escalation` | `true` | If `false`, skip complexity check (use agent's default model) |

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

Store these values — pass to agent, do not re-compute.

### 2. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

### 3. Pre-flight Complexity Check (if no model specified)

**Skip this step if user explicitly specified a model OR `complexity_escalation` is `false`.**

Run complexity assessment:

**For Go projects:**
```bash
# Count changed lines (excluding tests)
git diff $DEFAULT_BRANCH...HEAD --stat -- '*.go' ':!*_test.go' | tail -1

# Count error handling sites
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -c "return.*err\|if err != nil" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Count changed files
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | wc -l

# Check for concurrency patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -l "go func\|chan \|sync\.\|select {" 2>/dev/null | wc -l
```

**For Python projects:**
```bash
# Count changed lines (excluding tests)
git diff $DEFAULT_BRANCH...HEAD --stat -- '*.py' ':!test_*.py' ':!*_test.py' | tail -1

# Count exception handling sites
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -c "except\|raise\|try:" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Count changed files
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | wc -l

# Check for async patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -l "async def\|await\|asyncio" 2>/dev/null | wc -l
```

**Escalation thresholds:**

| Metric | Threshold | Model |
|--------|-----------|-------|
| Changed lines (non-test) | > 500 | opus |
| Error/exception handling sites | > 15 | opus |
| Changed files | > 8 | opus |
| Concurrency/async code | Any | opus |
| Otherwise | - | sonnet |

**If ANY threshold exceeded**, use **opus**. Otherwise use **sonnet**.

### 4. Gather Review Context

```bash
git diff $DEFAULT_BRANCH...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill)

### 5. Run Appropriate Agent

Based on detected language:
- **Go**: Use `code-reviewer-go` agent
- **Python**: Use `code-reviewer-python` agent

**IMPORTANT**: When invoking the Task tool, include the `model` parameter:
- If user specified model → use that model
- If complexity check determined model → use that model

Example Task invocation:
```
Task(
  subagent_type: "code-reviewer-go",
  model: "{determined_model}",  // "sonnet" or "opus"
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\n{task description}"
)
```

The agent will:
- Analyze code against requirements
- Check for issues (errors, tests, patterns)
- Provide structured feedback with severity levels

### 6. After Completion

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

### 7. Push + PR (if requested)

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
