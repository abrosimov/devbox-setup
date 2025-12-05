---
description: Review changes using code reviewer agent
---

You are orchestrating the review phase of a development workflow.

## Steps

### 1. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

### 2. Gather Context

```bash
# Get branch and potential Jira ticket
git branch --show-current

# Get changes for review
git diff main...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/<branch>.md` (see CLAUDE.md for configured path)

### 3. Run Appropriate Agent

Based on detected language:
- **Go**: Use `code-reviewer-go` agent
- **Python**: Use `code-reviewer-python` agent

The agent will:
- Analyze code against requirements
- Check for issues (errors, tests, patterns)
- Provide structured feedback with severity levels

### 4. After Completion

Present the structured feedback:
- 🔴 Must Fix (Blocking)
- 🟡 Should Fix (Important)
- 🟢 Consider (Optional)

If blocking issues:
> Say **'fix'** to have SE address issues, or provide specific instructions.

If no blocking issues:
> Say **'commit'** to proceed, or **'done'** to finish.
