---
tags: [claude-improvements, phase3, root-cause, layer-D]
phase: 3
rc-id: RC-20
layer: D
created: 2026-06-27
symptoms: [S-032, S-036]
---

# RC-20 — Pipeline forces horizontal waterfall; no re-entry after POC learning

## Mechanism

The agent pipeline cuts work into horizontal layers — full spec, then full domain analysis, then full plan, then code — with one-way gates between stages. Each `techne-*` command exits to its successor without a backedge: there is no `/techne-re-enter spec` or equivalent. The pipeline encodes the assumption that earlier-stage artefacts will not need revision once a later stage starts. Reality contradicts this: a POC produces empirical knowledge that invalidates spec assumptions. The current shape forces the user either to (a) start a new pipeline run from scratch (losing context), or (b) hand-edit the spec markdown and pretend later stages still match. Both fail. This is layer-D (workflow topology), not model behaviour — the model would happily revisit a spec if invited, but no asset invites it.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-032]] (waterfall), [[01-symptoms-inventory#S-036]] (no re-entry after POC)
- External: [[02-external-research#R3.3]] ("Explore → Plan → Execute. Human review gate between Plan and Execute, not between Explore and Plan."), [[02-external-research#R1.1]] ("Claude's latest models are extremely effective at discovering state from the local filesystem")
- Config gaps: [[03-current-config-map#1. Inventory at a glance]] (23 commands all forward-flow; no re-entry verb)
- Reflection: [[04-reflection-evidence#RC-ref-2]] (without working memory of confirmed facts, draft becomes source of truth — same shape applies at pipeline level)

## Fix proposals (≥5)

### F1 — New command `/techne-re-enter <stage>`

- **Surface:** command
- **Effort:** medium
- **Impact:** high
- **Risk:** low — opt-in, additive
- **Approach:** A command that opens any prior pipeline stage from later state. Loads the stage's artefacts, plus an evidence bundle from later stages (test outputs, POC observations) and prompts the corresponding agent to rewrite the assumptions section only — not the full artefact. Output is a delta-only patch to the original.
- **Steps:**
  1. Create `commands/techne-re-enter.md` taking `<stage>` arg.
  2. Stage list: `spec | domain | plan | api-design | schema`.
  3. Command loads `{stage}.md` + `{stage}_assumptions.md` (split via F3) and any `{PROJECT_DIR}/poc-evidence/*` artefacts.
  4. Dispatch to original stage's agent in iteration mode.
  5. Write back to `{stage}_assumptions.md`; leave `{stage}_evidence.md` untouched (now invalid → flag).
- **Touches/replaces:** new command, references in `techne-plan`/`techne-implement`.

### F2 — `workflow.json` mode `iterative` enabling POC-first

- **Surface:** workflow.json schema + per-project flag
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — changes default pipeline ordering
- **Approach:** Add a `mode: "iterative" | "waterfall"` flag to `workflow.json`. In `iterative` mode, `techne-implement` permits direct POC code without a prior plan, and post-POC artefacts feed back into spec via F1. In `waterfall` mode, current behaviour preserved.
- **Steps:**
  1. Extend `workflow.json` schema with `mode` enum.
  2. Update `techne-init-workflow` to ask mode at init.
  3. `techne-implement` checks mode and either enforces plan-first or permits POC-first.
  4. `techne-re-enter` only valid in `iterative` mode.
- **Touches/replaces:** `workflow.json` schema, `techne-init-workflow`, `techne-implement`.

### F3 — Split per-stage output into `assumptions.md` + `evidence.md`

- **Surface:** agent output templates
- **Effort:** medium
- **Impact:** high
- **Risk:** low
- **Approach:** Each pipeline stage today emits one monolithic markdown. Split into two atomic files: `{stage}_assumptions.md` (what we believed when we wrote this) and `{stage}_evidence.md` (what we learned). Re-entry (F1) rewrites only `assumptions.md`. Evidence stays as audit trail.
- **Steps:**
  1. Update `agents/technical_product_manager`, `domain_expert`, `domain_modeller`, `implementation_planner` output specs.
  2. Provide template `templates/atomic-output/assumptions.md` + `evidence.md`.
  3. Migrate existing `structured-output` skill JSON schemas.
  4. Update validators in `bin/validate-pipeline-output`.
- **Touches/replaces:** 4 agent definitions, `templates/`, `bin/validate-pipeline-output`.

### F4 — Command `/techne-checkpoint` saving pipeline state

- **Surface:** command + state file
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Snapshot the current pipeline state into `{PROJECT_DIR}/checkpoints/<timestamp>.json` — which stages exist, which are valid, which need re-entry. `/techne-next` consumes the latest checkpoint to suggest the next action. Re-entry updates it.
- **Steps:**
  1. Create `commands/techne-checkpoint.md`.
  2. State schema in `schemas/pipeline_checkpoint.schema.json`.
  3. `bin/progress` extended to read/write checkpoints.
  4. `techne-next` reads latest and reports.
- **Touches/replaces:** new command, `schemas/`, `bin/progress`.

### F5 — New skill `pipeline-re-entry`

- **Surface:** new skill (no-code)
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** Documents the protocol: when POC produces evidence contradicting spec, invoke `/techne-re-enter <stage>` rather than hand-editing. Referenced by `technical_product_manager`, `implementation_planner`, `software_engineer_*` agents.
- **Steps:**
  1. Create `skills/pipeline-re-entry/SKILL.md`.
  2. Describe trigger ("POC observation invalidates prior assumption"), action (`/techne-re-enter`), and bypass criteria (trivial typo fixes).
  3. Add `trigger_evals.json` with positive cases ("our assumption that X turned out wrong").
  4. Cross-reference from listed agents.
- **Touches/replaces:** 4 agent definitions add a `See also: pipeline-re-entry` line.

## Acceptance signal

- Sessions involving a POC complete with at least one `/techne-re-enter` invocation when the POC contradicts a prior assumption (eval on past sessions).
- Spec/plan artefacts split into `assumptions.md`+`evidence.md` for ≥1 project; downstream agents read only `assumptions.md` on re-entry.
- Average lines-rewritten on re-entry < 30 (delta-only, not full rewrite).
- No user complaint of "had to restart pipeline from scratch" for ≥1 month.
- `workflow.json` mode `iterative` adopted in ≥1 active project.

## Trade-offs and counter-evidence

- F1+F2 expand pipeline surface area; conflicts with the brevity/simplicity bias (RC-21 says we already have too many monolithic outputs). Mitigated because re-entry is opt-in and produces deltas, not new monoliths.
- F3 doubles file count per stage. Risks `ls` clutter and triggers RC-21 symptoms ("too many files"). Counter: each file is shorter, scoped, and the split is exactly the split RC-21 recommends.
- F2's `iterative` mode permits skipping spec — collides with `code-writing-protocols` mandate for "approval first". Resolution: iterative mode requires an explicit user "POC mode" token (an approval-class trigger) before bypass.
- Anthropic guidance ([[02-external-research#R1.1]]) says fresh sessions beat compaction. F4 checkpoint files support that: resume into a fresh session, do not compact-and-continue.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-032]]
- [[01-symptoms-inventory#S-036]]
- [[02-external-research#R3.3]]
- [[rc-21-monolithic-and-duplicate-outputs]]
- [[rc-22-manual-dispatch-no-roadmap]]
