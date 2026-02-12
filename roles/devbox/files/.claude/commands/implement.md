---
description: Implement current task using software engineer agent
---

You are orchestrating the implementation phase of a development workflow.

## CRITICAL: Verify User Approval Before Implementation

**Before spawning any implementation agent, verify ONE of these conditions:**

1. User explicitly invoked `/implement` command (this counts as approval)
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
- `/implement opus` or `/implement --model opus` → use **opus**
- `/implement sonnet` or `/implement --model sonnet` → use **sonnet**
- `/implement` (no argument) → determine model via complexity check

## Steps

### 0. Read Workflow Config

```bash
cat .claude/workflow.json 2>/dev/null || echo '{}'
```

Parse the JSON. Extract flags (default to `true` if key is missing, to preserve backward compatibility with projects that have the file but lack a key):

| Flag | Default | Effect |
|------|---------|--------|
| `agent_pipeline` | `true` | If `false`, this command still works but isn't mandatory |
| `auto_commit` | `true` | If `false`, skip commit steps (Steps 7-8 change) |
| `complexity_escalation` | `true` | If `false`, skip Step 4 (always use agent's default model) |

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
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

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
1. Check for `plan_output.json` at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan_output.json`
2. If `work_streams` exist in the JSON, route to the agent specified in each stream
3. If no work streams, ask user: "This is a fullstack project. Which part should I implement? (A) Backend, (B) Frontend, (C) Both sequentially"
4. When running both, run backend first (it may produce API types/contracts the frontend needs), then frontend

### 4. Pre-flight Complexity Check (if no model specified)

**Skip this step if user explicitly specified a model OR `complexity_escalation` is `false`.**

Run complexity assessment:

**For Go projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | wc -l

# Check for concurrency patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -l "go func\|chan \|sync\.\|select {" 2>/dev/null | wc -l
```

**For Python projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test_ | grep -v _test.py | wc -l

# Check for async patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -l "async def\|await\|asyncio" 2>/dev/null | wc -l
```

**For Frontend projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.ts' '*.tsx' 2>/dev/null | grep -v '.test.' | grep -v '.spec.' | grep -v '__tests__' | wc -l

# Check for complex patterns (Server Components + Client Components interleaving, complex state)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.ts' '*.tsx' 2>/dev/null | grep -v '.test.' | xargs grep -l "createContext\|useReducer\|Suspense" 2>/dev/null | wc -l
```

**Escalation thresholds:**

| Metric | Threshold | Model |
|--------|-----------|-------|
| Plan lines | > 200 | opus |
| Changed files (non-test) | > 8 | opus |
| Concurrency/async/complex patterns | Any | opus |
| Otherwise | - | sonnet |

**If ANY threshold exceeded**, use **opus**. Otherwise use **sonnet**.

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
- If complexity check determined model → use that model

**Single-stack example:**
```
Task(
  subagent_type: "software-engineer-go",
  model: "{determined_model}",  // "sonnet" or "opus"
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\n{task description}"
)
```

**Fullstack example (sequential):**
```
# Step 1: Backend
Task(
  subagent_type: "software-engineer-{go|python}",
  model: "{determined_model}",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\nStack: fullstack\nThis is the BACKEND portion.\n\n{backend task description}"
)

# Step 2: Frontend (after backend completes)
Task(
  subagent_type: "software-engineer-frontend",
  model: "{determined_model}",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\nStack: fullstack\nThis is the FRONTEND portion. Backend implementation is complete.\n\n{frontend task description}"
)
```

Each agent will:
- Read the implementation plan if it exists
- Read its assigned work stream requirements (if plan has work streams)
- Implement the required changes
- Provide summary and suggest next step

### 7. Commit Changes

**If `auto_commit` is `false`, skip this step.** Show changed files and tell the user:

> Changes ready on branch `$BRANCH`. Commit when you're ready.

**If `auto_commit` is `true` (default):**

After the agent completes successfully, commit the implementation:

```bash
# List changed files for the commit
git status --short

# Commit using safety wrapper (blocks protected branches, rejects secrets)
.claude/bin/git-safe-commit -m "feat($JIRA_ISSUE): <concise description of implementation>"
```

**Commit message conventions:**
- `feat(PROJ-123):` for new features
- `fix(PROJ-123):` for bug fixes
- `refactor(PROJ-123):` for refactoring
- Use the Jira issue as scope

If specific files should be committed (not all changes):
```bash
.claude/bin/git-safe-commit -m "feat($JIRA_ISSUE): <description>" file1.go file2.go
```

### 8. After Completion

Present the agent's summary and suggested next step to the user.

**If auto_commit was on:**
> Implementation committed on branch `$BRANCH`.

**If auto_commit was off:**
> Implementation complete on branch `$BRANCH` (not committed).

> **Next**: Run `/test` to write tests.
>
> Say **'continue'** to proceed, or provide corrections.
