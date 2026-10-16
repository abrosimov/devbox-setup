---
description: Implement current task using software engineer agent
---

You are orchestrating the implementation phase of a development workflow.

## Approval before implementation

Spawn an implementation agent only when one of these holds:

1. The user invoked `/techne-implement` (this counts as approval).
2. The user said "yes", "go ahead", "proceed", "implement it" after seeing a proposal.
3. The user picked a specific option from alternatives presented.

If the user only asked for analysis, a proposal, or options, present that and wait (core §1).

## Code goes through agents

Do not write code directly. This command exists so that every code change goes through a specialised
agent that carries the language standards, the production necessities (error handling, logging,
timeouts), and the project's own patterns. If you are about to write code without an agent, use this
command instead.

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

**If creating a feature branch**, name it yourself and state the name in one line: `PROJ-123_short_description`
when the request or the plan names a Jira issue, otherwise `adhoc_short_description` (a slug of the
task). Do not ask.

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
**If exit 2** — the branch does not match the `PROJ-123_description` convention. Use a Jira key only
when the request or the plan names one (`JIRA_ISSUE={key}`,
`PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`); otherwise
`PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`. State the choice in one line; do
not ask.

Store these values (including `DEFAULT_BRANCH` from Git Setup) — pass to agent, do not re-compute.

### 3. Detect Project Stack

Check for project markers (check all — a project may have multiple):
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
| Unclear | — | The side the request names; otherwise backend. State the assumption in one line |

**Fullstack routing** — when both backend and frontend markers exist:
1. Check for `plan.md` at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md`
2. If `plan.md` defines work streams, route to the agent specified in each stream
3. If no work streams and the request does not say which side, decide: both sides in parallel against the API contract when the change touches the contract, otherwise the side the change lives on. State the choice in one line; do not ask.
4. When running both, the contract comes first. Locate the API contract (`api_spec.yaml`, `*.proto`, or the project's OpenAPI spec; path from `plan.md` if it names one). If none exists, run `/techne-api-design` first. Once the contract exists, backend and frontend may run in parallel, because each builds against the contract and neither reads the other's code (see the `contract-boundary` skill)

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
- **Fullstack**: Make sure the API contract exists (run `/techne-api-design` if not), then run the backend and frontend agents in parallel, each given the contract path (or follow work stream order from plan)

When invoking the Task tool, include the `model` parameter:
- If user specified model → use that model
- Otherwise → use opus (default)

**The brief.** Every prompt carries these four fields after the context line (`agent-communication` — Dispatch Brief):

| Field | Contents |
|-------|----------|
| `User's ask` | The user's request, quoted or closely paraphrased, or the plan path and the work stream it covers |
| `Decisions already made` | Choices the user made in the conversation and binding plan rows; `none` if none |
| `In scope` | The files, packages, or areas the change may touch |
| `Out of scope` | Areas the change leaves alone, including anything the user excluded |

The brief carries the user's ask and the decisions already made, nothing more (core §6). Your own ideas — an extra TODO, a check script, an update to a neighbouring artefact such as `openapi.yaml` — are not tasks for the engineer, because an engineer implements whatever its brief lists. Put them in your report to the user instead.

**Single-stack example:**
```
Task(
  subagent_type: "software-engineer-go",
  model: "{determined_model}",  // "opus" (default) or "sonnet" (if user requested)
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={value}\n\nUser's ask: {the user's request}\nDecisions already made: {decisions, or none}\nIn scope: {files/areas}\nOut of scope: {files/areas}"
)
```

**Fullstack example (parallel, contract first):**
```
# Step 0: the contract exists (run /techne-api-design if it does not)

# Step 1: Backend and frontend, launched together in one message
Task(
  subagent_type: "software-engineer-{go|python}",
  model: "{determined_model}",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={value}\nStack: fullstack\nThis is the BACKEND portion.\nAPI contract: {contract_path}. Implement exactly what it guarantees; do not rely on how the frontend calls you.\n\nUser's ask: {backend part of the request}\nDecisions already made: {decisions, or none}\nIn scope: {backend files/areas}\nOut of scope: {frontend, and anything else excluded}"
)
Task(
  subagent_type: "software-engineer-frontend",
  model: "{determined_model}",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={value}\nStack: fullstack\nThis is the FRONTEND portion.\nAPI contract: {contract_path}. Build only on what it guarantees; raise a contract gap for anything missing.\n\nUser's ask: {frontend part of the request}\nDecisions already made: {decisions, or none}\nIn scope: {frontend files/areas}\nOut of scope: {backend, and anything else excluded}"
)
```

Each prompt carries the contract path and its own task only. Leave out backend progress ("backend is complete") and backend file paths from the frontend prompt, and frontend details from the backend prompt: those invite reasoning from the other side's implementation, which the contract exists to replace.

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

The user will commit manually. Do not auto-commit. If the user asks for help drafting a commit message, suggest the following conventions:

**Commit message conventions:**
- `feat(PROJ-123):` for new features
- `fix(PROJ-123):` for bug fixes
- `refactor(PROJ-123):` for refactoring
- Use the Jira issue as scope

### 8. After Completion

Present the agent's summary and suggested next step to the user.

> Implementation complete on branch `$BRANCH`. The user will commit manually.

> **Next**: Run `/techne-test` to write tests.
