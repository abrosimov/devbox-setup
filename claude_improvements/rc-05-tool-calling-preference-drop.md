---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-05
layer: A
created: 2026-06-27
symptoms: [S-015, S-016, S-027]
---

# RC-05 — 4.8 favours reasoning over tool calls

## Mechanism

Anthropic documents verbatim: "Claude Opus 4.8 tends to favor reasoning over tool calls" ([[02-external-research#R1.2]]). The 4.7→4.8 transition reversed the 4.6 sub-agent over-spawn but overcorrected: fewer file reads, more in-head speculation. Stella Laurenzo's 6,852-session study measured files-read-before-edit drop **6.6 → 2.0** Feb→March 2026 ([[02-external-research#R2.2]]). The mechanistic chain: fewer Reads → more speculation about file contents → more invented APIs / hallucinated function signatures → claims of "done" without verification → S-027 (build/test fails on user's machine). Anthropic's documented mitigation is the `<investigate_before_answering>` snippet ([[02-external-research#R1.1]]): "Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering." This user's setup partially covers this via `pre_write_existing_guard.py` (blocks Write to unread files) — but does not cover Edit, MultiEdit, or Bash file modification. The gap is structural ([[03-current-config-map#3.8 Reconnaissance before action]]).

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-015]] (random unsupported assumptions), [[01-symptoms-inventory#S-016]] (rushes to solve), [[01-symptoms-inventory#S-027]] (reports done — build fails)
- External: [[02-external-research#R1.2]] (verbatim "favor reasoning over tool calls"), [[02-external-research#R1.1]] (verbatim `<investigate_before_answering>` snippet), [[02-external-research#R1.3]] (4.8 changelog: "better tool triggering, fewer cases of skipping a tool call"), [[02-external-research#R2.2]] (6.6→2.0 file-reads-before-edit collapse)
- Config gaps: [[03-current-config-map#3.8 Reconnaissance before action]] — `pre_write_existing_guard.py` covers Write only; Edit/MultiEdit/Bash file-mod uncovered; [[03-current-config-map#3.15 Self-verification before reporting "done" (S-027)]] — no hook validates claimed-pass corresponds to executed test run

## Fix proposals

### F1 — PreToolUse(Edit) blocks edits to files not Read in this session

- **Surface:** hook (extend `pre_write_existing_guard.py` or new)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives on legitimate first-time Edit-via-pattern
- **Approach:** Extend `pre_write_existing_guard.py` (or new `pre_edit_unread_guard.py`) to apply the same "must Read first" rule to Edit and MultiEdit. Session state tracks Read tool calls per file path. If Edit/MultiEdit targets a path with no prior Read, exit-2 with "Reconnaissance required: Read this file before editing. `<investigate_before_answering>`."
- **Steps:**
  1. Audit `pre_write_existing_guard.py` for its session-state schema.
  2. Extend the matcher to Edit + MultiEdit in `hooks.json`.
  3. Whitelist legitimate first-touch scenarios (Write to genuinely new file already covered).
- **Touches/replaces:** `hooks.json`, `bin/pre_write_existing_guard.py`.

### F2 — PreToolUse(Bash) blocks file-modifying Bash on unread files

- **Surface:** hook (extend `pre_bash_safety_gate.py` or new)
- **Effort:** high
- **Impact:** medium
- **Risk:** medium — Bash command parsing is fiddly; risk of over-blocking
- **Approach:** New `pre_bash_unread_modify.py` parses Bash commands for file-modifying patterns (`sed -i`, `>`, `>>`, `mv`, `rm`, `tee`, `python -c "...write..."`). If a target path is not in the session's Read-history, exit-2 with reconnaissance requirement.
- **Steps:**
  1. Implement Bash command parser (reuse logic from existing safety gates).
  2. Cross-reference Read history.
  3. Conservative allowlist: `git` operations, `make`, `mkdir`, `touch` of new paths.
- **Touches/replaces:** `hooks.json`, new `bin/` script.

### F3 — Per-agent system-prompt clause: Anthropic verbatim `<investigate_before_answering>`

- **Surface:** agent-frontmatter (no-code)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — adds ~3 lines to agent prompts
- **Approach:** Append to SE / reviewer agents: `<investigate_before_answering>Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. If the task references a function or symbol, use LSP goToDefinition or Read before claiming anything about it.</investigate_before_answering>`. Anthropic-canonical wording — high adherence prior.
- **Steps:**
  1. Add to `software_engineer_go`, `software_engineer_python`, `software_engineer_frontend`, `code_reviewer`, `meta_reviewer`, `build_resolver_go`, `refactor_cleaner`, `unit_tests_writer`, `integration_tests_writer_*`.
  2. Bulk edit 10 agent files.
- **Touches/replaces:** 10 agent files.

### F4 — Stop hook validating claimed-pass against tool-call history

- **Surface:** hook (new bin script)
- **Effort:** high
- **Impact:** high
- **Risk:** medium — claim-detection regex tuning required
- **Approach:** New `stop_done_audit.py` scans the assistant final message for claims like "tests pass", "build succeeded", "lint clean", "all green". If any such claim is present AND the corresponding Bash invocation (`pytest`, `go test`, `npm test`, `lint`, `tsc`, `go build`) was not in this session's tool-call history (or its last run exited non-zero), emit `decision: block` with "Claimed verification not backed by tool call. Run the command or remove the claim."
- **Steps:**
  1. Implement `bin/stop_done_audit.py` with claim regex + tool-call history check.
  2. Register under `Stop` after `stop_lint_gate`.
  3. Allowlist for `dry-run`, `would-pass-if`, hypothetical language.
- **Touches/replaces:** `hooks.json`, new `bin/` script.

### F5 — Set `effort: xhigh` for SE agents (raises tool-call propensity)

- **Surface:** agent-frontmatter (no-code)
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low — token cost increase
- **Approach:** [[02-external-research#R1.2]] documents that higher effort reverses the tool-skip tendency. Set `effort: xhigh` on coding agents. Anthropic recommends `xhigh` for "coding and agentic work" per [[02-external-research#R1.5]] (`/effort xhigh` changelog entry).
- **Steps:**
  1. Add `effort: xhigh` to `software_engineer_*` agent frontmatter.
  2. Same change as F4 in [[rc-01-rlhf-pushback-loop]] — coordinate to avoid double-edit.
- **Touches/replaces:** 3 agent files (shared with RC-01).

## Acceptance signal

- File-reads-per-Edit-call ratio rises from current baseline to ≥3.0 (vs Stella Laurenzo's 2.0 March 2026 low).
- `pre_edit_unread_guard.py` block fires ≤2 per 50 Edit calls after tuning — meaning agents pre-Read.
- `stop_done_audit.py` block fires <1 per 20 sessions claiming completion — meaning claims are backed.
- User-reported S-027 "build/test fails when I run it" incident → 0 across 4 weeks.
- Manual audit: 20 SE-agent sessions show ≥18 with a Read tool call for every Edit target.

## Trade-offs and counter-evidence

- F1 + F2 (deterministic gates on Edit/Bash) are the highest-impact and the most likely to friction users. The current `pre_write_existing_guard.py` already does this for Write — extending the surface generalises the principle but multiplies false-positive surface area.
- F4 (Stop done-audit) requires reliable detection of "claim of completion" — natural language is hard. Anthropic's `<investigate_before_answering>` is the prior-art template but does not include a verification check. False-positive risk on legitimate "tests would pass if you run them" hedged claims.
- F5 (effort xhigh) directly costs tokens. 30-50% more per turn. Tolerable for SE agents; not for chat.
- Counter-evidence on hooks effectiveness: [[02-external-research#R6.3]] notes hooks override permission mode and run before every matching tool call — they are the deterministic backstop. Advisory prompts (F3) carry ~70% adherence; F1, F2, F4 are the reliability floor.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- Adjacent: [[rc-06-no-working-memory]], [[rc-24-done-without-verification]], [[rc-07-asymmetric-ask-vs-guess]]
