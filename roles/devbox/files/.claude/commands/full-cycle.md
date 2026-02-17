---
description: Run complete development cycle with 4 milestone gates (TPM → Domain → Model → Design → Plan → API → Implement → Test → Review)
---

You are orchestrating a complete development cycle with 4 strategic milestone gates. Agents run autonomously between gates.

## Workflow Overview

<pipeline>

1. **Setup** — detect feature type, init pipeline state
2. **TPM** → produces `spec.md` (autonomous)
3. **Domain Expert** → produces `domain_analysis.md` (autonomous)
4. **Domain Modeller** → produces `domain_model.md` (autonomous, skippable for simple domains)
5. **GATE 1** — user approves: "Is this the right problem and domain model?"
6. **Designer** ‖ **Impl Planner** → run in parallel for UI features (autonomous)
7. **GATE 2** — user picks design direction (skipped for backend-only)
8. **API Designer** → produces `api_design.md` (autonomous)
9. **GATE 3** — user approves: "Ready to implement?"
10. **SE → Tests → Review** → implementation cycle with fix loop (autonomous)
11. **GATE 4** — user approves: "Ship it?" → Commit/PR

</pipeline>

<transitions>
- Steps 2-4 run autonomously (TPM → Domain Expert → Domain Modeller), then pause at Gate 1
- Domain Modeller is skipped when: Cynefin = Clear AND <5 entities in discovery model
- Steps 6 run in parallel (Designer + Planner) for UI/fullstack; planner-only for backend
- Gate 2 is skipped when feature_type = backend
- Steps 8 runs autonomously, then pause at Gate 3
- Step 10 runs the full SE → test → review cycle autonomously (with internal fix loop)
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
    "domain_modeller": { "status": "pending", "output": "domain_model.md", "approved_at": null },
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

### Phase 1: Problem Definition + Domain Modelling (autonomous → Gate 1)

All agents in this phase run with `PIPELINE_MODE=true`.

**CRITICAL — Model Selection**: The Task tool inherits the parent's model by default. You MUST pass `model` explicitly on every Task invocation, otherwise opus agents silently run on the parent's model (often Sonnet). Use the model values shown below.

1. Run `technical-product-manager` agent with `PIPELINE_MODE=true` → produces `spec.md`
   ```
   Task(subagent_type: "technical-product-manager", model: "opus", prompt: "PIPELINE_MODE=true\nContext: BRANCH=..., JIRA_ISSUE=..., BRANCH_NAME=...\n\n...")
   ```
2. Update pipeline state: `tpm.status = "completed"`
3. Run `domain-expert` agent with `PIPELINE_MODE=true` → produces `domain_analysis.md`
   ```
   Task(subagent_type: "domain-expert", model: "opus", prompt: "PIPELINE_MODE=true\nContext: BRANCH=..., JIRA_ISSUE=..., BRANCH_NAME=...\n\n...")
   ```
4. Update pipeline state: `domain_expert.status = "completed"`
5. **Domain Modeller decision**: Check `domain_output.json` for `cynefin_classification` and count entities in `discovery_model.entities`:
   - If Cynefin = `clear` AND entity count < 5 → set `domain_modeller.status = "skipped"`
   - Otherwise → Run `domain-modeller` agent:
     ```
     Task(subagent_type: "domain-modeller", model: "opus", prompt: "PIPELINE_MODE=true\nContext: BRANCH=..., JIRA_ISSUE=..., BRANCH_NAME=...\n\n...")
     ```
6. Update pipeline state: `domain_modeller.status = "completed"` (or `"skipped"`)

**GATE 1** — "Is this the right problem and domain model?"

Present summary of spec, domain analysis, and domain model (if produced). Update `current_gate = "G1"`.

> **Gate 1: Problem & Domain Validation**
>
> Spec, domain analysis, and domain model complete. Key findings:
> - [Summary of personas/goals from spec]
> - [Summary of validated/invalidated assumptions from domain analysis]
> - [Summary of bounded contexts and aggregates from domain model, or "Domain model skipped (simple domain)"]
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
1. Run `designer` agent AND `implementation-planner-{lang}` agent in parallel (both with `PIPELINE_MODE=true`):
   ```
   Task(subagent_type: "designer", model: "opus", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   Task(subagent_type: "implementation-planner-{lang}", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
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
1. Run `implementation-planner-{lang}` agent:
   ```
   Task(subagent_type: "implementation-planner-{lang}", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
2. Update pipeline state: `impl_planner.status = "completed"`
3. Skip G2 entirely, proceed to API Designer

### Phase 3: Contracts + Final Check (autonomous → Gate 3)

**Check plan for work streams**: Read `plan_output.json` for `work_streams`. If a schema stream exists, run database designer first.

1. **If plan has schema work stream**: Run `database-designer` agent → produces `schema_design.md` + migrations
   ```
   Task(subagent_type: "database-designer", model: "opus", prompt: "PIPELINE_MODE=true\nContext: ...\nDomain model: {path to domain_model.json}\n\n...")
   ```
   - Pass domain model context: include `domain_model.json` / `domain_model.md` path so database designer can align table/column names with ubiquitous language and respect aggregate boundaries
   - Update pipeline state: `database_designer.status = "completed"`
   - Otherwise: set `database_designer.status = "skipped"`
2. Run `api-designer` agent → produces `api_design.md` + spec files
   ```
   Task(subagent_type: "api-designer", model: "opus", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
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

**PIPELINE_MODE**: All agents in Phase 4 run with `PIPELINE_MODE=true` in their prompt. This means:
- Agents make Tier 2 decisions autonomously (logged in `autonomous_decisions` in structured output)
- Agents return structured results instead of asking "Say 'continue'"
- Only Tier 3 decisions escalate to user (genuine blockers)

See `agent-communication` skill — Pipeline Mode section for full behavior differences.

**Model selection for Phase 4**: SE, test writer, and reviewer agents default to `sonnet`. If `complexity_escalation` is `true` in `workflow.json`, check plan complexity (>200 lines or >10 FRs → escalate to `opus`). Otherwise use `sonnet`.

**Detailed execution:**

1. **Backend implementation** (if applicable):
   ```
   Task(subagent_type: "software-engineer-{lang}", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
   - Implements backend, writes `se_backend_output.json`
   - Update pipeline state: `software_engineer_backend.status = "completed"`

2. **Frontend implementation** (if applicable, can run in parallel with backend when API contract exists):
   ```
   Task(subagent_type: "software-engineer-frontend", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
   - Implements frontend, writes `se_frontend_output.json`
   - Update pipeline state: `software_engineer_frontend.status = "completed"`
   - For `backend`-only features: set `software_engineer_frontend.status = "skipped"`

3. **Observability** (if work stream exists, can run in parallel with implementation):
   ```
   Task(subagent_type: "observability-engineer", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
   - Dashboards and alerts
   - Update pipeline state: `observability_engineer.status = "completed"`
   - If no observability stream: set `observability_engineer.status = "skipped"`

**Commit after implementation** (before testing) — **if `auto_commit` is `true`**:
```bash
.claude/bin/git-safe-commit -m "feat($JIRA_ISSUE): implement $BRANCH_NAME"
```
If `auto_commit` is `false`, skip — changes stay unstaged/uncommitted until user commits.

4. **Testing**:
   ```
   Task(subagent_type: "unit-test-writer-{lang}", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
   - If frontend exists:
     ```
     Task(subagent_type: "unit-test-writer-frontend", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
     ```
   - Test writers read `se_backend_output.json` / `se_frontend_output.json` to target untested areas
   - Run all tests to verify they pass
   - Update pipeline state: `test_writer.status = "completed"`

**Commit after tests** — **if `auto_commit` is `true`**:
```bash
.claude/bin/git-safe-commit -m "test($JIRA_ISSUE): add tests for $BRANCH_NAME"
```

5. **Review**:
   ```
   Task(subagent_type: "code-reviewer-{lang}", model: "sonnet", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
   ```
   - Code reviewer reads `se_backend_output.json` / `se_frontend_output.json` to audit `domain_compliance` and `autonomous_decisions`
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
- Agents run autonomously between gates with `PIPELINE_MODE=true` — they make Tier 2 decisions autonomously, log them in structured output, and return results without prompting
- Individual commands (`/implement`, `/test`, `/review`) still use per-step approval (interactive mode)
- SE agents write per-role output files (`se_backend_output.json`, `se_frontend_output.json`) to avoid conflicts during parallel execution
- Pipeline state persists in `pipeline_state.json` — resume with `/full-cycle` if interrupted
- Decisions are logged in `decisions.json` for audit trail
- Use `stop` at any time to exit
- One Jira ticket can span multiple worktrees (e.g., `PROJ-123_backend`, `PROJ-123_frontend`)
