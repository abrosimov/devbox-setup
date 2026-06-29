# Writer agent instructions — DO NOT DEPLOY, internal reference

This file is consumed only by Phase 3 writer agents. It defines the file template, tool discipline, and asset surface vocabulary.

## Tool discipline

USE ONLY: `Read`, `Write`.
DO NOT use: `Bash`, `Grep`, `Glob`, `Edit`, `AskUserQuestion`, `Task` (no nested subagents), `Skill`, `WebSearch`, `WebFetch`, `NotebookEdit`, anything else.

If you need to verify a path or skill exists, you may use `Read` once on the relevant file. Do NOT enumerate directories. If a path you would reference does not exist, write the fix WITHOUT verification — the user will validate.

## Per-RC file template

Output path: `/Users/kirillabrosimov/Projects/devbox-setup/claude_improvements/rc-NN-<slug>.md`

```markdown
---
tags: [claude-improvements, phase3, root-cause, layer-<A|B|C|D|E|F>]
phase: 3
rc-id: RC-NN
layer: <A|B|C|D|E|F>
created: 2026-06-27
symptoms: [S-XXX, S-YYY, ...]
---

# RC-NN — <Mechanism name as short sentence>

## Mechanism

One paragraph. What is the actual *cause* (not the symptom). Reference the level (model / harness / config / workflow / verification / process). Cite evidence from existing files: [[02-external-research#R1.2]], [[04-reflection-evidence#RC-ref-N]], etc.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-XXX]], …
- External: [[02-external-research#R<…>]], …
- Config gaps: [[03-current-config-map#<section>]]
- Reflection: [[04-reflection-evidence#RC-ref-N]] (if applicable)

## Fix proposals (≥5)

### F1 — <Short imperative name>

- **Surface:** {hook | skill | settings.json | agent-frontmatter | CLAUDE.md | new bin script | template | new agent | workflow.json | output-style | command}
- **Effort:** {low | medium | high}
- **Impact:** {low | medium | high}
- **Risk:** {low | medium | high} — and what it is
- **Approach:** 1-3 sentences describing the concrete change.
- **Steps:**
  1. Concrete action (file path, function name, setting key)
  2. Concrete action
  3. …
- **Touches/replaces:** existing assets (paths). Empty list if greenfield.

### F2 — <Short imperative name>
… (same shape)

### F3 — … (same)
### F4 — … (same)
### F5 — … (same)

## Acceptance signal

What downstream observation would prove this RC is mitigated? One bullet list, ≤5 items. Each item testable.

## Trade-offs and counter-evidence

If any fix has a known cost (e.g. evals dropping when brevity is forced — see [[02-external-research#R2.1]]), note it explicitly. Do not handwave.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- Adjacent RCs if causally linked: [[rc-XX-name]]
```

## Asset surface vocabulary

When proposing fixes, draw from this vocabulary. These are the levers available in this user's `dot_claude/` setup.

### Hooks (existing — extend or add new)

Located: `roles/devbox/files/dot_claude/bin/*.py`. Registered in `hooks.json`. Lifecycle:
- `PreToolUse` (matchers: `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`): exit-2 forbids the call.
- `PostToolUse`: runs after; can emit `additionalContext`.
- `UserPromptSubmit`: runs on user input; can inject `additionalContext`.
- `Stop`: runs at end of turn; can require re-run, gate output.
- `PreCompact`: runs before harness compacts context.
- `SessionEnd`, `WorktreeCreate`, `WorktreeRemove`: lifecycle.
- `PermissionRequest`: intercepts permission prompts.

Existing relevant hooks (do not propose duplicates):
- `pre_bash_safety_gate.py` — blocks destructive Bash.
- `pre_bash_toolchain_guard.py` — project-toolchain corrections.
- `pre_bash_boundary_wrap.py` — Bash shape discipline.
- `pre_tmpdir_guard.py` — TMPDIR enforcement.
- `pre_edit_lint_guard.py` — pre-edit lint check.
- `pre_plan_code_guard.py` — Plan-mode write block.
- `pre_write_existing_guard.py` — blocks Write to unread files.
- `pre_write_completion_gate.py` — completion gating on Write.
- `post_edit_lint.py`, `post_edit_typecheck.py`, `post_edit_cyrillic_guard.py`.
- `permission_auto_approve.py` — auto-approve safe commands.
- `proposal_discipline.py` — nudges delta-only iteration on UserPromptSubmit + Stop.
- `session_save.py` — PreCompact + SessionEnd persistence.
- `pre_compact_mask.py` — mask content before compaction.
- `stop_format.py`, `stop_lint_gate.py` — Stop gates.
- `suggest_checkpoint.py` — async PostToolUse nudge.
- `fpf_drift_check.py` — FPF drift detector.

### Skills (existing)

Located: `roles/devbox/files/dot_claude/skills/<name>/SKILL.md`. Frontmatter `alwaysApply: true|false`.

Relevant existing skills (40 total — full list in [[03-current-config-map#1. Inventory at a glance]]). Do not duplicate; you can extend or supersede:
- `agent-base-protocol`, `code-writing-protocols` — agent foundations.
- `fpf-thinking`, `diverge-synthesize-select`, `iterative-retrieval` — thinking patterns.
- `self-contained-options` — option-listing discipline.
- `code-comments` — comment policy.
- `lsp-navigation`, `lsp-tools`, `ast-grep` — code navigation.
- `project-preferences`, `project-toolchain`, `sandbox-toolchain` — project conventions.
- `techne-fewer-permission-prompts` — permission allowlist mining.
- `editing-claude-config` — meta: editing this very config.

### Agents (existing)

28 total. Per-agent frontmatter contains:
- `tools:` — explicit tool whitelist.
- `model:` — opus/sonnet/haiku.
- `description:` — when to invoke.

You can propose:
- Per-agent `tools:` tightening (smaller surface = fewer rogue actions).
- New agent (rare — add only if no existing agent fits).
- Per-agent reference to a new skill.

### settings.json

- `permissions.allow`, `permissions.deny`, `permissions.defaultMode`.
- `env.<KEY>` — `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` etc.
- `enabledPlugins`, `statusLine`, `sandbox`.

### CLAUDE.md (USER_AUTHORITY_PROTOCOL.md)

- Sections: Helpfulness Contract, Discipline Protocol, Voice, Proposal ≠ Approval, Stop Conditions, Self-checks, Git, Language, Code Projects.
- Currently 216 lines. Budget pressure (RC-13).

### bin/ helper scripts

You can propose new validators in `bin/` that hooks then call. Conventions: snake_case, `from _claude_lib import env, hooks`, single-purpose.

### Templates

`roles/devbox/files/dot_claude/templates/` — devcontainer template lives here. You can propose new templates (e.g. `facts-list.md`, `session-state.md`).

### output-styles

`roles/devbox/files/dot_claude/output-styles/` — exists. Output-style files alter response format. You can propose new styles (e.g. `delta-only`, `brevity-strict`).

### commands

`roles/devbox/files/dot_claude/commands/techne-*.md` — 23 slash commands. You can propose new commands (must be `techne-` prefixed).

### workflow.json (per-project)

Toggle for the mandatory-agent pipeline.

## Fix-proposal hygiene rules

1. **Each fix targets one surface.** Not "add hook AND skill AND CLAUDE.md edit" in one fix — split.
2. **At least 2 of the 5 fixes per RC must be deterministic.** A hook, a permission constraint, a tool whitelist tightening — not all advisory.
3. **At least 1 of the 5 fixes must be "no-code" (settings/CLAUDE.md/agent-frontmatter only).** Cheap and reversible.
4. **At most 1 fix can be a new skill.** Skills are advisory; don't pile them.
5. **If a fix has known counter-evidence** (e.g. Anthropic reverted ≤25/≤100 word caps — [[02-external-research#R2.1]]), note in trade-offs.
6. **No invented hook events.** Use the lifecycle events listed above. If a needed event does not exist, write the fix as "post-Stop validator triggered by Stop hook + state file" rather than inventing a new event.

## Numbering and slugs

- `rc-NN` zero-padded to 2 digits: `rc-01`, `rc-02`, …, `rc-30`.
- Slug: kebab-case, ≤5 words. Examples: `rc-01-rlhf-pushback-loop`, `rc-14-inter-asset-conflicts`.

## Wiki-link conventions (Obsidian)

- `[[01-symptoms-inventory#S-005]]` — cross-link to symptom.
- `[[02-external-research#R3.1]]` — cross-link to research sub-section.
- `[[rc-02-helpfulness-as-artefact]]` — cross-link to adjacent RC.
- `[[10-root-causes-overview]]` — back to overview.

## Style

- British English (per global language policy).
- Fact density. Numbers and identifiers over adjectives. No padding.
- Each RC file 100-200 lines. Compact.
- No emojis.
