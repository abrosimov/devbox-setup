---
description: Write tests for recent changes using unit test writer agent
---

You are orchestrating the testing phase of a development workflow.

## CRITICAL: Always Use Agents for Tests

**DO NOT write tests directly.** This command exists to ensure all test code goes through specialized agents that enforce:
- Bug-hunting mindset and comprehensive coverage
- Proper mocking of external dependencies
- Language-specific test patterns (parametrized tests, table-driven tests)

**If you find yourself about to write tests without invoking an agent, STOP and use this command instead.**

## Parse Arguments

Check if user passed a model argument:
- `/test opus` or `/test --model opus` → use **opus**
- `/test sonnet` or `/test --model sonnet` → use **sonnet**
- `/test` (no argument) → determine model via complexity check

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

### 3. Identify What Needs Testing

Check recent changes:
```bash
git diff --name-only HEAD~1
```

Or if there's an implementation summary from SE, use that for context.

### 4. Pre-flight Complexity Check (if no model specified)

**Skip this step if user explicitly specified a model.**

Run complexity assessment:

**For Go projects:**
```bash
# Count public functions needing tests
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -c "^func [A-Z]" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Count error handling sites (complexity indicator)
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -c "if err != nil\|return.*err" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Check for concurrency patterns
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -l "go func\|chan \|sync\." 2>/dev/null | wc -l
```

**For Python projects:**
```bash
# Count public functions needing tests
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -c "^def [^_]\|^async def [^_]" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Count exception handling sites
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -c "except\|raise\|try:" 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'

# Check for async patterns
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -l "async def\|await\|asyncio" 2>/dev/null | wc -l
```

**Escalation thresholds:**

| Metric | Threshold | Model |
|--------|-----------|-------|
| Public functions | > 15 | opus |
| Error/exception handling sites | > 20 | opus |
| Concurrency/async code | Any | opus |
| Otherwise | - | sonnet |

**If ANY threshold exceeded**, use **opus**. Otherwise use **sonnet**.

### 5. Run Appropriate Agent

Based on detected language:
- **Go**: Use `unit-test-writer-go` agent
- **Python**: Use `unit-test-writer-python` agent

**IMPORTANT**: When invoking the Task tool, include the `model` parameter:
- If user specified model → use that model
- If complexity check determined model → use that model

Example Task invocation:
```
Task(
  subagent_type: "unit-test-writer-go",
  model: "{determined_model}",  // "sonnet" or "opus"
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}\n\n{task description}"
)
```

The agent will:
- Analyze the implementation
- Write comprehensive tests
- Provide summary and suggest next step

### 6. After Completion

Present the agent's summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections.
