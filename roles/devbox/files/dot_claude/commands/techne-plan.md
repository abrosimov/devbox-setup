---
description: Create implementation plan from spec or requirements
---

You are orchestrating the planning phase of a development workflow.

## Steps

### 1. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py)
RC=$?
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

Store these values — pass to agent, do not re-compute.
Project directory: `{PROJECT_DIR}` (from resolve-context JSON)

### 2. Detect Project Stack

There is a **single, stack-agnostic** planner: `implementation-planner`. It detects the stack itself, but you still detect it here to pass as context (and to label the run).

Check for project markers (check ALL — a project may have multiple):
- If `go.mod` exists → **Go backend**
- If `pyproject.toml` or `requirements.txt` exists → **Python backend**
- If `package.json` or `tsconfig.json` or `next.config.*` exists → **Frontend (TypeScript/React/Next.js)**

**Stack classification:**

| Markers Found | Classification | Stack to pass to planner |
|---------------|---------------|--------------------------|
| Go only | `backend` | `Go` |
| Python only | `backend` | `Python` (or `Python (Flask monolith)`) |
| Frontend only | `frontend` | `Frontend` |
| Backend + Frontend | `fullstack` | `Fullstack` — planner creates work streams for both |
| Unclear | — | Ask user |

For Python projects, also check if it's a Flask-OpenAPI3 monolith:
- If `app/application/__init__.py` exists with layer initialization → pass `Stack: Python (Flask monolith)` and note its layered-DI / repository constraints
- Otherwise → pass `Stack: Python`

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

### 4. Run the Planner

Always use the single `implementation-planner` agent. Pass the detected stack/architecture as context — the agent tailors language-conditional guidance (security patterns, downstream SE agent, manifest) itself.

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly. The Task tool inherits the parent's model by default — without an explicit `model` parameter, the agent runs on the parent's model, ignoring the agent frontmatter.

```
Task(
  subagent_type: "implementation-planner",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\nStack: {Go|Python|Python (Flask monolith)|Frontend|Fullstack}\nFrontend stack: {Next.js|Vite|etc.}\n\n{task description}"
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
