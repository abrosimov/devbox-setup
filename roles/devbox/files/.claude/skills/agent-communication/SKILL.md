---
name: agent-communication
description: >
  Shared patterns for agent handoffs, escalation rules, completion formats, and user interaction.
  Use when agents need to communicate with each other or with users.
  Triggers on: handoff, escalation, completion, next step, continue, approval.
---

# Agent Communication Patterns

Standardised patterns for agent-to-agent handoffs, user communication, and escalation.

## Handoff Protocol

Every agent must define its position in the pipeline:

```markdown
**Receives from**: <upstream agent or "User"> (`document.md` + optionally `{stage}_output.json`)
**Produces for**: <downstream agent or "User">
**Deliverables**:
  - `document.md` — primary (human-readable reasoning and rationale)
  - `{stage}_output.json` — supplementary (structured contract for downstream agents, see `structured-output` skill)
**Completion criteria**: <what must be true before handoff>
```

When reading upstream output, check for `{stage}_output.json` first (faster, typed). Fall back to the markdown file if JSON is not available.

### Common Pipelines

| Pipeline | Flow |
|----------|------|
| Full cycle (backend) | TPM → Domain Expert → Domain Modeller → G1 → Planner → [Schema Designer ‖ API Designer] → G3 → SE-backend → Tests → Review → G4 |
| Full cycle (UI) | TPM → Domain Expert → Domain Modeller → G1 → [Designer ‖ Planner] → G2 → API Designer → G3 → SE-frontend → Tests → Review → G4 |
| Full cycle (fullstack) | TPM → Domain Expert → Domain Modeller → G1 → [Designer ‖ Planner] → G2 → [Schema Designer ‖ API Designer] → G3 → [SE-backend ‖ SE-frontend] → Tests → Review → G4 |
| API design only | User → API Designer → SE |
| UI design only | User → Designer → SE-frontend |
| Quick fix (backend) | User → SE-backend → Test Writer → Reviewer |
| Quick fix (frontend) | User → SE-frontend → Test Writer → Reviewer |
| Quick fix (fullstack) | User → [SE-backend ‖ SE-frontend] → Test Writer → Reviewer |
| Test only | User → Test Writer → Reviewer |
| Review only | User → Reviewer |
| Build (3-gate) | User → Builder → G1 → Meta-Reviewer → G2 → Content Reviewer → G3 |
| Audit (full) | User → [Freshness Auditor ‖ Consistency Checker] → merged report |
| Audit (fix) | User → [Freshness Auditor ‖ Consistency Checker] → Builder(s) per artifact |

### Artifact Registry (Single Source of Truth)

Every file in the pipeline is listed here. Agents reference this table in their Step 1 to know what to read.

All paths are relative to `{PROJECT_DIR}` (see `config` skill: `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`).

| Agent | Reads | Writes |
|-------|-------|--------|
| **TPM** | *(user input)* | `spec.md`, `research.md`, `decisions.md`, `spec_output.json` |
| **Domain Expert** | `spec.md`, `spec_output.json` | `domain_analysis.md`, `domain_output.json` |
| **Domain Modeller** | `domain_analysis.md`, `domain_output.json`, `spec.md` | `domain_model.md`, `domain_model.json` |
| **Designer** | `spec.md`, `domain_analysis.md`, `plan.md`?, `api_design.md`? | `design.md`, `design_system.tokens.json`, `design_output.json` |
| **Impl Planner** | `spec.md`, `spec_output.json`, `domain_analysis.md`, `domain_model.md`, `domain_model.json` | `plan.md`, `plan_output.json` |
| **Database Designer** | `plan.md`, `plan_output.json`, `spec.md`, `domain_analysis.md`, `domain_model.md`, `domain_model.json` | `schema_design.md`, `migrations/` |
| **API Designer** | `plan.md`, `plan_output.json`, `spec.md`, `domain_analysis.md`, `domain_model.md`, `domain_model.json` | `api_design.md`, `api_spec.yaml`, `api_design_output.json` |
| **SE (backend)** | `plan.md`, `plan_output.json`, `api_spec.yaml`, `schema_design.md`, `domain_model.md`?, `domain_model.json`? | *(source code)*, `se_{lang}_output.json` |
| **SE (frontend)** | `plan.md`, `plan_output.json`, `design.md`, `design_output.json`, `api_spec.yaml`, `domain_model.md`?, `domain_model.json`? | *(source code)*, `se_frontend_output.json` |
| **Observability** | `plan.md`, `plan_output.json` | *(dashboards, alerts)* |
| **Test Writer** | `plan.md`, `spec.md`, `domain_model.json`?, `domain_model.md`?, `se_{lang}_output.json`?, `se_frontend_output.json`? | *(test files)* |
| **Code Reviewer** | `plan.md`, `spec.md`, `domain_model.json`?, `domain_model.md`?, `design.md`?, `design_output.json`?, `se_{lang}_output.json`?, `se_frontend_output.json`? | *(review report — inline)* |
| **Content Reviewer** | agent/skill artifact, 2-3 referenced skills | `<audit-findings>` XML (inline) |
| **Freshness Auditor** | all `agents/*.md`, all `skills/*/SKILL.md` | `<audit-findings scope="library">` XML (inline) |
| **Consistency Checker** | all `agents/*.md`, all `skills/*/SKILL.md`, all `commands/*.md` | `<audit-findings scope="library">` XML (inline) |
| **DSS (via /options)** | `spec.md`, `domain_analysis.md`, `plan.md`?, `design.md`? | `dss_output.json` |
| **Architect** | `spec.md`, `domain_analysis.md`, `plan.md`? | *(architecture analysis — inline)* |
| **TDD Guide** | *(user query)* | *(TDD guidance — inline)* |
| **Build Resolver (Go)** | *(build error logs)* | *(code fixes — direct edits)* |
| **Doc Updater** | *(code changes)* | *(documentation file updates)* |
| **Database Reviewer** | `schema_design.md`, `migrations/` | *(review feedback — inline)* |
| **Refactor Cleaner** | *(source code)* | *(refactored code — direct edits)* |
| **All pipeline agents** | `progress/plan.json` | *(read only — TPM creates, Planner refines)* |
| **Each pipeline agent** | *(upstream artifacts)* | `progress/{agent}.json` |

`?` = optional, read if available.

**Rule**: When an agent's Step 1 lists files to check, it MUST match this table. If you add a new agent or artifact, update this table first.

**Fallback**: If a JSON file doesn't exist, fall back to the corresponding markdown file. Never fail because a JSON file is missing (see `structured-output` skill — Graceful Degradation Rule).

### Work Stream Handoffs

When the planner produces work streams, downstream agents consume them via `plan_output.json`:

1. **Orchestrator reads** `plan_output.json` → extracts `work_streams` and `parallelism_groups`
2. **For each parallelism group** (in order): launch all streams in the group concurrently
3. **Each stream's agent** receives its assigned `requirements` list as scope
4. **API contract is the handshake** — frontend streams depend on API contract completion, not backend implementation
5. **Schema before backend** — if a schema stream exists, it must complete before backend implementation begins

### DAG Execution Protocol

Phase 4 uses a Directed Acyclic Graph (DAG) instead of batch-gated phases. Each task node executes as soon as its specific dependencies are met — no waiting for unrelated streams.

#### Execution Model

```
BATCH-GATED (old):
[SE-be ‖ SE-fe] → wait ALL → [Test-be ‖ Test-fe] → wait ALL → Review

DAG-BASED (current):
Stream 1: SE-be → Test-be ──────────────────┐
              ↓ (BE done, FE still running)  │
         [launch cross-stream tasks]         ├──► Review → G4
                                             │
Stream 2: SE-fe ──────► Test-fe ─────────────┘
```

#### Schema Contracts

All execution state is schema-validated JSON, not text conventions:

| File | Schema | Validated By |
|------|--------|-------------|
| `execution_dag.json` | `schemas/execution_dag.schema.json` | `bin/validate-pipeline-output --dag-check` |
| `{stream}_completion.json` | `schemas/stream_completion.schema.json` | `bin/validate-pipeline-output --full` |
| `pipeline_state.json` | `schemas/pipeline_state.schema.json` | `bin/validate-pipeline-output --schema pipeline_state` |
| `progress/plan.json` | `schemas/progress_plan.schema.json` | `bin/validate-pipeline-output --progress-check` |
| `progress/{agent}.json` | `schemas/progress_agent.schema.json` | `bin/validate-pipeline-output --progress-check` |

#### Stream Executors

Each work stream runs as a single background Task (`general-purpose` agent) that chains agents internally:

1. SE agent → implementation
2. `git-safe-commit` → commit implementation
3. Test writer agent → tests
4. `git-safe-commit` → commit tests
5. Write `{stream}_completion.json` conforming to `stream_completion.schema.json`

Stream executors run in parallel. Within a stream, steps are sequential.

#### Validation Gates

After each stream completes, the orchestrator runs `bin/validate-pipeline-output --full`:

| Exit Code | Meaning | Retry Prompt |
|-----------|---------|-------------|
| 0 | All checks passed | — (advance DAG) |
| 1 | Schema validation failed | "Output JSON malformed. Required fields: ..." |
| 2 | Reality check failed | "Claimed files don't exist / git state mismatch" |
| 3 | Build check failed | "Code doesn't compile: {stderr}" |
| 4 | Test check failed | "Tests fail: {stderr}" |

Exit codes drive **targeted retry prompts** — the orchestrator doesn't interpret text, it branches on a number.

#### Retry Protocol

```
if exit_code != 0:
  node.attempt += 1
  if attempt > max_attempts (default: 2):
    ESCALATE to user with exit-code-specific error
  else:
    launch new agent with:
      "RETRY {N}/{max}. Previous failure (exit {code}): {error}.
       Check existing state. Continue from where previous agent stopped.
       Do NOT redo correct work. If same error recurs, return status: blocked."
```

#### Liveness Detection

For hung background tasks (TaskOutput never returns):
1. Check elapsed time against `timeout_minutes` in DAG node
2. Read output file — if content unchanged since last poll, declare hung
3. Fall back to checking `{stream}_completion.json` existence (bypasses TaskOutput bugs)
4. If truly hung: kill, increment attempt, retry

#### Reactive Cross-Stream Dispatch

When a stream completes early:
1. Orchestrator marks node `completed` in DAG
2. Scans all `pending` nodes: are any now unblocked (all deps completed)?
3. Launches newly-ready nodes immediately — even if other streams still running
4. Cross-stream tasks (integration tests, unified review) start as soon as their specific deps resolve

## Pipeline Mode

Agents operate in two modes depending on who invoked them:

| Mode | Invoked By | Flag | Behaviour |
|------|-----------|------|-----------|
| **Interactive** (default) | `/implement`, `/test`, `/review`, or direct user | `PIPELINE_MODE` absent | Talk to user, ask for confirmation |
| **Pipeline** | `/full-cycle` orchestrator via Task tool | `PIPELINE_MODE=true` in prompt | Return result to orchestrator, no prompts |

**Detection**: Check your invocation prompt for `PIPELINE_MODE=true`. If absent, default to interactive mode.

### Behaviour Differences

| Behaviour | Interactive | Pipeline |
|-----------|------------|----------|
| **Completion** | "Say 'continue'" → wait for user | Return structured result → done |
| **Tier 1 decisions** | Just do it | Just do it |
| **Tier 2 decisions** | Quick ask, then proceed | Decide autonomously, log in `autonomous_decisions` |
| **Tier 3 decisions** | Present options, wait for user | **Still escalates** — genuine blocker |
| **Model note** | Already on Opus (default); downgraded tasks show "say 'opus' to override" | Use the model assigned by orchestrator |
| **Structured output** | Optional | **Required** |
| **Approval validation** | Verify explicit user approval | Skip — orchestrator already has gate approval |

### Pipeline Completion Format

In pipeline mode, agents return a structured summary instead of asking the user:

```markdown
> <One-line summary of what was done>
>
> **Output**: `{stage}_output.json` written to `{PROJECT_DIR}/`
> **Status**: complete | partial | blocked
> **Blocking issues**: [none | list of issues requiring human input]
```

Only `blocked` status pauses the pipeline. `complete` and `partial` hand off to the next agent.

### Autonomous Decision Logging

In pipeline mode, Tier 2 decisions are logged in the agent's structured output under `autonomous_decisions`:

```json
{
  "autonomous_decisions": [
    {
      "tier": 2,
      "question": "Whether to use repository pattern or direct DB access",
      "decision": "Repository pattern",
      "rationale": "Codebase already uses repositories for other entities"
    }
  ]
}
```

The Code Reviewer audits these decisions. Wrong calls get caught in the review → fix loop, all within the autonomous G3→G4 phase.

### Why This Is Safe

In pipeline mode, the safety net is the **review cycle**, not human micro-approvals:
- SE makes Tier 2 decisions autonomously → Code Reviewer catches mistakes → fix loop corrects them
- All decisions are logged and auditable
- Tier 3 decisions (architecture, pattern selection, new abstractions) still escalate to the user
- The 4 strategic gates remain the human checkpoints

---

## Completion Output Format

### Interactive Mode (default)

When an agent completes its work and `PIPELINE_MODE` is NOT set:

```markdown
> <One-line summary of what was done>
>
> **Next**: Run `<next-agent>` to <action>.
>
> Say **'continue'** to proceed, or provide corrections.
```

#### Examples

**Software Engineer:**
```markdown
> Implementation complete. Created/modified X files.
>
> **Next**: Run `/test` to write tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Test Writer:**
```markdown
> Tests complete. X test cases covering Y scenarios.
>
> **Next**: Run `/review` to review implementation and tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**API Designer:**
```markdown
> API design complete. 4 resources, 12 endpoints defined.
>
> **Next**: Run `/implement` to begin backend implementation, or `/design` for UI/UX design.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Designer (UI/UX):**
```markdown
> Design specification complete. 8 components specified, 42 tokens defined.
>
> **Next**: Run `/implement` to have `software-engineer-frontend` implement from this spec.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Code Reviewer (issues found):**
```markdown
> Review complete. Found X blocking, Y important, Z optional issues.
>
> **Next**: Address blocking issues with `/implement`, then re-run `/review`.
>
> Say **'fix'** to have SE address issues, or provide specific instructions.
```

**Code Reviewer (approved):**
```markdown
> Review complete. No blocking issues found.
>
> **Next**: Ready to commit and create PR.
>
> Say **'commit'** to proceed, or provide corrections.
```

### Pipeline Mode

When `PIPELINE_MODE=true`, use the pipeline completion format (see above). Do NOT ask "Say 'continue'" — return your result and terminate.

---

## Escalation Rules

### Model Downgrade Notice (Opus → Sonnet)

**Interactive mode only.** In pipeline mode, use the model assigned by the orchestrator.

SE agents default to opus. When the `/implement` command auto-downgrades to sonnet for a simple task, it shows:

```markdown
Task looks straightforward (N files, ~M lines). Using Sonnet for speed. Say 'opus' to override.
```

Code reviewers and implementation planners always use opus — no downgrade logic applies.

### User Escalation

Stop and ask the user when (**in pipeline mode, only Tier 3**):

1. **Ambiguous requirements** — Multiple valid interpretations
2. **Trade-off decisions** — Significant impact either way
3. **Scope questions** — Unclear what's in/out of scope
4. **Blocking issues** — Cannot proceed without input

### How to Ask Questions

**CRITICAL: Ask ONE question at a time.** Never overwhelm with multiple questions.

**Format:**
```markdown
[Context]: Working on [X], encountered [situation].

Options:
A) [Option] — [trade-off]
B) [Option] — [trade-off]

Recommendation: [A/B] because [reason].

**[Awaiting your decision]**
```

**Example:**
```markdown
The `process_order` function can handle empty orders two ways:

A) Reject with ValidationError — Explicit, prevents downstream issues
B) Return empty result — Permissive, lets caller decide

Recommendation: A because empty orders indicate upstream bugs.

**[Awaiting your decision]**
```

## Approval Validation

Before implementation, agents must verify explicit approval exists.

### Valid Approval Phrases

- "yes", "yep", "y", "go ahead", "proceed", "do it"
- "approved", "looks good", "implement it"
- "option 1" / "option 2" (explicit choice)
- `/implement` command

### NOT Approval (Keep Waiting)

- "interesting", "I see", "okay" (acknowledgment)
- Follow-up questions
- "let me think about it"
- Silence

### Approval Check Format

```markdown
✓ Approval found: "[quote the approval phrase]"
Proceeding with implementation...
```

Or if not found:

```markdown
⚠️ **Approval Required**

This agent requires explicit user approval before implementation.

**To proceed**: Reply with "yes", "go ahead", or use `/implement`.
```

## Decision Classification

Classify decisions before acting:

| Tier | Type | Action |
|------|------|--------|
| 1 | Routine | Apply rule directly, no approval needed |
| 2 | Standard | Quick consideration, check precedent, proceed |
| 3 | Design | Full exploration (5-7 options), present to user |

### Tier 1 Examples (Just Do It)
- Apply formatting
- Fix style violations
- Remove narration comments
- Add missing type hints

### Tier 2 Examples (Quick Decision)
- Error message wording
- Variable naming (when domain clear)
- Small refactoring choices

### Tier 3 Examples (Present Options)
- Pattern/architecture selection
- API design choices
- New abstraction boundaries

## Stop Conditions

Every agent has boundaries. When you catch yourself crossing them, STOP.

**Common stop conditions:**
- Writing code when job is review → STOP, report issues only
- Modifying production code when job is testing → STOP, test as-is
- Adding features not in plan → STOP, ask about scope
- Implementing without approval → STOP, request approval

## Pipeline Gates

When using `/full-cycle`, the pipeline pauses at 4 strategic gates instead of after every agent. Agents run autonomously between gates.

| Gate | After | User Decides | Why |
|------|-------|-------------|-----|
| G1 | TPM + Domain Expert + Domain Modeller | "Is this the right problem and domain model?" | Wrong problem or model = wasted pipeline |
| G2 | Designer options | "Which design direction?" | UX is subjective |
| G3 | Design + API + Plan all ready | "Ready to implement?" | Last cheap exit |
| G4 | Code Review complete | "Ship it?" | Final quality check |

### Autonomous Execution Rules

- **Before G1**: Domain Expert + Domain Modeller run autonomously (sequential: expert then modeller)
- **Between G1 and G2**: Impl Planner + Designer run without pausing (parallel for UI features)
- **Between G2 and G3**: [Schema Designer ‖ API Designer] run without pausing (schema first if both needed)
- **Between G3 and G4**: Work-stream-driven execution — [SE-backend ‖ SE-frontend ‖ Observability] run based on parallelism groups from `plan_output.json`, then Tests + Review
- **Schema validation**: Runs automatically after every agent (no human gate)

### Backward Compatibility

Individual commands (`/implement`, `/test`, `/review`, etc.) keep their existing per-step approval behaviour. Gates **only** apply when using `/full-cycle`.

## Feedback Format

When reporting issues back to another agent or user:

```markdown
### 🔴 Must Fix (Blocking)
- [ ] `file.py:42` — **Issue**: <description>
  **Fix**: <conceptual fix, not code>

### 🟡 Should Fix (Important)
- [ ] `file.py:87` — **Issue**: <description>
  **Fix**: <conceptual fix>

### 🟢 Consider (Optional)
- [ ] `file.py:120` — **Suggestion**: <improvement idea>

### Summary
Review: X blocking | Y important | Z suggestions
Action: [Fix blocking and re-review] or [Ready to proceed]
```

---

## Progress Spine Protocol

File-based progress tracking that survives interruptions. Each agent updates its own status file; the orchestrator reads merged state.

### Architecture

```
Agent → bin/progress update → {PROJECT_DIR}/progress/{agent}.json (per-agent, no conflicts)
                                         ↓
Orchestrator → bin/progress view --json → merged progress
                                         ↓
Orchestrator → TaskCreate/TaskUpdate → user sees native task UI
```

### When to Update

| Event | Call |
|-------|------|
| Agent starts work on a milestone | `bin/progress update --project-dir $PROJECT_DIR --agent {name} --milestone {id} --status started --quiet` |
| Sub-deliverable completed (SE agents) | `bin/progress update --project-dir $PROJECT_DIR --agent {name} --milestone {id} --subtask {id} --status in_progress --summary "FR-001 done" --files "path/file.go" --quiet` |
| Agent completes milestone | `bin/progress update --project-dir $PROJECT_DIR --agent {name} --milestone {id} --status completed --summary "..." --quiet` |
| Agent blocked | `bin/progress update --project-dir $PROJECT_DIR --agent {name} --milestone {id} --status blocked --error "..." --quiet` |

### Rules

1. **Always use `--quiet`** — agents run in pipeline mode; stdout goes to orchestrator
2. **Graceful degradation** — append `|| true` so progress failures never block the agent's actual work
3. **Summaries under 100 chars** — these appear in `bin/progress view --format tree`
4. **One file per agent** — never write to another agent's progress file
5. **Orchestrator reads, agents write** — agents never call `bin/progress view`

### Resume Protocol (Interrupted Agent Recovery)

When an agent's progress file shows `status: "running"` (never completed), the orchestrator runs reconciliation before re-launching:

```bash
RESUME_JSON=$(~/.claude/bin/progress reconcile --project-dir "$PROJECT_DIR" --agent {name} --pre-sha "$PRE_SHA")
```

The reconciled JSON provides:

| Field | Resume Action |
|-------|--------------|
| `frs_completed: ["FR-001", "FR-002"]` | Skip these — already implemented |
| `frs_pending: ["FR-003", "FR-004"]` | Start from first pending FR |
| `has_uncommitted_work: true` | Review `git diff` before resuming — may contain partial FR-003 |
| `resume_hint` | Human-readable suggestion passed to the agent |

**Orchestrator passes to resumed agent:**

```
RESUME_CONTEXT=true
Completed FRs: FR-001, FR-002 (skip these — verified via git)
Uncommitted changes: {list of files from git diff}
Resume from: FR-003
Previous agent was interrupted. Check existing code before implementing.
Do NOT redo work that already exists and is correct.
```

**Three recovery scenarios:**

| Scenario | Reconcile Output | Agent Action |
|----------|-----------------|--------------|
| Interrupted early (no FRs done) | `frs_completed: []`, no uncommitted | Fresh start — implement all FRs |
| Interrupted mid-work (some FRs done) | `frs_completed: [...]`, maybe uncommitted | Skip completed FRs, review uncommitted, continue |
| Interrupted after all FRs (before output) | `frs_completed: [all]`, output file missing | Skip implementation, write output file |

**Rules:**
1. Orchestrator ALWAYS runs reconcile before re-launching an interrupted agent
2. Agent MUST check existing code (`git diff`, file reads) before implementing — never blindly redo
3. If `has_uncommitted_work` is true, agent reviews the diff first and decides: keep, fix, or discard
4. Reconcile is read-only — it never modifies progress files or git state

---

## Structured Handoff Protocol

When handing off between agents (especially during long sessions or after compaction), use structured JSON instead of free-text to preserve critical context.

### Handoff Schema

```json
{
  "handoff": {
    "from_agent": "string (agent name)",
    "to_agent": "string (target agent name)",
    "status": "complete | partial | blocked",
    "branch": "string (current git branch)",
    "files_modified": ["string (relative paths)"],
    "decisions_made": [
      { "question": "string", "decision": "string", "rationale": "string" }
    ],
    "blocking_issues": ["string (issues requiring resolution)"],
    "context_keys": {
      "jira_issue": "string",
      "plan_path": "string",
      "output_json": "string (path to structured output)"
    }
  }
}
```

### When to Use

| Situation | Use Structured Handoff? |
|-----------|------------------------|
| Agent-to-agent in pipeline mode | Yes — always |
| `/implement` → `/test` → `/review` chain | Yes — pass via prompt context |
| After context compaction | Yes — restore from `pre-compact-mask` output |
| Single-agent interactive session | No — free-text is fine |

### Compaction Survival

The `pre-compact-mask` hook (in `hooks.json`) automatically captures branch, modified files, and pipeline state before compaction. After compaction, the preserved context helps agents resume work without re-reading the entire codebase.

For multi-agent sessions, each agent should include `context_keys` in its completion output so the next agent can quickly locate all relevant artifacts without searching.
