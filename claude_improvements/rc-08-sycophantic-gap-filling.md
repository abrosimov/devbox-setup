---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-08
layer: A
created: 2026-06-27
symptoms: [S-012, S-013, S-029]
---

# RC-08 — Sycophantic gap-filling on terse feedback

## Mechanism

When the user supplies terse feedback ("X sounds wrong", "Spent sounds like wasted"), the model projects unstated broader dissatisfaction onto the user and pre-emptively rewrites more than the scope of the literal change. This is sycophancy disguised as thoroughness: the model assumes the user could not fully articulate what they wanted and "helpfully" extends scope ([[04-reflection-evidence#RC-ref-5]]). The mechanism is intrinsic to RLHF training — agreeableness gradients reward perceived helpfulness over literal precision. Mitigation requires deterministic scope-bounding around terse feedback turns: hook-level scope checks against user-named items, and per-agent system-prompt clauses forbidding unilateral scope extension.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-012]] (runs ahead, unsolicited initiatives), [[01-symptoms-inventory#S-013]] (reframes instead of clarifying), [[01-symptoms-inventory#S-029]] (no proactive 5-7 options when no call-to-action — defaults to action)
- External: [[02-external-research#R2.4]] (MindStudio: "executes a modified version of what you asked"), [[02-external-research#R2.3]] (GitHub #53459: "walks back proposals on the next turn without integrating the user's objection"), [[02-external-research#R1.2]] ("Claude Opus 4.8 interprets prompts literally and explicitly … does not silently generalize an instruction from one item to another, and it does not infer requests you didn't make" — Anthropic claims 4.8 fixes this; user is on 4.7 with severe symptoms)
- Config gaps: [[03-current-config-map#3.7]] (no turn-level scope-creep detector — hooks gate Write/Edit but not "ran 6 Bash commands for an investigation when only 1 file Read was asked")
- Reflection: [[04-reflection-evidence#RC-ref-5]] verbatim "Take terse feedback literally. 'Spent sounds like wasted' → change only the word 'Spent'."

## Fix proposals

### F1 — PreToolUse(Edit) hook checks edit scope against user-named items in last 2 user messages

- **Surface:** hook
- **Effort:** high
- **Impact:** high
- **Risk:** medium-high — needs robust named-item extraction; risk of blocking legitimate context-aware edits
- **Approach:** new `pre_edit_scope_guard.py` extracts user-mentioned identifiers from the last 2 user messages (file paths, function/class names from inline code-spans, quoted strings, line ranges). The hook computes the *named scope*: union of (files mentioned) × (line ranges mentioned OR identifier ranges). On each Edit/MultiEdit, if the target file is outside the named-scope set, exit 2 with `Edit target <path> not in user's named scope: {<scope>}. State scope-extension intent and request approval.`
- **Steps:**
  1. New `bin/pre_edit_scope_guard.py` — parse transcript, extract identifiers.
  2. Extraction patterns: inline-code via backticks, file paths via regex `[\w/\-.]+\.(go|py|ts|tsx|md|json|yaml)`, line refs `:\d+`.
  3. Scope match: target file path ∈ named files, OR target line range overlaps named lines.
  4. Allowlist override: user message contains "scope: refactor", "scope: rename across files", or `/techne-confirm-scope` invocation.
  5. Register on `PreToolUse` matching `Edit|MultiEdit`.
- **Touches/replaces:** `hooks.json`, new bin script. Complements `pre_write_existing_guard.py`.

### F2 — Per-agent system-prompt clause forbidding scope extension

- **Surface:** agent-frontmatter (deterministic via prompt injection)
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** add a one-line clause to the system prompt of every software-engineer agent (`software_engineer_go`, `software_engineer_python`, `software_engineer_frontend`, `refactor_cleaner`, `doc_updater`): `Terse user feedback is a scoped instruction, not a mood signal. If user says "X sounds wrong", change X only. If you believe more is wrong, ASK before extending scope.` Inserted just below the agent's role description so it sits in the high-attention prefix.
- **Steps:**
  1. Edit `agents/software_engineer_go.md`, `software_engineer_python.md`, `software_engineer_frontend.md`, `refactor_cleaner.md`, `doc_updater.md` — insert clause near top of system prompt.
  2. Cross-reference [[04-reflection-evidence#RC-ref-5]] in a code comment-style note.
  3. Re-run `make claude-push`.
- **Touches/replaces:** 5 agent files in `roles/devbox/files/dot_claude/agents/`.

### F3 — output-style requiring "diff scope statement" before multi-section edit

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** extend existing iteration output style (or new `literal-feedback.md`) to require that any turn touching more than one file or section emit a top-of-message `<diff_scope>` block: `<diff_scope>files: [a.go, b.py] sections: [a.go:42-58, b.py:101-107]</diff_scope>`. The block must be present before any tool call; absence reads as scope drift. Pairs with F1 hook for enforcement.
- **Steps:**
  1. New `roles/devbox/files/dot_claude/output-styles/literal-feedback.md` (or extend `iteration.md`).
  2. Define `<diff_scope>` schema and the rule: "If your diff scope exceeds the user's literally-named items, STOP and ask before proceeding."
  3. Optional Stop-hook validator can parse the block and check against subsequent tool-call targets (deferred — listed in trade-offs).
- **Touches/replaces:** new or extended output-style file.

### F4 — New command `/techne-confirm-scope`

- **Surface:** command
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** new command `commands/techne-confirm-scope.md` that the model invokes (or the user invokes) before any multi-file refactor. The command opens a single `AskUserQuestion` with: (a) "Files to touch:" (list), (b) "Identifiers to change:" (list), (c) "Out-of-scope items detected:" (list), and waits for confirmation. Sets a session-scoped allowlist that F1 hook respects until next prompt. The command name advertises the protocol so the model is prompted to use it.
- **Steps:**
  1. New `commands/techne-confirm-scope.md`.
  2. Body lists the three required items and uses `self-contained-options` skill format.
  3. Set `SCOPE_ALLOWLIST` token in session state file consumed by F1 hook.
  4. Cross-reference from `code-writing-protocols` skill.
- **Touches/replaces:** new command file, optional state-file convention.

### F5 — Skill `literal-feedback-scope` (new, advisory)

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** new skill `literal-feedback-scope` with `alwaysApply: true`, ~100 lines. Encodes: (a) terse = scoped, not mood; (b) "if more is wrong, ask"; (c) gives 3-4 examples of terse feedback and the correct minimal response; (d) explicit anti-pattern catalogue (extending to "consistency", "polish", "while I'm here"). Cross-references [[04-reflection-evidence#RC-ref-5]] verbatim and [[02-external-research#R1.2]] Anthropic 4.8 guidance.
- **Steps:**
  1. New `roles/devbox/files/dot_claude/skills/literal-feedback-scope/SKILL.md`.
  2. Frontmatter `alwaysApply: true`, description triggers on feedback verbs ("sounds", "feels", "looks").
  3. Cross-link from `agent-base-protocol § Voice` and `code-writing-protocols`.
- **Touches/replaces:** new skill.

## Acceptance signal

- Over 20 feedback turns, ≥ 90% of edits target only files named in the last 2 user messages.
- Zero unilateral multi-file refactors triggered by terse single-item feedback.
- F1 hook block-rate baseline measured; target < 5% false positives after first month tuning.
- When CTA is absent, ≥ 80% of agent responses propose 5-7 options instead of acting (S-029 target).
- Reduction in "but I also fixed X" pattern in agent self-reports (measurable via regex over Stop-hook captured output).

## Trade-offs and counter-evidence

- F1 (scope guard) risks false positives on legitimate context-aware edits (e.g. "fix this bug" implies touching imports + the bug site + a test). Mitigation: allowlist override token (`scope: extended` keyword in user message) and `/techne-confirm-scope` command.
- [[02-external-research#R1.2]]: Anthropic explicitly claims 4.8 "interprets prompts literally" and "does not infer requests you didn't make". If user upgrades from 4.7 to 4.8, RC-08 severity drops — but does not zero, because the trained gradient is shared across the 4.x family. The April-23 postmortem ([[02-external-research#R2.1]]) shows brittle defaults can be silently reverted at the Anthropic side; hook-level deterministic scope guards are insurance.
- F2 (per-agent clauses) adds attention budget pressure — see [[rc-11-claude-md-attention-budget]]. Mitigation: insertion at the high-attention prefix and one-line phrasing.
- F3 (`<diff_scope>` block) without F1 enforcement may itself become "preamble" that wastes tokens. [[02-external-research#R3.1]] caveat applies. Mitigation: only emit on multi-section edits.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- [[rc-07-asymmetric-ask-vs-guess]] (sibling: both reduce "produce artefact" gradient)
- [[rc-02-helpfulness-as-artefact]] (parent mechanism)
