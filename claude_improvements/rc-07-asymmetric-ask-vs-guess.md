---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-07
layer: A
created: 2026-06-27
symptoms: [S-007, S-015, S-016]
---

# RC-07 — Asymmetric perceived cost of asking vs guessing

## Mechanism

Asking a question feels to the model like admitting incompetence and stalling the turn — no artefact is produced, so the turn looks empty. Guessing feels like momentum: a draft appears, tokens flow, the gradient toward "produce a complete artefact" is satisfied. Over RLHF training, this asymmetry hardens into a strong prior for inference-over-inquiry, even when the system prompt explicitly inverts it ([[04-reflection-evidence#RC-ref-3]]). The mechanism is *intrinsic to weights* (Layer A): mitigations operate by making question-turns visibly successful via wrapping, scoring, or hook-level reframing, and by blocking action when the user's last message ended in a `?`.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-007]] (asks too early, not batched), [[01-symptoms-inventory#S-015]] (random unsupported assumptions), [[01-symptoms-inventory#S-016]] (rushes to solve before data)
- External: [[02-external-research#R1.1]] (Anthropic `<investigate_before_answering>` and `<do_not_act_before_instructions>` snippets — official acknowledgement that reconnaissance-before-action must be promptable), [[02-external-research#R5]] item 8
- Config gaps: [[03-current-config-map#3.3]] (premature action — `pre_plan_code_guard.py` covers Write/Edit but not "agent emitted final answer without doing a single Read first"), [[03-current-config-map#3.4]] (inquiry rule is advisory — agent-base-protocol conflict with USER_AUTHORITY_PROTOCOL on batched vs one-at-a-time)
- Reflection: [[04-reflection-evidence#RC-ref-3]] verbatim "Asking a question feels like admitting incompetence and stalling the turn"

## Fix proposals

### F1 — UserPromptSubmit hook injects "Reconnaissance turn" reframe token

- **Surface:** hook (extend or new bin script)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — wrong heuristic might fire on follow-ups that legitimately need an artefact
- **Approach:** add a `UserPromptSubmit` hook step that detects non-trivial prompts (length ≥ 80 chars, contains code/file path identifiers, or starts with a verb like "implement"/"refactor"/"design"). When detected, inject `additionalContext` of the form: `[Reconnaissance turn] A turn that produces only a Disclosure block + batched questions is a SUCCESS state. Producing an artefact this turn without prior approval is the FAILURE state.` This makes question-turns visibly rewarded inside the prompt the model sees.
- **Steps:**
  1. New `bin/user_prompt_reconnaissance_reframe.py` triggered from existing `UserPromptSubmit` chain (alongside `proposal_discipline.py`).
  2. Detection heuristic: regex over user message — flags presence of file paths (`[\w/]+\.(go|py|ts|tsx|md)`), imperative verbs at sentence start, length threshold.
  3. Emit `additionalContext` token `[Reconnaissance turn]` plus the success/failure framing.
  4. Register in `hooks.json` under `UserPromptSubmit`.
- **Touches/replaces:** `roles/devbox/files/dot_claude/hooks.json`, new bin script. Adjacent to existing `proposal_discipline.py`.

### F2 — PreToolUse(Edit|Write|Bash) hook blocks action when last user message ended with `?` and no approval token

- **Surface:** hook
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives on rhetorical questions; needs allowlist for trivial reads
- **Approach:** new `pre_action_after_question_guard.py` reads the last user message from the transcript; if it ends with `?` (after trimming code blocks) AND there is no approval token ("yes", "go ahead", "proceed", "do it", "approved", "option N", "/techne-implement") in any subsequent user message, exit 2 with a message: `Last user turn was a question. Answer the question before taking action.` Exempt: Read, Glob, Grep, LS (pure reconnaissance).
- **Steps:**
  1. New `bin/pre_action_after_question_guard.py` — read transcript file, scan user messages.
  2. Token list: reuse the approval allowlist from [[03-current-config-map#§ What Counts as Approval]].
  3. Apply matcher to `PreToolUse` for `Edit`, `Write`, `MultiEdit`, `Bash` (but skip if Bash command is in reconnaissance allowlist: `ls`, `cat`, `pwd`, `git status|log|diff|show`).
  4. Register in `hooks.json`.
- **Touches/replaces:** `hooks.json`, new bin script. Complements `pre_plan_code_guard.py` (which only covers Plan mode).

### F3 — output-style awarding rhetorical credit to question-only turns

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** new output-style `inquiry-first.md` that defines a turn-template where the assistant's response begins with a `<turn_type>` tag — either `<turn_type>recon</turn_type>` (Disclosure block + AskUserQuestion only) or `<turn_type>artefact</turn_type>` (any tool call producing an edit/write/commit). The style asserts: "A `recon` turn is a successful turn. Producing an `artefact` turn without an approval token in the prior 2 user messages is a failure." User opts in by setting it as default style for their profile.
- **Steps:**
  1. New file `roles/devbox/files/dot_claude/output-styles/inquiry-first.md`.
  2. Define the `<turn_type>` schema and the success/failure mapping.
  3. Document in `00-MoC` and reference from `USER_AUTHORITY_PROTOCOL.md § Discipline Protocol`.
- **Touches/replaces:** new output-style file. Optional opt-in.

### F4 — settings.json `defaultMode: plan` bias

- **Surface:** settings.json
- **Effort:** low
- **Impact:** medium
- **Risk:** medium — every new session opens in plan mode; user friction if not desired
- **Approach:** set `permissions.defaultMode` to `plan` in deployed `~/.claude/settings.json`. Plan mode is the harness-enforced read-only gate ([[02-external-research#R3.2]]); it deterministically prevents Edit/Write/destructive Bash until the user types `/exit_plan_mode` or accepts the plan. This collapses the ask-vs-guess asymmetry at the platform level — guessing produces no artefact because the harness forbids it.
- **Steps:**
  1. Edit `roles/devbox/files/dot_claude/settings.json` → set `permissions.defaultMode: "plan"`.
  2. Document in `dot_claude/README.md` (deployed as `~/.claude/README.md`).
  3. Provide opt-out via `claude --permission-mode default` or `/permission-mode default`.
- **Touches/replaces:** `roles/devbox/files/dot_claude/settings.json`.

### F5 — Skill `question-as-deliverable` (new, advisory)

- **Surface:** new skill
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low — advisory only; advisory rules already at ~70% adherence
- **Approach:** new skill `question-as-deliverable` with `alwaysApply: true` frontmatter, ~80 lines. Encodes the rule: "A turn producing only a Disclosure block + batched AskUserQuestion is the canonical success state for non-trivial requests. Inferred-intent artefacts without approval are failures even when technically correct. Include a one-line self-audit at end of every recon turn: `Recon: <N> questions batched, <0> artefacts emitted.`" References [[02-external-research#R1.1]] Anthropic `<do_not_act_before_instructions>` snippet.
- **Steps:**
  1. New `roles/devbox/files/dot_claude/skills/question-as-deliverable/SKILL.md`.
  2. Frontmatter `alwaysApply: true`, description triggers on imperative/design/architect verbs.
  3. Cross-link from `agent-base-protocol § When to Ask` and `code-writing-protocols § Approval Validation`.
- **Touches/replaces:** new skill. Cross-refs in existing skills.

## Acceptance signal

- Over 20 non-trivial sessions, ≥ 80% of first replies contain a Disclosure block.
- Zero Edit/Write tool calls occur in a turn where the prior user message ended with `?` and no approval token follows.
- Median count of files Read before first Edit ≥ 4 (vs Stella Laurenzo baseline 2.0 — [[02-external-research#R2.2]]).
- Sessions opened in `plan` mode complete planning artefact before any code mutation in ≥ 90% of cases.
- Telemetry hook logs ratio of `recon` turns to `artefact` turns; baseline measured, target ≥ 1:1 for design-class tasks.

## Trade-offs and counter-evidence

- F2 (block-after-question) will misfire on rhetorical questions ("Should we use Redis here? Probably not, because…"). Mitigation: heuristic exempts questions answered within the same user turn (presence of "Probably", "I think", "Likely" within ±3 sentences).
- F4 (`defaultMode: plan`) trades opening friction for safety. [[02-external-research#R3.2]] supports plan mode but practitioner consensus is that always-on plan mode causes drop-out for trivial tasks. Mitigation: pair with `/permission-mode default` toggle and document the toggle in the auto-injected first-session message.
- F3 + F5 are advisory; [[02-external-research#R3.1]] notes "Semantic eval confirms baselines on current models already exhibit 0% preamble … rules targeting those behaviors carry input cost without changing output." This RC mitigation runs the same risk if advisory only — hence F1, F2 carry the deterministic weight.
- Counter-evidence on `<do_not_act_before_instructions>` ([[02-external-research#R1.1]]): the snippet works at session start but model attention to it decays as context fills (per Lost-in-the-Middle [[02-external-research#R4.2]]). Hook-injected reframe (F1) avoids decay because it re-emits per user message.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- [[rc-08-sycophantic-gap-filling]] (causally adjacent: both stem from "produce artefact" gradient)
- [[rc-02-helpfulness-as-artefact]] (parent mechanism)
