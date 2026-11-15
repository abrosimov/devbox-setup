---
description: Review changes using code reviewer agent
---

You are orchestrating the review phase of a development workflow.

## Parse Arguments

Check if user passed a model argument:
- `/techne-review opus` or `/techne-review --model opus` → use **opus**
- `/techne-review sonnet` or `/techne-review --model sonnet` → use **sonnet**
- `/techne-review` (no argument) → use **opus** (default)

## Steps

### 1. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py)
RC=$?
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

**If exit 0** — parse JSON fields: `PROFILE`, `VAULT`, `BRANCH`, `JIRA_ISSUE` (null when the
branch carries none), `BRANCH_NAME`. Artefacts are notes in `VAULT` (see `config` skill).
**If exit 1** — stderr names what is missing (the profile variable, `.vault-root`, or the vault
directory it names). Relay that line and stop; do not guess a location.

Store these values — pass to agent, do not re-compute.

### 2. Gather Review Context

```bash
git diff $DEFAULT_BRANCH...HEAD
```

Check if implementation plan exists at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill).

Language detection is the agent's responsibility — `code-reviewer` runs `git diff --name-only` in its Step 1, classifies files by extension, and loads only the relevant `{lang}-engineer`/`{lang}-testing` skills. Polyglot diffs (e.g. Go backend + frontend) are reviewed stack-by-stack within a single invocation.

### 3. Run code-reviewer Agent

The unified `code-reviewer` agent handles Go, Python and TypeScript/React/Next.js. No language-specific routing required.

When invoking the Task tool, pass `model: "opus"` explicitly (or the user-specified model).

Example Task invocation:
```
Task(
  subagent_type: "code-reviewer",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}\n\nUser's ask: {the user's request}\nDecisions already made: {decisions, or none}\nIn scope: {files/areas}\nOut of scope: {files/areas}"
)
```

If `JIRA_ISSUE` was resolved to `"none"` in Step 1, pass it through unchanged — the agent will skip Jira fetching and review the diff only.

The agent will:
- Analyze code against requirements
- Check for issues (errors, tests, patterns)
- Provide structured feedback with severity levels

### 4. After Completion

Present the structured feedback:
- Must Fix (Blocking)
- Should Fix (Important)
- Consider (Optional)

- Outside this change (for the user only)

If there are findings, send all of them — Must Fix, Should Fix and Consider — to the matching
software engineer agent without asking the user, then run this review again. The loop and its stop
conditions are in the `workflow` skill, section *Review–fix loop*.

If no findings remain:
> Review passed.

The review reports only. Commits, the push and the PR/MR belong to the engine adapter's git
delivery; fixes made after the review update the PR/MR that is already open.
