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
Project directory: `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/` (see `config` skill)

### 2. Detect Project Stack

Check for project markers (check ALL — a project may have multiple):
- If `go.mod` exists → **Go backend**
- If `pyproject.toml` or `requirements.txt` exists → **Python backend**
- If `package.json` or `tsconfig.json` or `next.config.*` exists → **Frontend (TypeScript/React/Next.js)**

**Stack classification:**

| Markers Found | Classification | Planners to Run |
|---------------|---------------|-----------------|
| Go only | `backend` | `implementation-planner-go` |
| Python only | `backend` | `implementation-planner-python` (or `-monolith`) |
| Frontend only | `frontend` | `implementation-planner-go` or `-python` (use as generic planner with frontend awareness) |
| Backend + Frontend | `fullstack` | Backend planner (Go or Python) — planner is stack-aware and will create work streams for both |
| Unclear | — | Ask user |

For Python projects, also check if it's a Flask-OpenAPI3 monolith:
- If `app/application/__init__.py` exists with layer initialization → Use `implementation-planner-python-monolith`
- Otherwise → Use `implementation-planner-python`

**For fullstack projects**, tell the planner about the frontend stack so it can create appropriate work streams:
- Include in agent prompt: `Frontend stack detected: [Next.js/Vite/etc.] — create work streams for both backend and frontend agents.`

### 3. Check for Existing Spec

Look for specification documents in `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`:
- `spec.md` - Main product specification
- `research.md` - Research findings
- `decisions.md` - Decision log

If spec exists, the planner will use it as primary input.
If no spec exists, the planner will work from user requirements directly.

The plan will be created at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md`

### 4. Run Appropriate Agent

Based on detected stack/architecture:
- **Go (backend or fullstack)**: Use `implementation-planner-go` agent
- **Python (standard)**: Use `implementation-planner-python` agent
- **Python (Flask monolith)**: Use `implementation-planner-python-monolith` agent
- **Frontend-only** (no backend markers): Use `implementation-planner-go` or `-python` as generic planner — include frontend context

**IMPORTANT**: When invoking the Task tool, always pass the `model` parameter explicitly. The Task tool inherits the parent's model by default — without an explicit `model` parameter, the agent runs on the parent's model, ignoring the agent frontmatter.

```
Task(
  subagent_type: "implementation-planner-{go|python|python-monolith}",
  model: "sonnet",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\nStack: {backend|frontend|fullstack}\nFrontend stack: {Next.js|Vite|etc.}\n\n{task description}"
)
```

**Include in agent prompt**:
```
Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}
Stack: {backend|frontend|fullstack}
Frontend stack: {Next.js|Vite|etc.} (if frontend markers detected)
```

The agent will:
- Read the spec if it exists
- Explore the codebase for patterns
- Create detailed implementation plan with work streams and agent assignments
- Suggest next step based on work stream dependencies

### 5. After Completion

Present the plan summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections to the plan.
