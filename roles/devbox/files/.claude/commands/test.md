---
description: Write tests for recent changes using unit test writer agent
---

You are orchestrating the testing phase of a development workflow.

## Steps

### 1. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

### 2. Identify What Needs Testing

Check recent changes:
```bash
git diff --name-only HEAD~1
```

Or if there's an implementation summary from SE, use that for context.

### 3. Run Appropriate Agent

Based on detected language:
- **Go**: Use `unit-test-writer-go` agent
- **Python**: Use `unit-test-writer-python` agent

The agent will:
- Analyze the implementation
- Write comprehensive tests
- Provide summary and suggest next step

### 4. After Completion

Present the agent's summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections.
