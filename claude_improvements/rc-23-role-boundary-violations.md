---
tags: [claude-improvements, phase3, root-cause, layer-D]
phase: 3
rc-id: RC-23
layer: D
created: 2026-06-27
symptoms: [S-037, S-038]
---

# RC-23 — Agents decide and read outside their role scope; no hook enforces per-agent boundaries

## Mechanism

Each agent has a frontmatter `description` declaring its lane (TPM = product reasoning; designer = UX; SE = code) but the runtime treats the lane as advisory. The TPM agent reads source code directly even though its mandate explicitly says "translate to TPM-level language through SE handoff" ([[01-symptoms-inventory#S-037]]). The TPM + designer jointly declared an issue "frontend-only" ([[01-symptoms-inventory#S-038]]) — a scoping decision that belongs to architecture, not product/UX. The root cause is twofold: (a) `tools:` whitelists are too permissive (most agents can `Read` any file, so the TPM happily opens `.go`/`.py`), and (b) no PreToolUse hook checks the agent's identity against the file extension or decision class being touched. This is layer-D (workflow). Lane discipline lives only in description prose, which models drop under attention pressure (RC-11/RC-13).

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-037]] (TPM reads code), [[01-symptoms-inventory#S-038]] (out-of-scope "frontend-only" declaration)
- External: [[02-external-research#R3.3]] ("Subagents preserve the quality of the context that already exists" — implies scope-tight handoffs), [[02-external-research#R3.2]] ("Hooks for 100% enforcement. CLAUDE.md is advisory")
- Config gaps: [[03-current-config-map#3.7 Initiative creep / unsolicited reframing (S-012, S-013, S-029, S-037, S-038)]] — "Agents have per-role tools: and scoped responsibilities... [but] hook gate Write/Edit but not [scope creep]"
- Reflection: [[04-reflection-evidence#RC-ref-5]] (sycophantic gap-filling — agent extends scope beyond what was asked)

## Fix proposals (≥5)

### F1 — Per-agent `tools:` constraint tightening (no-code, frontmatter only)

- **Surface:** agent frontmatter
- **Effort:** low
- **Impact:** high
- **Risk:** low
- **Approach:** Tighten `tools:` on each non-SE agent. TPM gets `Read`+`Write`+`AskUserQuestion` only — no `Edit`, no `Bash`. Domain expert same. Designer gets `Read`+`Write`+`AskUserQuestion`+`mcp__figma__*`. Code reading is still possible (Read works) but code modification requires SE handoff. This is the cheapest, most reversible structural fix.
- **Steps:**
  1. Audit all 28 agents' `tools:` lists.
  2. For each non-engineer agent, restrict to `Read`+`Write`+`AskUserQuestion`+role-specific MCP tools.
  3. Document the carve-outs in agent description.
  4. Update `agent-base-protocol` skill to reference the new convention.
- **Touches/replaces:** ~15 agent frontmatter blocks.

### F2 — PreToolUse hook checking agent identity vs file extension

- **Surface:** new bin script + hook registration
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives if agent legitimately needs to Read code
- **Approach:** A PreToolUse(Read|Edit|Write|MultiEdit) hook reads `$CLAUDE_AGENT_NAME` (or transcript-derived identity), looks up an allow-table of `agent → file-extension globs`, and exits 2 if mismatch. TPM cannot Read `*.go|*.py|*.ts`. SE cannot Write `*.md` outside `docs/`/`progress/`/`memory/`.
- **Steps:**
  1. Create `bin/pre_tool_agent_scope_guard.py`.
  2. Define allow-table in `schemas/agent_scope.json`.
  3. Identity from agent context (transcript or env).
  4. Register under `PreToolUse(Read|Edit|Write|MultiEdit)`.
  5. Escalate env var for emergency override.
- **Touches/replaces:** `hooks.json`, new bin, new schema.

### F3 — Per-agent role-boundary skill referenced from frontmatter

- **Surface:** new skill (no new code)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** A single skill `role-boundary` enumerating each agent's mandate and forbidden actions. TPM section: "you do not read code; you commission SE handoffs." Designer section: same. Architect section: "you do scope decisions; TPM does not." All agents add `role-boundary` to their always-loaded set.
- **Steps:**
  1. Create `skills/role-boundary/SKILL.md` enumerating each agent.
  2. Each section has positive ("you do") and negative ("you do not") lists.
  3. Reference from agent description.
  4. Add `trigger_evals.json` with "TPM reads code" → SKILL match.
- **Touches/replaces:** new skill, ~10 agent descriptions add reference.

### F4 — Output-style requiring agent to declare scope before acting

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** A reusable output-style `scope-first` that every non-SE agent uses. The agent's first emission is a one-line scope declaration: `Scope: TPM — product reasoning; will not modify code or declare layer-localised solutions.` Forces explicit ownership of lane on every turn.
- **Steps:**
  1. Create `output-styles/scope-first.md`.
  2. Template: `Scope: <agent-name> — <one-line mandate>; will not <forbidden classes>.`
  3. Reference from each non-SE agent.
  4. Couple with F2 — hook checks for declaration in transcript.
- **Touches/replaces:** new output-style, ~10 agent frontmatter blocks.

### F5 — Command `/techne-scope-check` audit

- **Surface:** command
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** A diagnostic command run after a multi-agent session to audit each agent's tool-call history against its lane. Reports violations: "TPM agent Read `src/api.go` at turn 4 — out of scope". Useful in code review of the workflow itself.
- **Steps:**
  1. Create `commands/techne-scope-check.md`.
  2. Read transcript and agent identity per turn.
  3. Cross-check against `schemas/agent_scope.json` (same as F2).
  4. Output violation list with line numbers.
- **Touches/replaces:** new command; shares schema with F2.

## Acceptance signal

- TPM agent zero `Read` calls on `*.go|*.py|*.ts|*.tsx` files over a one-week sample.
- `/techne-scope-check` reports zero violations on closed sessions.
- F2 hook exit-2 rate trending to zero as agents adapt.
- "Frontend-only" style scope declarations from TPM disappear from session logs.
- Each non-SE agent's first emission per turn matches the `scope-first` output-style.

## Trade-offs and counter-evidence

- F1 (no Edit for TPM) may break legitimate workflows where TPM updates own `roadmap.md`. Carve-out: TPM keeps `Write` (single-shot file emission), not `Edit` (in-place modify). Re-emit instead of in-place edit on roadmap updates.
- F2 is deterministic but the agent-identity signal is fragile in nested-Task scenarios. The fallback when identity is unknown is "permit + log" (not "forbid + log"), to avoid breaking sessions on hook misdetection.
- F3 (role-boundary skill) bloats context if always-applied across all agents. Per-agent inclusion only — each agent loads role-boundary's section for itself plus a one-line summary of others.
- Anthropic guidance ([[02-external-research#R1.1]]) flags 4.7/4.8 as more literal followers — explicit lane declarations work better than implicit. F1+F4 leverage this.
- F4 collides with brevity (RC-12, RC-21) — one extra line per turn. Acceptable; explicitly anti-graphomania output-style would not have this line, so opt-in only on non-SE agents.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-037]]
- [[01-symptoms-inventory#S-038]]
- [[02-external-research#R3.2]]
- [[rc-19-skill-invocation-advisory]]
- [[rc-22-manual-dispatch-no-roadmap]]
