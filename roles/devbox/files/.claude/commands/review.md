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

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to agent, do not re-compute.

### 2. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

### 3. Pre-flight Complexity Check (if no model specified)

**Skip this step if user explicitly specified a model.**

Run complexity assessment:

**For Go projects:**
```bash
# Count changed lines (excluding tests)
git diff main...HEAD --stat -- '*.go' ':!*_test.go' | tail -1

# Count error handling sites
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -c "return.*err\|if err != nil" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Count changed files
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | wc -l

# Check for concurrency patterns
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -l "go func\|chan \|sync\.\|select {" 2>/dev/null | wc -l
```

**For Python projects:**
```bash
# Count changed lines (excluding tests)
git diff main...HEAD --stat -- '*.py' ':!test_*.py' ':!*_test.py' | tail -1

# Count exception handling sites
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -c "except\|raise\|try:" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Count changed files
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | wc -l

# Check for async patterns
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -l "async def\|await\|asyncio" 2>/dev/null | wc -l
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
git diff main...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see config.md)

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
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\n\n{task description}"
)
```

The agent will:
- Analyze code against requirements
- Check for issues (errors, tests, patterns)
- Provide structured feedback with severity levels

### 6. After Completion

Present the structured feedback:
- 🔴 Must Fix (Blocking)
- 🟡 Should Fix (Important)
- 🟢 Consider (Optional)

If blocking issues:
> Say **'fix'** to have SE address issues, or provide specific instructions.

If no blocking issues:
> Say **'commit'** to proceed, or **'done'** to finish.
