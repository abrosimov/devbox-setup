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

**If exit 0** — parse JSON fields: `PROFILE`, `VAULT`, `BRANCH`, `JIRA_ISSUE` (null when the
branch carries none), `BRANCH_NAME`. Artefacts are notes in `VAULT` (see `config` skill).
**If exit 1** — stderr names what is missing (the profile variable, `.vault-root`, or the vault
directory it names). Relay that line and stop; do not guess a location.
If `JIRA_ISSUE` is null and the user named an issue key in the conversation, use that key.

Store these values — pass to agent, do not re-compute.
Vault: `{VAULT}` (from resolve-context JSON)

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
| Unclear | — | Nothing — the planner detects the stack itself; report this under "Decisions I made" (no AskUserQuestion) |

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
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\nStack: {Go|Python|Python (Flask monolith)|Frontend|Fullstack}\nFrontend stack: {Next.js|Vite|etc.}\n\nUser's ask: {the user's request}\nDecisions already made: {decisions, or none}\nIn scope: {files/areas}\nOut of scope: {files/areas}"
)
```

**Include in agent prompt**:
```
Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}
Stack: {backend|frontend|fullstack}
Frontend stack: {Next.js|Vite|etc.} (if frontend markers detected)
User decisions: {every decision, answer, analogy, and stated principle from this conversation, in the user's words}
```

The planner cannot see the conversation, so the decisions it would otherwise turn into questions must travel in the brief.

The agent will:
- Read the spec if it exists
- Explore the codebase for patterns
- Create detailed implementation plan with work streams and agent assignments
- Suggest next step based on work stream dependencies

### 5. After Completion

Present the plan summary and suggested next step to the user. Before relaying the planner's "Blockers for the user", resolve each one you can from the conversation (core §6); relay only the residue that passes the stop list, each with its recommended answer, and list the planner's key decisions under "Decisions I made".
End on the recommended next command; the user runs it or replies with corrections to the plan.
