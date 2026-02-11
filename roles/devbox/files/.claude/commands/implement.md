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

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to agent, do not re-compute.

### 2. Detect Project Stack

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

### 3. Pre-flight Complexity Check (if no model specified)

**Skip this step if user explicitly specified a model.**

Run complexity assessment:

**For Go projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | wc -l

# Check for concurrency patterns
git diff main...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | xargs grep -l "go func\|chan \|sync\.\|select {" 2>/dev/null | wc -l
```

**For Python projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test_ | grep -v _test.py | wc -l

# Check for async patterns
git diff main...HEAD --name-only -- '*.py' 2>/dev/null | grep -v test | xargs grep -l "async def\|await\|asyncio" 2>/dev/null | wc -l
```

**For Frontend projects:**
```bash
# Count lines in plan (if exists)
wc -l {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null | awk '{print $1}'

# Count changed files (excluding tests)
git diff main...HEAD --name-only -- '*.ts' '*.tsx' 2>/dev/null | grep -v '.test.' | grep -v '.spec.' | grep -v '__tests__' | wc -l

# Check for complex patterns (Server Components + Client Components interleaving, complex state)
git diff main...HEAD --name-only -- '*.ts' '*.tsx' 2>/dev/null | grep -v '.test.' | xargs grep -l "createContext\|useReducer\|Suspense" 2>/dev/null | wc -l
```

**Escalation thresholds:**

| Metric | Threshold | Model |
|--------|-----------|-------|
| Plan lines | > 200 | opus |
| Changed files (non-test) | > 8 | opus |
| Concurrency/async/complex patterns | Any | opus |
| Otherwise | - | sonnet |

**If ANY threshold exceeded**, use **opus**. Otherwise use **sonnet**.

### 4. Check for Implementation Plan

Look for plan at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill for configured path)

### 5. Run Appropriate Agent(s)

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
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\n\n{task description}"
)
```

**Fullstack example (sequential):**
```
# Step 1: Backend
Task(
  subagent_type: "software-engineer-{go|python}",
  model: "{determined_model}",
  prompt: "Context: ...\nStack: fullstack\nThis is the BACKEND portion.\n\n{backend task description}"
)

# Step 2: Frontend (after backend completes)
Task(
  subagent_type: "software-engineer-frontend",
  model: "{determined_model}",
  prompt: "Context: ...\nStack: fullstack\nThis is the FRONTEND portion. Backend implementation is complete.\n\n{frontend task description}"
)
```

Each agent will:
- Read the implementation plan if it exists
- Read its assigned work stream requirements (if plan has work streams)
- Implement the required changes
- Provide summary and suggest next step

### 6. After Completion

Present the agent's summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections.
