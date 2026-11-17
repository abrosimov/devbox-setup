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

**If exit 0** — parse JSON fields: `PROFILE`, `VAULT`, `BRANCH`, `JIRA_ISSUE` (null when the
branch carries none), `BRANCH_NAME`. Artefacts are notes in `VAULT` (see `config` skill).
**If exit 1** — stderr names what is missing (the profile variable, `.vault-root`, or the vault
directory it names). Relay that line and stop; do not guess a location.
If `JIRA_ISSUE` is null and the request or the plan names an issue key, use that key.

Store these values (including `DEFAULT_BRANCH` from Git Setup) — pass to agent, do not re-compute.

### 3. Route by Agent File Scope

The agents declare the files they own in their `globs:` frontmatter; this command holds no stack
table of its own, so a new engineer agent is routed to as soon as it declares `globs:`.

1. Read the `globs:` field of every agent definition in `~/.claude/agents/*.md`. A pattern prefixed
   with `!` excludes files from that agent's ownership: an agent owns a file when one of its plain
   patterns matches it and none of its `!` patterns does. Engineers exclude test files this way;
   `unit-test-writer` claims them.
2. List the files the change will touch: from the plan's work streams, from the request, or — when
   neither names them — the tracked files of the area the request describes (`git ls-files`).
3. Every agent that owns one of those files is a claimant, and owns the matching files. Test files
   never go to an engineer: they are handled in step 7 (Run the Test Writer), even when the request
   is only about tests.

| Claimants | Classification | Agent(s) |
|-----------|---------------|----------|
| One | that agent's stack | that agent |
| `software-engineer-frontend` plus a backend engineer | `fullstack` | See fullstack routing below |
| Several backend engineers | per-file ownership | Each claimant gets its own files; run them in parallel only when their files do not depend on each other |
| None | — | No agent covers the work: say so in one line and stop; the main session decides whether to work directly under the engine adapter's carve-outs |

**Fullstack routing** — when both backend and frontend claimants exist:
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

Based on the claimants from step 3:
- **One claimant**: run that agent with the files it owns
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
  prompt: "Context: PROFILE={value}, VAULT={path}, BRANCH={value}, JIRA_ISSUE={value or null}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\nUser's ask: {the user's request}\nDecisions already made: {decisions, or none}\nIn scope: {files/areas}\nOut of scope: {files/areas}"
)
```

**Fullstack example (parallel, contract first):**
```
# Step 0: the contract exists (run /techne-api-design if it does not)

# Step 1: Backend and frontend, launched together in one message
Task(
  subagent_type: "software-engineer-{go|python}",
  model: "{determined_model}",
  prompt: "Context: PROFILE={value}, VAULT={path}, BRANCH={value}, JIRA_ISSUE={value or null}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\nStack: fullstack\nThis is the BACKEND portion.\nAPI contract: {contract_path}. Implement exactly what it guarantees; do not rely on how the frontend calls you.\n\nUser's ask: {backend part of the request}\nDecisions already made: {decisions, or none}\nIn scope: {backend files/areas}\nOut of scope: {frontend, and anything else excluded}"
)
Task(
  subagent_type: "software-engineer-frontend",
  model: "{determined_model}",
  prompt: "Context: PROFILE={value}, VAULT={path}, BRANCH={value}, JIRA_ISSUE={value or null}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\nStack: fullstack\nThis is the FRONTEND portion.\nAPI contract: {contract_path}. Build only on what it guarantees; raise a contract gap for anything missing.\n\nUser's ask: {frontend part of the request}\nDecisions already made: {decisions, or none}\nIn scope: {frontend files/areas}\nOut of scope: {backend, and anything else excluded}"
)
```

Each prompt carries the contract path and its own task only. Leave out backend progress ("backend is complete") and backend file paths from the frontend prompt, and frontend details from the backend prompt: those invite reasoning from the other side's implementation, which the contract exists to replace.

Each agent will:
- Read the implementation plan if it exists
- Read its assigned work stream requirements (if plan has work streams)
- Implement the required changes
- Provide summary and suggest next step

### 7. Run the Test Writer

Every implementation run ends with tests written by a test writer, never by the engineer
(`code-writing-protocols` — Test Ownership). Once the engineer(s) have finished, run without asking:

- **`unit-test-writer`**, always, for the behaviour the engineer changed. Pick its model as
  `/techne-test` does (its pre-flight complexity check), unless the user named a model for this run.
- **`integration-tests-writer-{go,python}`** as well, when the plan has an integration-test work
  stream or the engineer's handoff names integration scenarios (database, HTTP, messaging).

The brief carries the same four fields as the engineer's, plus the engineer's handoff verbatim: the
files changed, the scenarios it named for coverage, and the existing tests it reported as broken by
a deliberate behaviour change, which the test writer updates.

When the test writer reports a defect in production code, send the failing test back to the
engineer with the defect, then rerun the test writer on the fix. This is the review–fix loop of the
`workflow` skill and is bounded the same way.

If the engineer's run produced no behaviour change (a rename, a comment, a config value), skip this
step and say so in one line.

### 8. Show Changes

After the agents complete successfully, show the user the changed files:

```bash
git status --short
```

Commit, push and the PR/MR follow the core's §7 git delivery; write their text with the
`commit-and-pr-text` skill.

### 9. After Completion

Present the engineer's and the test writer's summaries to the user.

> Implementation and tests complete on branch `$BRANCH`.

> **Next**: Run `/techne-review` to review all changes.
