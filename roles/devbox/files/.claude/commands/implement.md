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
- `/implement sonnet` or `/implement --model sonnet` → use **sonnet** (cost-saving mode)
- `/implement` (no argument) → default **opus**
- `/implement fast` → use **sonnet**, skip all pre-flight checks

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
| `complexity_escalation` | `true` | Legacy flag — ignored (Opus is always the default for SE agents) |

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
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
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
1. Check for `plan_output.json` at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan_output.json`
2. If `work_streams` exist in the JSON, route to the agent specified in each stream
3. If no work streams, ask user: "This is a fullstack project. Which part should I implement? (A) Backend, (B) Frontend, (C) Both sequentially"
4. When running both, run backend first (it may produce API types/contracts the frontend needs), then frontend

### 4. Determine Model

**Default model is opus.** Use sonnet only when the user explicitly requests it (`/implement sonnet` or `/implement fast`).

| User Input | Model | Notes |
|------------|-------|-------|
| `/implement` | opus | Default — highest quality |
| `/implement opus` | opus | Explicit |
| `/implement sonnet` | sonnet | Cost-saving mode |
| `/implement fast` | sonnet | Cost-saving + skip pre-flight |

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

### 6a. Independent Verification

After the agent Task returns, run independent verification before committing or reporting completion. This step does not trust the agent's self-reported results.

**Detect language for verifier** (reuse markers from Step 3):
- `go.mod` exists → `go`
- `pyproject.toml` or `setup.py` exists → `python`
- `package.json` exists → `node`

**Check if verifier is available:**

```bash
VERIFIER=~/.claude/bin/verify-se-completion
if [ ! -x "$VERIFIER" ]; then
  echo "VERIFIER_SKIP: verify-se-completion not found"
fi
```

If the verifier is not found or not executable, skip this step and note it in the completion report.

**Run verification:**

```bash
# Base command
CMD="$VERIFIER --lang <detected-lang> --work-dir <project-root>"

# If the agent produced an output JSON, append --output-file
if [ -n "$SE_OUTPUT_FILE" ] && [ -f "$SE_OUTPUT_FILE" ]; then
  CMD="$CMD --output-file $SE_OUTPUT_FILE"
fi

$CMD
VERIFY_EXIT=$?
```

**Act on the result:**

| Exit code | Meaning | Action |
|-----------|---------|--------|
| `0` | Verification passed | Report "Implementation verified independently" and continue to Step 7 |
| Non-zero | Verification failed | Show failure output; pause before commit; offer re-invocation |

**If verification fails**, show the verifier output and prompt:

> Verification found issues:
>
> ```
> {verifier output}
> ```
>
> Would you like me to re-invoke the agent to fix these?

If the user says yes, go back to Step 6 and spawn the same agent again, passing the verification errors in the prompt context. If the user says no (or wants to proceed anyway), continue to Step 7 with a warning note.

### 6b. Work Log Audit (Advisory)

After verification, run the work log auditor on the agent's output to detect excuse patterns. This is advisory — it does not block completion.

```bash
AUDITOR=~/.claude/bin/audit-work-log
if [ -x "$AUDITOR" ] && [ -n "$SE_OUTPUT_FILE" ] && [ -f "$SE_OUTPUT_FILE" ]; then
  $AUDITOR --se-output "$SE_OUTPUT_FILE" --lang <detected-lang> --json
  AUDIT_EXIT=$?
fi
```

| Exit code | Meaning | Action |
|-----------|---------|--------|
| `0` | Clean | Continue silently |
| `1` | Excuse patterns found | Warn user: "Work log audit flagged potential excuse patterns" |
| `2` | Missing commands | Warn user: "Work log audit found missing expected commands" |
| `3` | Both | Warn user with both findings |

Show warnings but do not block — the independent verification (Step 6a) is the hard gate.

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
