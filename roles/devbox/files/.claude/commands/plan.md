---
description: Create implementation plan from spec or requirements
---

You are orchestrating the planning phase of a development workflow.

## Steps

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to agent, do not re-compute.
Project directory: `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/` (see config.md)

### 2. Detect Project Language

Check for project markers:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user which language to use

For Python projects, also check if it's a Flask-OpenAPI3 monolith:
- If `app/application/__init__.py` exists with layer initialization → Use `implementation-planner-python-monolith`
- Otherwise → Use `implementation-planner-python`

### 3. Check for Existing Spec

Look for specification documents in `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`:
- `spec.md` - Main product specification
- `research.md` - Research findings
- `decisions.md` - Decision log

If spec exists, the planner will use it as primary input.
If no spec exists, the planner will work from user requirements directly.

The plan will be created at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md`

### 4. Run Appropriate Agent

Based on detected language/architecture:
- **Go**: Use `implementation-planner-go` agent
- **Python (standard)**: Use `implementation-planner-python` agent
- **Python (Flask monolith)**: Use `implementation-planner-python-monolith` agent

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`

The agent will:
- Read the spec if it exists
- Explore the codebase for patterns
- Create detailed implementation plan with test plan
- Suggest next step

### 5. After Completion

Present the plan summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections to the plan.
