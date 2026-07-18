---
description: Implement current task using software engineer agent
---

You are orchestrating the implementation phase of a development workflow.

## CRITICAL: Verify User Approval Before Implementation

**Before spawning any implementation agent, verify ONE of these conditions:**

1. User explicitly invoked `/techne-implement` command (this counts as approval)
2. User said "yes", "go ahead", "proceed", "implement it" after seeing a proposal
3. User selected a specific option from alternatives presented

**If user only asked for analysis/proposal/options → DO NOT proceed. Present your analysis and wait.**

## CRITICAL: Always Use Agents for Code

**DO NOT write code directly.** This command exists to ensure all code changes go through specialized agents that enforce:
- Language-specific standards and patterns
- Production necessities (error handling, logging, timeouts)
- Consistency with existing codebase

**If you find yourself about to write code without invoking an agent, STOP and use this command instead.**

## Parse Arguments

Check if user passed a model argument:
- `/techne-implement opus` or `/techne-implement --model opus` → use **opus**
- `/techne-implement sonnet` or `/techne-implement --model sonnet` → use **sonnet** (cost-saving mode)
- `/techne-implement` (no argument) → default **opus**
- `/techne-implement fast` → use **sonnet**, skip all pre-flight checks

## Steps

### 1. Git Setup

Ensure you are on the correct branch before any work begins.

```bash
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
CURRENT=$(git branch --show-current)
```

**Branch logic:**

| Current Branch | Action |
|---------------|--------|
| `main` / `master` / `$DEFAULT_BRANCH` | Create feature branch from it |
| Feature branch (anything else) | Use it as-is |

**If creating a feature branch**, ask user for the branch name:

> What should I name the feature branch? Convention: `PROJ-123_short_description`

Then:
```bash
# Create and switch to feature branch
git checkout -b <branch-name> "$DEFAULT_BRANCH"
```

### 2. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py)
RC=$?
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

Store these values (including `DEFAULT_BRANCH` from Git Setup) — pass to agent, do not re-compute.

### 3. Detect Project Stack

Check for project markers (check ALL — a project may have multiple):
- If `go.mod` exists → **Go backend**
- If `pyproject.toml` or `requirements.txt` exists → **Python backend**
- If `package.json` or `tsconfig.json` or `next.config.*` exists → **Frontend (TypeScript/React/Next.js)**

**Stack classification:**

| Markers Found | Classification | Agent(s) |
|---------------|---------------|----------|
| Go only | `backend` | `software-engineer-go` |
| Python only | `backend` | `software-engineer-python` |
| Frontend only | `frontend` | `software-engineer-frontend` |
| Backend + Frontend | `fullstack` | See work stream routing below |
| Unclear | — | Ask user |

**Fullstack routing** — when both backend and frontend markers exist:
1. Check for `plan.md` at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md`
2. If `plan.md` defines work streams, route to the agent specified in each stream
3. If no work streams, ask user: "This is a fullstack project. Which part should I implement? (A) Backend, (B) Frontend, (C) Both sequentially"
4. When running both, run backend first (it may produce API types/contracts the frontend needs), then frontend

### 4. Determine Model

**Default model is opus.** Use sonnet only when the user explicitly requests it (`/techne-implement sonnet` or `/techne-implement fast`).

| User Input | Model | Notes |
|------------|-------|-------|
| `/techne-implement` | opus | Default — highest quality |
| `/techne-implement opus` | opus | Explicit |
| `/techne-implement sonnet` | sonnet | Cost-saving mode |
| `/techne-implement fast` | sonnet | Cost-saving + skip pre-flight |

If user says 'sonnet' → switch to sonnet and proceed.

### 5. Check for Implementation Plan

Look for plan at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill for configured path)

### 6. Run Appropriate Agent(s)

Based on detected stack:
- **Go**: Use `software-engineer-go` agent
- **Python**: Use `software-engineer-python` agent
- **Frontend**: Use `software-engineer-frontend` agent
- **Fullstack**: Run backend agent first, then frontend agent (or follow work stream order from plan)

**IMPORTANT**: When invoking the Task tool, include the `model` parameter:
- If user specified model → use that model
- Otherwise → use opus (default)

**Single-stack example:**
```
Task(
  subagent_type: "software-engineer-go",
  model: "{determined_model}",  // "opus" (default) or "sonnet" (if user requested)
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={value}\n\n{task description}"
)
```

**Fullstack example (sequential):**
```
# Step 1: Backend
Task(
  subagent_type: "software-engineer-{go|python}",
  model: "{determined_model}",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={value}\nStack: fullstack\nThis is the BACKEND portion.\n\n{backend task description}"
)

# Step 2: Frontend (after backend completes)
Task(
  subagent_type: "software-engineer-frontend",
  model: "{determined_model}",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={value}\nStack: fullstack\nThis is the FRONTEND portion. Backend implementation is complete.\n\n{frontend task description}"
)
```

Each agent will:
- Read the implementation plan if it exists
- Read its assigned work stream requirements (if plan has work streams)
- Implement the required changes
- Provide summary and suggest next step

### 7. Show Changes

After the agent completes successfully, show the user the changed files:

```bash
git status --short
```

The user will commit manually. Do NOT auto-commit. If the user asks for help drafting a commit message, suggest the following conventions:

**Commit message conventions:**
- `feat(PROJ-123):` for new features
- `fix(PROJ-123):` for bug fixes
- `refactor(PROJ-123):` for refactoring
- Use the Jira issue as scope

### 8. After Completion

Present the agent's summary and suggested next step to the user.

> Implementation complete on branch `$BRANCH`. The user will commit manually.

> **Next**: Run `/techne-test` to write tests.
>
> Say **'continue'** to proceed, or provide corrections.
