---
tags: [claude-improvements, phase3, root-cause, layer-D]
phase: 3
rc-id: RC-22
layer: D
created: 2026-06-27
symptoms: [S-035, S-039]
---

# RC-22 — Manual stage dispatch with no parallelism; no roadmap or milestone tracking

## Mechanism

The pipeline is invoked one stage at a time by the user typing `/techne-domain-analysis`, then `/techne-plan`, then `/techne-api-design`. Each invocation is sequential and synchronous even when stages are causally independent (e.g. API design and schema design can run in parallel for a given spec). Worse, there is no longer-horizon spine: no roadmap file, no milestone tracking, no notion of "where are we in the project as a whole". The user holds the project-level state in their head; the harness sees one task at a time. This is layer-D (workflow topology). The asset gap is two-fold: (a) no DAG-aware dispatcher, (b) no project-level state file consumed by `techne-next` / statusline / planner agents.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-035]] (manual dispatch), [[01-symptoms-inventory#S-039]] (no roadmaps/milestones)
- External: [[02-external-research#R3.3]] ("Subagents preserve the quality of the context that already exists"), [[02-external-research#R1.1]] (Anthropic acknowledges 4.6 over-spawns, 4.7/4.8 under-spawn — parallelism needs explicit invitation)
- Config gaps: [[03-current-config-map#1. Inventory at a glance]] — `techne-next` exists but reads no roadmap; `bin/progress` manages milestones but no project-level view

## Fix proposals (≥5)

### F1 — New command `/techne-dag` running independent stages in parallel

- **Surface:** command
- **Effort:** high
- **Impact:** high
- **Risk:** medium — coordination errors if dependencies misdeclared
- **Approach:** A command that reads a stage DAG (from `schemas/execution_dag.schema.json` — already exists per CLAUDE.md mentioning `bin/validate-pipeline-output --progress-check`), identifies independent stages, and dispatches them concurrently via background `Task` agents. Joins on completion. Sequential stages remain sequential.
- **Steps:**
  1. Create `commands/techne-dag.md`.
  2. Read execution DAG from `{PROJECT_DIR}/progress/execution-dag.json`.
  3. For each ready-set in DAG, spawn `Task` agents in parallel.
  4. Wait on all, then advance.
  5. Update `progress/agent-status/*.json` per agent.
- **Touches/replaces:** new command, `schemas/execution_dag.schema.json`, `bin/progress`.

### F2 — Project-level `roadmap.md` template + skill

- **Surface:** template + new skill
- **Effort:** medium
- **Impact:** high
- **Risk:** low
- **Approach:** A roadmap template `templates/project/roadmap.md` with sections for milestones, current focus, blocking items. Bootstrapped by `techne-init-workflow`. A new skill `pipeline-roadmap` documents the format and is referenced by `technical_product_manager` and `implementation_planner` agents — they update the roadmap each stage.
- **Steps:**
  1. Create `templates/project/roadmap.md`.
  2. Create `skills/pipeline-roadmap/SKILL.md`.
  3. `techne-init-workflow` copies template on project init.
  4. TPM + planner agents reference skill; update roadmap on stage completion.
  5. `techne-next` reads roadmap to suggest next focus.
- **Touches/replaces:** `templates/`, new skill, `techne-init-workflow`, `technical_product_manager`, `implementation_planner` agents.

### F3 — Command `/techne-milestone` for milestone progress dump

- **Surface:** command
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Reads `roadmap.md` + `progress/` directory and prints current milestone, percent-complete, blocking items, recent commits. Pure aggregation; no state writes.
- **Steps:**
  1. Create `commands/techne-milestone.md`.
  2. Aggregate roadmap milestones, progress agent-status files, git log since last milestone.
  3. Output: milestone name, % done, next action, blockers.
  4. Reference from `techne-next`.
- **Touches/replaces:** new command, references `bin/progress`.

### F4 — Statusline showing roadmap progress (no-code config)

- **Surface:** settings.json `statusLine`
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** Extend the statusline to show current milestone + progress fraction (e.g. `milestone: api-design 3/5`). Reads roadmap and progress files via a shell snippet. Pure settings change, no behavioural code.
- **Steps:**
  1. Edit `settings.json` `statusLine` to call a helper `bin/statusline_milestone.py`.
  2. Helper reads `{PROJECT_DIR}/roadmap.md` + `progress/`.
  3. Outputs short string.
  4. No-code from a behaviour standpoint.
- **Touches/replaces:** `settings.json`, new `bin/statusline_milestone.py`.

### F5 — TPM + planner agent frontmatter mandates roadmap read on dispatch (no-code)

- **Surface:** agent frontmatter
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Add to `technical_product_manager` and `implementation_planner` description: "Always Read `{PROJECT_DIR}/roadmap.md` before generating output. If absent, halt and instruct the user to run `/techne-init-workflow`." A no-code structural constraint that prevents agents producing stage-level output without project-level context.
- **Steps:**
  1. Edit `agents/technical_product_manager.md` description.
  2. Same for `agents/implementation_planner.md`.
  3. Add to `tools:` only `Read`+`Write` (already covered by RC-23 F5).
  4. Frontmatter-only change.
- **Touches/replaces:** 2 agent frontmatter blocks.

## Acceptance signal

- For projects with `roadmap.md`, `techne-next` cites a roadmap milestone in its suggestion ≥90% of sessions.
- DAG-parallel stages (e.g. api-design + schema) complete in wall-clock time noticeably less than sum-of-parts.
- Statusline shows non-empty milestone string in active projects.
- Zero "what should I work on next" prompts requiring user to dig through `progress/` manually.
- New projects bootstrap with a `roadmap.md` automatically.

## Trade-offs and counter-evidence

- F1 (DAG dispatch) risks subagent spawn-storms. 4.6 over-spawned, 4.7/4.8 under-spawn ([[02-external-research#R1.2]]) — the parallel command must cap fan-out (e.g. ≤3 concurrent agents) and require explicit user invocation.
- F2's roadmap.md adds another file to every project — extends RC-21's "more files" concern. Mitigated because roadmap is project-level (one file) not per-stage.
- F4 (statusline) burns ~50-100 chars of every prompt header. Negligible vs the value of always-visible state.
- F5 risks blocking work on projects that never adopted roadmaps. Mitigated by the "halt and instruct" path — not a hard forbid, just a nudge to bootstrap.
- Anthropic [[02-external-research#R1.1]] notes 4.6 subagent overuse. F1's parallel dispatch must be opt-in (user types `/techne-dag`), not the default for `/techne-implement`.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-035]]
- [[01-symptoms-inventory#S-039]]
- [[02-external-research#R3.3]]
- [[rc-20-waterfall-pipeline]]
- [[rc-23-role-boundary-violations]]
