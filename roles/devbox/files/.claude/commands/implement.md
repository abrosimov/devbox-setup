---
description: Implement current task using software engineer agent
---

You are orchestrating the implementation phase of a development workflow.

## Steps

### 1. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

### 2. Check for Implementation Plan

```bash
git branch --show-current
```

Look for plan at `{PLANS_DIR}/<branch_name>.md` (see CLAUDE.md for configured path)

### 3. Run Appropriate Agent

Based on detected language:
- **Go**: Use `software-engineer-go` agent
- **Python**: Use `software-engineer-python` agent

The agent will:
- Read the implementation plan if it exists
- Implement the required changes
- Provide summary and suggest next step

### 4. After Completion

Present the agent's summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections.
