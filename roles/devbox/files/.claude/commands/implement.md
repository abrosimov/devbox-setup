---
description: Implement current task using software engineer agent
---

You are orchestrating the implementation phase of a development workflow.

## CRITICAL: Always Use Agents for Code

**DO NOT write code directly.** This command exists to ensure all code changes go through specialized agents that enforce:
- Language-specific standards and patterns
- Production necessities (error handling, logging, timeouts)
- Consistency with existing codebase

**If you find yourself about to write code without invoking an agent, STOP and use this command instead.**

## Parse Arguments

Check if user passed a model argument:
- `/implement opus` or `/implement --model opus` → use **opus**
- `/implement sonnet` or `/implement --model sonnet` → use **sonnet**
- `/implement` (no argument) → determine model via complexity check

## Steps

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`; JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
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
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | wc -l

# Check for concurrency patterns
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -l "go func\|chan \|sync\.\|select {" 2>/dev/null | wc -l
```

**For Python projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test_ | grep -v _test.py | wc -l

# Check for async patterns
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -l "async def\|await\|asyncio" 2>/dev/null | wc -l
```

**Escalation thresholds:**

| Metric | Threshold | Model |
|--------|-----------|-------|
| Plan lines | > 200 | opus |
| Changed files (non-test) | > 8 | opus |
| Concurrency/async code | Any | opus |
| Otherwise | - | sonnet |

**If ANY threshold exceeded**, use **opus**. Otherwise use **sonnet**.

### 4. Check for Implementation Plan

Look for plan at `{PLANS_DIR}/{JIRA_ISSUE}/plan.md` (see config.md for configured path)

### 5. Run Appropriate Agent

Based on detected language:
- **Go**: Use `software-engineer-go` agent
- **Python**: Use `software-engineer-python` agent

**IMPORTANT**: When invoking the Task tool, include the `model` parameter:
- If user specified model → use that model
- If complexity check determined model → use that model

Example Task invocation:
```
Task(
  subagent_type: "software-engineer-go",
  model: "{determined_model}",  // "sonnet" or "opus"
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}\n\n{task description}"
)
```

The agent will:
- Read the implementation plan if it exists
- Implement the required changes
- Provide summary and suggest next step

### 6. After Completion

Present the agent's summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections.
