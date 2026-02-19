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
| `complexity_escalation` | `true` | If `false`, always use agent's default model (no auto-downgrade of SE agents to Sonnet) |

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
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
RC=$?
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

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
   Task(subagent_type: "implementation-planner-{lang}", model: "opus", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
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
   Task(subagent_type: "implementation-planner-{lang}", model: "opus", prompt: "PIPELINE_MODE=true\nContext: ...\n\n...")
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

### Phase 4: Implementation Cycle (DAG execution → Gate 4)

**Work-stream-driven DAG execution**: Build a task graph from `plan_output.json`, execute nodes as their dependencies resolve, validate each node's output with `bin/validate-pipeline-output`.

All agents in Phase 4 run with `PIPELINE_MODE=true`.

#### Step 1: Build Execution DAG

Read `plan_output.json` for `work_streams`. Build `execution_dag.json` (schema: `schemas/execution_dag.schema.json`):

**Default DAG templates by feature type:**

| Feature | Streams | Nodes per stream |
|---------|---------|-----------------|
| Backend-only | 1 (backend) | se → commit_impl → test → commit_test |
| Frontend-only | 1 (frontend) | se → commit_impl → test → commit_test |
| Fullstack | 2+ (backend, frontend, ...) | se → commit_impl → test → commit_test per stream |

**Cross-stream nodes** (added after all stream nodes):
- `review`: depends on ALL stream `commit_test` nodes
- `gate_4`: depends on `review`

**If plan has `work_streams`** — use them to build the DAG. Each work stream becomes a stream with nodes.
**If no work streams** — use default template based on `feature_type`.

After building, validate the DAG:
```bash
.claude/bin/validate-pipeline-output --dag-check --file execution_dag.json
```

Update `pipeline_state.json`: set `execution_dag_file` to the DAG path.

#### Step 2: Record Baseline

```bash
PRE_EXECUTION_SHA=$(git rev-parse HEAD)
```

Store in `execution_dag.json` as `pre_execution_sha`.

#### Step 3: Launch Ready Nodes

For each node where status is `pending` and ALL dependencies (via `edges`) have status `completed`:
1. Transition node to `ready`, then to `running`
2. Record `pre_sha=$(git rev-parse HEAD)` and `started_at`

**For `agent` nodes** — launch as background Task:

For stream executors (SE + test chain), launch a single background Task per stream using `general-purpose` agent. The prompt instructs the agent to chain steps sequentially:

```
Task(
  subagent_type: "general-purpose",
  model: "opus",
  run_in_background: true,
  prompt: "You are a stream executor for the '{stream}' stream.
    PIPELINE_MODE=true
    Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}

    Execute these steps SEQUENTIALLY:

    1. Run software-engineer-{lang} agent via Task tool:
       Task(subagent_type: 'software-engineer-{lang}', model: '{model}', prompt: 'PIPELINE_MODE=true\n...')

    2. **SE Verification Gate** (independent of agent self-reported results):
       Check if ~/.claude/bin/verify-se-completion exists before running:
       ```bash
       if [ -x ~/.claude/bin/verify-se-completion ]; then
         ~/.claude/bin/verify-se-completion --lang {lang} --work-dir {project-root} \
           [--output-file {PLANS_DIR}/{stream}_se_output.json]
         SE_VERIFY_EXIT=$?
       else
         echo "WARNING: verify-se-completion not found — skipping independent verification"
         SE_VERIFY_EXIT=0
       fi
       ```
       - Exit 0 → log 'independently verified' in pipeline state for this stream's SE stage; continue
       - Non-zero → log failure in pipeline state; record errors; DO NOT proceed to test writer or
         code reviewer. Report errors to orchestrator (include script stderr). The stream executor
         must surface this as a failed step in the completion file so the orchestrator can offer
         to re-invoke the SE agent with the specific errors.

    2b. **Work Log Audit** (advisory — does not block):
       ```bash
       if [ -x ~/.claude/bin/audit-work-log ] && [ -f "{PLANS_DIR}/{stream}_se_output.json" ]; then
         ~/.claude/bin/audit-work-log --se-output "{PLANS_DIR}/{stream}_se_output.json" --lang {lang} --json
         AUDIT_EXIT=$?
       else
         AUDIT_EXIT=0
       fi
       ```
       - Exit 0 → clean, continue
       - Non-zero → log warning in pipeline state; continue (advisory only)

    3. Commit implementation (only if SE verification passed):
       .claude/bin/git-safe-commit -m 'feat({JIRA_ISSUE}): implement {stream}'
    4. Run unit-test-writer-{lang} agent via Task tool:
       Task(subagent_type: 'unit-test-writer-{lang}', model: 'sonnet', prompt: 'PIPELINE_MODE=true\n...')
    5. Commit tests:
       .claude/bin/git-safe-commit -m 'test({JIRA_ISSUE}): add {stream} tests'

    After ALL steps, write a completion file: {PLANS_DIR}/{stream}_completion.json
    conforming to schemas/stream_completion.schema.json:
    {
      'stream': '{stream}',
      'status': 'complete|partial|blocked|failed',
      'steps': [{name, status, error?, output_file?}, ...],
      'git_sha': '$(git rev-parse --short HEAD)',
      'files_modified': [list of files],
      'output_files': [list of JSON outputs],
      'build_passed': true|false,
      'tests_passed': true|false,
      'tests_total': N,
      'tests_failed': N,
      'se_independently_verified': true|false,
      'attempt': {attempt},
      'started_at': '{started_at}',
      'completed_at': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
    }

    The 'steps' array MUST include a 'se_verification' entry immediately after the SE agent step:
    { 'name': 'se_verification', 'status': 'passed|failed|skipped', 'error': '<stderr if failed>' }
    Set 'se_independently_verified' to true only when se_verification.status == 'passed'.

    Run a build check before writing completion (go build/ruff check/tsc --noEmit).
    Set build_passed based on the result.
    If any step fails, set status to 'failed' with the error in the step entry. Still write the completion file."
)
```

Record the `task_id` in the DAG node. Write updated `execution_dag.json`.

**For `commit` nodes** — run directly (not backgrounded):
```bash
.claude/bin/git-safe-commit -m "{commit message}"
```

**For `verify` nodes** — run validation script directly:
```bash
.claude/bin/validate-pipeline-output --full --file {completion_file} --lang {lang}
```

#### Step 4: Poll and Advance Loop

Repeatedly check running nodes and advance the DAG:

```
For each node with status "running":

  1. PRIMARY: Check TaskOutput(task_id=node.task_id, block=false, timeout=5000)
  2. FALLBACK: Check if {stream}_completion.json exists (for phantom completion bug)

  If completed (via either check):
    a. Run validation gate:
       EXIT_CODE = .claude/bin/validate-pipeline-output --full \
         --file {stream}_completion.json --lang {lang}

    b. Branch on exit code:
       0 → node.status = "completed", node.completed_at = now
       1 → RETRY: "Output JSON malformed. Required schema: stream_completion"
       2 → RETRY: "Reality check failed — claimed files don't match filesystem/git"
       3 → RETRY: "Build failed: {stderr from validation script}"
       4 → RETRY: "Tests failed: {stderr from validation script}"

    c. **SE Verification failure** — check completion file for SE verification step status:
       If `steps[].name == "se_verification" && steps[].status == "failed"`:
         node.status = "se_verify_failed"
         Log `software_engineer_{lang}.verification = "failed"` in pipeline state
         ESCALATE to user (do NOT advance to test writer or code reviewer):
           "SE verification failed for stream '{stream}' after independent build/test/lint check.
            Errors from verify-se-completion:
            {errors from completion file step entry}

            Options:
            A) Re-invoke SE agent with these specific errors
            B) Skip verification and continue (not recommended)
            C) Stop pipeline
            [Awaiting your decision]"
         - On A: re-launch stream executor starting from step 1 only (SE agent), passing the errors
           as context. Increment attempt counter.
         - On B: override node.status = "completed", log decision in decisions.json, continue.
         - On C: stop pipeline.

    d. If RETRY (from exit codes 1-4):
       node.attempt += 1
       If attempt > max_attempts:
         node.status = "failed"
         ESCALATE to user:
           "Stream '{stream}' failed validation after {N} attempts.
            Last exit code: {code} — {error}
            Options: A) Retry with different approach  B) Skip stream  C) Stop pipeline
            [Awaiting your decision]"
       Else:
         Launch new background Task with augmented retry prompt:
           "RETRY {attempt}/{max_attempts}
            Previous validation failed (exit code {code}): {error}
            Check existing state via git diff. Continue from where previous agent stopped.
            Do NOT redo work that already exists and is correct.
            If the same error recurs, set status: 'blocked' in completion file."

  If NOT completed:
    Check liveness — if elapsed > timeout_minutes:
      Read output file to check for progress
      If no new content since last poll:
        node.status = "failed", node.error = "Timed out after {timeout} minutes"
        Attempt retry (same as above)
      Else:
        Extend timeout by 5 minutes (once)

  After processing all running nodes:
    Scan for newly ready nodes (all deps completed, status still "pending")
    Transition them to "ready" → launch immediately (Step 3 logic)

  Write updated execution_dag.json after each iteration.

  If all nodes are completed/skipped/failed → exit loop.
```

**IMPORTANT**: When polling, also check completion files via Glob as fallback for the known TaskOutput completion detection bug. If the file exists and validates, trust it even if TaskOutput still says "running".

#### Step 5: Review (after all streams complete)

After all stream nodes reach `completed`:

1. Launch code reviewer:
   ```
   Task(subagent_type: "code-reviewer-{lang}", model: "opus",
     prompt: "PIPELINE_MODE=true\nContext: ...\n\nReview ALL changes across streams...")
   ```

2. **If reviewer finds blocking issues:**
   - Identify which stream(s) are affected
   - Re-launch those stream executors with review feedback
   - Re-run validation on the re-executed streams
   - Re-run review
   - Repeat until clean (max 2 review cycles)

3. **If `auto_commit` is `true`**: commit any review fixes via `.claude/bin/git-safe-commit -m "fix({JIRA_ISSUE}): address review feedback"`

#### Step 6: Gate 4

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
- Phase 4 builds an `execution_dag.json` from plan work streams and executes nodes as dependencies resolve — parallel streams run concurrently, cross-stream nodes (review, gate) wait for all predecessors
- Each stream executor writes a `{stream}_completion.json` validated by `bin/validate-pipeline-output` against `schemas/stream_completion.schema.json` — exit codes drive retry/escalation logic (0=pass, 1=malformed, 2=reality-check, 3=build-fail, 4=test-fail)
- After each SE agent completes, `~/.claude/bin/verify-se-completion` runs as an independent gate before test writer or code reviewer stages. This is separate from the agent's self-reported Pre-Flight results. If the script is absent, the gate is skipped with a warning. A non-zero exit blocks pipeline advancement and offers to re-invoke the SE agent with the specific errors. The result is recorded as `se_independently_verified` in the completion file and as `verification` on the SE stage in pipeline state.
- Pipeline state persists in `pipeline_state.json` and `execution_dag.json` — resume with `/full-cycle` if interrupted
- Decisions are logged in `decisions.json` for audit trail
- Use `stop` at any time to exit
- One Jira ticket can span multiple worktrees (e.g., `PROJ-123_backend`, `PROJ-123_frontend`)
