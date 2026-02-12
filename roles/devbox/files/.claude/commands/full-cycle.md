---
description: Run complete development cycle with 4 milestone gates (TPM → Domain → Design → Plan → API → Implement → Test → Review)
---

You are orchestrating a complete development cycle with 4 strategic milestone gates. Agents run autonomously between gates.

## Workflow Overview

<pipeline>

1. **Setup** — detect feature type, init pipeline state
2. **TPM** → produces `spec.md` (autonomous)
3. **Domain Expert** → produces `domain_analysis.md` (autonomous)
4. **GATE 1** — user approves: "Is this the right problem?"
5. **Designer** ‖ **Impl Planner** → run in parallel for UI features (autonomous)
6. **GATE 2** — user picks design direction (skipped for backend-only)
7. **API Designer** → produces `api_design.md` (autonomous)
8. **GATE 3** — user approves: "Ready to implement?"
9. **SE → Tests → Review** → implementation cycle with fix loop (autonomous)
10. **GATE 4** — user approves: "Ship it?" → Commit/PR

</pipeline>

<transitions>
- Steps 2-3 run autonomously, then pause at Gate 1
- Steps 5 run in parallel (Designer + Planner) for UI/fullstack; planner-only for backend
- Gate 2 is skipped when feature_type = backend
- Steps 7 runs autonomously, then pause at Gate 3
- Step 9 runs the full SE → test → review cycle autonomously (with internal fix loop)
- Gate 4 is the final ship/no-ship decision
</transitions>

## Steps

### Phase 0: Setup (Gate 0)

**Read Workflow Config**:

```bash
cat .claude/workflow.json 2>/dev/null || echo '{}'
```

Parse the JSON. Extract flags (default to `true` if key is missing):

| Flag | Default | Effect in Full-Cycle |
|------|---------|---------------------|
| `auto_commit` | `true` | If `false`, skip all auto-commit steps; show changes and let user commit |
| `complexity_escalation` | `true` | If `false`, always use agent's default model (no auto-escalation to Opus) |

Note: `agent_pipeline` is not checked here — `/full-cycle` always uses agents by definition.

**Git Setup**:

```bash
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
CURRENT=$(git branch --show-current)
```

| Current Branch | Action |
|---------------|--------|
| `main` / `master` / `$DEFAULT_BRANCH` | Create feature branch from it |
| Feature branch (anything else) | Use as-is |

If creating a feature branch, ask user for name (convention: `PROJ-123_short_description`):
```bash
# Create and switch to feature branch
git checkout -b <branch-name> "$DEFAULT_BRANCH"
```

**Compute Task Context (once)**:
```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values (including `DEFAULT_BRANCH` from Git Setup) — pass to all agents throughout the cycle.

**Detect project stack**:
- If `go.mod` exists → **Go backend**
- If `pyproject.toml` or `requirements.txt` exists → **Python backend**
- If `package.json` or `tsconfig.json` or `next.config.*` exists → **Frontend**
- If backend + frontend markers → **Fullstack**
- If unclear → Ask user

**Initialise pipeline state**:

Check for existing `{PROJECT_DIR}/pipeline_state.json`. If found, resume from current state. If not found, create it:

```json
{
  "pipeline_id": "{JIRA_ISSUE}_{BRANCH_NAME}",
  "feature_type": "pending_detection",
  "stages": {
    "tpm": { "status": "pending", "output": "spec.md", "approved_at": null },
    "domain_expert": { "status": "pending", "output": "domain_analysis.md", "approved_at": null },
    "designer": { "status": "pending", "output": "design.md", "selected_option": null, "approved_at": null },
    "impl_planner": { "status": "pending", "output": "plan.md", "approved_at": null },
    "database_designer": { "status": "pending", "output": "schema_design.md", "approved_at": null },
    "api_designer": { "status": "pending", "output": "api_design.md", "approved_at": null },
    "software_engineer_backend": { "status": "pending", "approved_at": null },
    "software_engineer_frontend": { "status": "pending", "approved_at": null },
    "test_writer": { "status": "pending", "approved_at": null },
    "code_reviewer": { "status": "pending", "approved_at": null },
    "observability_engineer": { "status": "pending", "approved_at": null }
  },
  "current_gate": "none",
  "decisions": []
}
```

Also initialise `{PROJECT_DIR}/decisions.json` if it doesn't exist:
```json
{ "decisions": [] }
```

**Update pipeline state** at each phase transition — set stage status to `in_progress` before running agent, `completed` after agent finishes, record `approved_at` when user approves at a gate.

### Phase 1: Problem Definition (autonomous → Gate 1)

1. Run `technical-product-manager` agent → produces `spec.md`
2. Update pipeline state: `tpm.status = "completed"`
3. Run `domain-expert` agent → produces `domain_analysis.md`
4. Update pipeline state: `domain_expert.status = "completed"`

**GATE 1** — "Is this the right problem?"

Present summary of spec and domain analysis. Update `current_gate = "G1"`.

> **Gate 1: Problem Validation**
>
> Spec and domain analysis complete. Key findings:
> - [Summary of personas/goals from spec]
> - [Summary of validated/invalidated assumptions from domain analysis]
> - [Any blockers or risks]
>
> **[Awaiting your decision]** — Approve to proceed, or provide corrections.

Record decision in `decisions.json`. On approval, update `current_gate = "none"`.

### Phase 2: Design + Planning (autonomous → Gate 2)

**Feature Type Detection** (after G1):

1. Check `spec.md` / `spec_output.json` for UI-related requirements
2. Check if project has frontend markers (`package.json`, `tsconfig.json`, `next.config.*`, `*.tsx`, `*.vue`, `*.svelte`, `*.jsx`)
3. If unclear, ask user:

```markdown
This feature could be:
A) **UI feature** — has user-facing interface (Designer + Planner parallel → API Designer → SE)
B) **Backend-only** — API/service change, no UI (Planner → API Designer → SE)
C) **Full-stack** — both UI and backend (Designer + Planner parallel → API Designer → SE frontend + SE backend)

**[Awaiting your decision]**
```

Update `pipeline_state.json` with `feature_type`.

**Routing:**

| Type | Path | G2 |
|------|------|----|
| `ui` | [Designer ‖ Planner] → G2 → API Designer → G3 | Design options presented |
| `backend` | Planner → API Designer → G3 | **Skipped** |
| `fullstack` | [Designer ‖ Planner] → G2 → API Designer → G3 | Design options presented |

**For UI / fullstack features:**
1. Run `designer` agent AND `implementation-planner-{lang}` agent (parallel)
2. Designer presents 3-5 design options
3. Update pipeline state: `designer.status = "completed"`, `impl_planner.status = "completed"`

**GATE 2** — "Which design direction?"

> **Gate 2: Design Direction**
>
> [Designer's options are presented inline]
>
> **[Awaiting your decision]** — Pick a direction, mix elements, or ask for variations.

Record chosen option in `decisions.json` and `pipeline_state.json` (`designer.selected_option`).
On approval, Designer develops full spec for selected option autonomously.

**For backend features:**
1. Run `implementation-planner-{lang}` agent
2. Update pipeline state: `impl_planner.status = "completed"`
3. Skip G2 entirely, proceed to API Designer

### Phase 3: Contracts + Final Check (autonomous → Gate 3)

**Check plan for work streams**: Read `plan_output.json` for `work_streams`. If a schema stream exists, run database designer first.

1. **If plan has schema work stream**: Run `database-designer` agent → produces `schema_design.md` + migrations
   - Update pipeline state: `database_designer.status = "completed"`
   - Otherwise: set `database_designer.status = "skipped"`
2. Run `api-designer` agent → produces `api_design.md` + spec files
   - Update pipeline state: `api_designer.status = "completed"`

**GATE 3** — "Ready to implement?"

Present summary of all planning artifacts. Update `current_gate = "G3"`.

> **Gate 3: Implementation Readiness**
>
> All planning artifacts complete:
> - Spec: `spec.md` [summary]
> - Domain: `domain_analysis.md` [summary]
> - Plan: `plan.md` [N functional requirements, M work streams]
> - Design: `design.md` [N components, M tokens] (if applicable)
> - Schema: `schema_design.md` [N tables, M migrations] (if applicable)
> - API: `api_design.md` [N resources, M endpoints]
>
> Work stream execution order:
> [List streams from plan_output.json with parallelism notes]
>
> **[Awaiting your decision]** — Approve to start implementation, or provide corrections.

Record decision in `decisions.json`. On approval, update `current_gate = "none"`.

### Phase 4: Implementation Cycle (autonomous → Gate 4)

**Work-stream-driven execution**: Read `plan_output.json` for `work_streams` and `parallelism_groups`.

**If work streams exist** — follow the dependency graph:
1. Execute streams in parallelism group order (lower group numbers first)
2. Within a group, streams can run in parallel (use concurrent Task invocations)
3. After all implementation streams complete, run tests and review

**If no work streams** (backward compatible) — use default sequential:
1. Run backend SE → frontend SE (if fullstack)

**Detailed execution:**

1. **Backend implementation** (if applicable):
   - Run `software-engineer-{lang}` agent → implements backend
   - Update pipeline state: `software_engineer_backend.status = "completed"`

2. **Frontend implementation** (if applicable, can run in parallel with backend when API contract exists):
   - Run `software-engineer-frontend` agent → implements frontend
   - Update pipeline state: `software_engineer_frontend.status = "completed"`
   - For `backend`-only features: set `software_engineer_frontend.status = "skipped"`

3. **Observability** (if work stream exists, can run in parallel with implementation):
   - Run `observability-engineer` agent → dashboards and alerts
   - Update pipeline state: `observability_engineer.status = "completed"`
   - If no observability stream: set `observability_engineer.status = "skipped"`

**Commit after implementation** (before testing) — **if `auto_commit` is `true`**:
```bash
.claude/bin/git-safe-commit -m "feat($JIRA_ISSUE): implement $BRANCH_NAME"
```
If `auto_commit` is `false`, skip — changes stay unstaged/uncommitted until user commits.

4. **Testing**:
   - Run `unit-test-writer-{lang}` agent → writes backend tests
   - Run `unit-test-writer-frontend` agent → writes frontend tests (if frontend exists)
   - Run all tests to verify they pass
   - Update pipeline state: `test_writer.status = "completed"`

**Commit after tests** — **if `auto_commit` is `true`**:
```bash
.claude/bin/git-safe-commit -m "test($JIRA_ISSUE): add tests for $BRANCH_NAME"
```

5. **Review**:
   - Run `code-reviewer-{lang}` agent → reviews implementation
   - Update pipeline state: `code_reviewer.status = "completed"`

**If reviewer finds blocking issues:**
- Run appropriate SE agent(s) with review feedback (fix loop)
- Re-run tests
- Re-run review
- If `auto_commit` is `true`: commit fixes via `.claude/bin/git-safe-commit -m "fix($JIRA_ISSUE): address review feedback"`
- Repeat until clean

**GATE 4** — "Ship it?"

Update `current_gate = "G4"`.

> **Gate 4: Ship Decision**
>
> Implementation complete. Review passed with no blocking issues.
> - [Summary of changes: N files modified, M tests written]
> - [Review result: X blocking (fixed) | Y important | Z suggestions]
> - Branch: `$BRANCH` (N commits ahead of `$DEFAULT_BRANCH`)
>
> **[Awaiting your decision]**:
> - **'pr'** — push branch and create pull request
> - **'done'** — finish without pushing (changes stay on feature branch)
> - Or provide corrections.

Record decision in `decisions.json`.

### Phase 5: Push + PR (if requested)

When user says **'pr'**:

```bash
# Ensure everything is committed
if ! git diff --quiet || ! git diff --cached --quiet; then
  # If auto_commit is false, warn about uncommitted changes and ask user to commit first
  # If auto_commit is true (default):
  .claude/bin/git-safe-commit -m "chore($JIRA_ISSUE): final cleanup"
fi

# Push and create PR
git push -u origin $BRANCH
gh pr create --title "feat($JIRA_ISSUE): $BRANCH_NAME" --body "$(cat <<'EOF'
## Summary
[Summary of changes from implementation]

## Test plan
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual verification

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

If push/PR succeeds:
> PR created for `$BRANCH` against `$DEFAULT_BRANCH`.
>
> Next steps:
> - Review the PR in GitHub
> - Delete feature branch after merge: `git branch -d $BRANCH`
> - Clean up worktree: `claude-wt rm $BRANCH` (if using worktrees)

## User Commands (Available at Any Gate)

| Command | Action |
|---------|--------|
| `continue` / `approve` | Proceed past current gate |
| `option A/B/C` | Select a design option (Gate 2) |
| `fix <instruction>` | Apply specific correction before continuing |
| `skip` | Skip current phase, move to next gate |
| `stop` | End workflow entirely |
| `back` | Return to previous gate |
| `pr` | Push branch and create PR (Gate 4) |
| `done` | Finish without pushing (Gate 4) |

## Git Workflow

- **Branch creation**: Phase 0 creates a feature branch from the default branch if needed
- **Auto-commits**: Implementation and test phases auto-commit via `git-safe-commit` (when `auto_commit: true` in `workflow.json`)
- **Manual commits**: When `auto_commit: false`, the pipeline shows changes but lets the user commit
- **Push + PR**: Gate 4 offers to push and create a pull request
- **Safety**: All git operations go through `.claude/bin/git-safe-*` scripts
- **Protected branches**: Commits blocked on `main`, `master` via hooks
- **Push requires approval**: The pipeline never pushes without user confirmation

### Commit Convention

```
<type>(<JIRA_ISSUE>): <description>
```

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

## Notes

- The pipeline pauses only at 4 strategic gates, not after every agent
- Agents run autonomously between gates
- Individual commands (`/implement`, `/test`, `/review`) still use per-step approval
- Pipeline state persists in `pipeline_state.json` — resume with `/full-cycle` if interrupted
- Decisions are logged in `decisions.json` for audit trail
- Use `stop` at any time to exit
- One Jira ticket can span multiple worktrees (e.g., `PROJ-123_backend`, `PROJ-123_frontend`)
