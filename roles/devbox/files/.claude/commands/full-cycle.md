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

**Compute Task Context (once)**:
```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to all agents throughout the cycle.

**Detect project language**:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user

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
    "api_designer": { "status": "pending", "output": "api_design.md", "approved_at": null },
    "software_engineer": { "status": "pending", "approved_at": null },
    "test_writer": { "status": "pending", "approved_at": null },
    "code_reviewer": { "status": "pending", "approved_at": null }
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
2. Check if project has frontend code (`*.tsx`, `*.vue`, `*.svelte`, `*.jsx`)
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

### Phase 3: API Design + Final Check (autonomous → Gate 3)

1. Run `api-designer` agent → produces `api_design.md` + spec files
2. Update pipeline state: `api_designer.status = "completed"`

**GATE 3** — "Ready to implement?"

Present summary of all planning artifacts. Update `current_gate = "G3"`.

> **Gate 3: Implementation Readiness**
>
> All planning artifacts complete:
> - Spec: `spec.md` [summary]
> - Domain: `domain_analysis.md` [summary]
> - Plan: `plan.md` [N functional requirements]
> - Design: `design.md` [N components, M tokens] (if applicable)
> - API: `api_design.md` [N resources, M endpoints]
>
> **[Awaiting your decision]** — Approve to start implementation, or provide corrections.

Record decision in `decisions.json`. On approval, update `current_gate = "none"`.

### Phase 4: Implementation Cycle (autonomous → Gate 4)

1. Run `software-engineer-{lang}` agent → implements feature
2. Update pipeline state: `software_engineer.status = "completed"`
3. Run `unit-test-writer-{lang}` agent → writes tests
4. Run tests to verify they pass
5. Update pipeline state: `test_writer.status = "completed"`
6. Run `code-reviewer-{lang}` agent → reviews implementation
7. Update pipeline state: `code_reviewer.status = "completed"`

**If reviewer finds blocking issues:**
- Run SE agent with review feedback (fix loop)
- Re-run tests
- Re-run review
- Repeat until clean

**GATE 4** — "Ship it?"

Update `current_gate = "G4"`.

> **Gate 4: Ship Decision**
>
> Implementation complete. Review passed with no blocking issues.
> - [Summary of changes: N files modified, M tests written]
> - [Review result: X blocking (fixed) | Y important | Z suggestions]
>
> **[Awaiting your decision]** — Say **'commit'** to create commit, **'done'** to finish without commit, or provide corrections.

Record decision in `decisions.json`.

## User Commands (Available at Any Gate)

| Command | Action |
|---------|--------|
| `continue` / `approve` | Proceed past current gate |
| `option A/B/C` | Select a design option (Gate 2) |
| `fix <instruction>` | Apply specific correction before continuing |
| `skip` | Skip current phase, move to next gate |
| `stop` | End workflow entirely |
| `back` | Return to previous gate |
| `commit` | Create commit (Gate 4) |
| `done` | Finish without commit (Gate 4) |

## Notes

- The pipeline pauses only at 4 strategic gates, not after every agent
- Agents run autonomously between gates
- Individual commands (`/implement`, `/test`, `/review`) still use per-step approval
- Pipeline state persists in `pipeline_state.json` — resume with `/full-cycle` if interrupted
- Decisions are logged in `decisions.json` for audit trail
- Use `stop` at any time to exit
