---
tags: [claude-improvements, phase3, root-cause, layer-D]
phase: 3
rc-id: RC-21
layer: D
created: 2026-06-27
symptoms: [S-033, S-034]
---

# RC-21 — Each pipeline stage emits a monolithic markdown plus a JSON shadow

## Mechanism

The pipeline contract today is "each agent writes `X.md` plus `X_output.json`". The markdown is for humans; the JSON is for downstream agents. In practice both encode the same content, so each stage emits two walls of text saying the same thing in two formats. Worse, the markdown is a single monolithic file per stage — a 400-line spec, a 300-line domain analysis — even when natural sections (assumptions, evidence, decisions, open questions) would split cleanly into atomic files. This is layer-D (workflow output topology), not model verbosity — the agents emit monoliths because the templates and validators demand monoliths. The dual MD+JSON shadow is RC-21's most egregious case: pure duplication, structurally encoded in the pipeline.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-033]] (monolithic spec/domain), [[01-symptoms-inventory#S-034]] (`X.md` + `X_output.json` duplication)
- External: [[02-external-research#R3.1]] (Anthropic: "Provide concise, focused responses. Skip non-essential context."), [[02-external-research#R1.1]] (acknowledged "tendency to overengineer by creating extra files")
- Config gaps: [[03-current-config-map#3.2 Brevity / anti-graphomania (S-005, S-006, S-009, S-011, S-014, S-033)]] — no PostStop hook flags output > N lines

## Fix proposals (≥5)

### F1 — Stop hook flagging stage output exceeding line budget

- **Surface:** new bin script + hook registration
- **Effort:** low
- **Impact:** medium
- **Risk:** low — warning only, no forbid
- **Approach:** A Stop hook reads any `*.md` files modified in the session that are pipeline-stage outputs (matched by location/path convention) and emits `additionalContext` if any exceeds a per-stage budget (e.g. spec ≤ 200 lines, domain ≤ 150, plan ≤ 250).
- **Steps:**
  1. Create `bin/stop_stage_output_budget.py`.
  2. Define budgets in `schemas/stage_budgets.json`.
  3. Register under `Stop`.
  4. Optionally escalate to exit-2 after N warnings (configurable).
- **Touches/replaces:** `hooks.json`, new bin script, new schema.

### F2 — Merge `*.md` + `*_output.json` into single MD with frontmatter

- **Surface:** template + agent output spec
- **Effort:** medium
- **Impact:** high
- **Risk:** low
- **Approach:** Eliminate the duplication entirely. Each stage emits one markdown file whose frontmatter contains the structured fields (today's JSON) and whose body is the narrative. Validators read the frontmatter; downstream agents read the same file. `bin/validate-pipeline-output` adjusts to parse frontmatter.
- **Steps:**
  1. Update `templates/*` for spec/domain/plan/api-design/schema stages.
  2. Migrate JSON schemas from `schemas/*.schema.json` into frontmatter blocks.
  3. Update `bin/validate-pipeline-output` to read frontmatter.
  4. Add a one-shot migration helper to convert existing `*.md`+`*_output.json` pairs.
- **Touches/replaces:** `templates/`, `schemas/`, `bin/validate-pipeline-output`, agent definitions.

### F3 — Per-stage outputs split into atomic section files

- **Surface:** agent output spec + templates
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — more files; needs index
- **Approach:** Sections become files. A spec stage emits `assumptions.md`, `evidence.md`, `decisions.md`, `open-questions.md`, plus an `_index.md` linking them. Downstream agents (and humans) read only the sections they need. Reinforces RC-20's `assumptions.md` + `evidence.md` split.
- **Steps:**
  1. Update `templates/atomic-output/` with one file per canonical section.
  2. Update agent specs in `agents/technical_product_manager.md` etc. to emit per-section files.
  3. `_index.md` regenerated per stage by validator.
  4. `iterative-retrieval` skill referenced for downstream consumption.
- **Touches/replaces:** 5 agent definitions, `templates/`, `bin/validate-pipeline-output`.

### F4 — New output-style `atomic-emission`

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** A reusable output-style enforcing per-section file emission rules: max lines per file, max files per stage, mandatory frontmatter keys. Agents opt in via frontmatter `output_style: atomic-emission`.
- **Steps:**
  1. Create `output-styles/atomic-emission.md`.
  2. Spec rules: line cap per file, frontmatter schema, file naming.
  3. Reference from pipeline agents.
  4. Couple with F1 (Stop hook checks file counts and sizes).
- **Touches/replaces:** new output-style, 5 agent definitions add `output_style:` key.

### F5 — Agent-frontmatter cap on `tools:` for output-only stages (no-code)

- **Surface:** agent frontmatter
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** Pipeline agents that emit specifications (TPM, domain expert, planner) should have `tools:` restricted to `Read`, `Write`. No `Edit`, `MultiEdit`, `Bash`. This forces single-shot writes per file — multiple sections become multiple `Write` calls, naturally pushing toward atomic emission. Tightening `tools:` is a no-code structural fix.
- **Steps:**
  1. Audit each pipeline agent's current `tools:`.
  2. Remove `Edit`/`MultiEdit`/`Bash` where not strictly needed.
  3. Document the constraint in agent description.
  4. No new code; pure frontmatter change.
- **Touches/replaces:** ~5 agent frontmatter blocks.

## Acceptance signal

- For any pipeline run, average lines per emitted markdown file < 100 (down from typical 200-400).
- Zero `*_output.json` shadow files emitted after F2; validator passes on frontmatter-only inputs.
- Stage output directory has ≥3 atomic section files per stage, not one monolith.
- Stop hook flag rate trending to zero as agents adapt.
- Downstream agents (planner, code) `Read` only the section files they need — measurable as fewer-tokens-per-handoff.

## Trade-offs and counter-evidence

- F3 (atomic split) increases file count — risks "ls clutter" and harder navigation. Mitigated by `_index.md` and tool flag `Glob` works fine.
- F2 (MD+frontmatter) breaks any tooling that consumes `*_output.json` directly. Migration helper needed; one-time cost.
- F1 (budget hook) risks false positives on legitimately long stages (e.g. complex domain with many entities). Budgets must be data-driven, not arbitrary; set them via percentile of historical outputs.
- Anthropic guidance ([[02-external-research#R2.1]]) reverted a blunt ≤25/≤100 word cap after 3% eval drop. F1's caps must be at file/stage level (not per turn), and must be warnings before exits.
- F5 collides with agents that legitimately need `Edit` (e.g. updating `_index.md`). Carve-out: `Edit` allowed on `_index.md` only.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-033]]
- [[01-symptoms-inventory#S-034]]
- [[02-external-research#R3.1]]
- [[rc-13-claude-md-bloat]]
- [[rc-20-waterfall-pipeline]]
