---
tags: [claude-improvements, phase3, root-cause, layer-E]
phase: 3
rc-id: RC-24
layer: E
created: 2026-06-27
symptoms: [S-027]
---

# RC-24 — Agent claims build/lint/test pass without running them; no hook validates the claim

## Mechanism

Sub-agents end their turn with statements like "tests pass, lint clean, ready for review", and when the user runs the suggested commands they fail (compilation errors, broken tests, lint violations). The cause is not that the agent lies — it is that the model's notion of "tests pass" is "I would expect tests to pass given the changes I made", not "I ran `pytest` and saw exit-code 0". This is a layer-E (verification) gap. `stop_lint_gate.py` exists and runs lint at session end, but it does not (a) validate that claimed test runs actually occurred, or (b) gate `Stop` on a successful run when the final message asserts tests pass. The asymmetry — claim is cheap, verification is expensive — is the precise shape RC-24 fixes by making the claim itself trigger verification.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-027]] (reports done, build/lint/test fails when user runs them)
- External: [[02-external-research#R2.2]] (Stella Laurenzo 6852 sessions: "When thinking is shallow, the model defaults to the cheapest action available: edit without reading, **stop without finishing**, dodge responsibility for failures"), [[02-external-research#R1.2]] (4.8 favours reasoning over tool calls — fewer verification runs)
- Config gaps: [[03-current-config-map#3.15 Self-verification before reporting "done" (S-027)]] — "No hook validates that build/test commands the agent reports as passing actually passed"
- Reflection: [[04-reflection-evidence#RC-ref-2]] ("draft becomes its own source of truth" — agent's prior-turn intent becomes "fact" that tests pass)

## Fix proposals (≥5)

### F1 — Stop hook reading transcript for test claims and verifying tool calls

- **Surface:** new bin script + hook registration
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives on legitimate "tests pass" mentions
- **Approach:** A Stop hook scans the assistant's final message for patterns like "tests pass", "build succeeds", "lint clean", "all green". For each match, scan the transcript for a corresponding `Bash` ToolUse with `pytest`/`go test`/`make test`/etc. and exit-code 0. If no matching call, exit-2 with `additionalContext` "you claimed `<claim>` without a matching tool call — run the command and retry".
- **Steps:**
  1. Create `bin/stop_verify_claims.py`.
  2. Pattern library: `tests? pass`, `build succeed|build OK|builds`, `lint clean|no lint|lint pass`, `all green|all checks pass`.
  3. Toolcall library: `pytest`, `go test`, `make test`, `make lint`, `npm test`, `cargo test`.
  4. Read transcript via Claude Code's stop-hook payload.
  5. Register under `Stop`.
- **Touches/replaces:** `hooks.json`, new bin script.

### F2 — Post-Stop validator running `make test` when final message mentions tests

- **Surface:** Stop hook + state file
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — running tests on every Stop is slow
- **Approach:** Triggered only when F1 detects a claim. The hook runs the project's test command (detected from `package.json`/`Makefile`/`pyproject.toml`) and stops only if exit-code 0. Caches the run so subsequent identical-state Stops do not re-run. Slower but deterministic.
- **Steps:**
  1. Extend `bin/stop_verify_claims.py` or add `bin/stop_run_tests.py`.
  2. Detect test command from project files.
  3. Hash the diff since last verification and skip if unchanged.
  4. On failure, exit-2 with full failure output as `additionalContext`.
  5. Register under `Stop` after F1.
- **Touches/replaces:** `hooks.json`, new/extended bin script.

### F3 — Per-agent system prompt forbidding "tests pass" claim without prior tool call

- **Surface:** agent frontmatter (no-code)
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Add a verbatim line to each engineering agent (`software_engineer_*`, `unit_tests_writer`, `integration_tests_writer_*`, `code_reviewer`) description: "Never claim 'tests pass' / 'build succeeds' / 'lint clean' unless you ran the command this turn and observed exit-code 0. If you did not run, say 'tests not run — please verify' or run the command now."
- **Steps:**
  1. Edit ~8 engineering agent frontmatter blocks.
  2. Add to `agent-base-protocol` skill as cross-cutting rule.
  3. Add positive trigger evals.
  4. No code.
- **Touches/replaces:** ~8 agent descriptions, `agent-base-protocol` skill.

### F4 — Extend `/techne-verify` command to detect false-done patterns

- **Surface:** existing command
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** `/techne-verify` already runs build/typecheck/lint/test. Extend it to also (a) scan the last assistant message for done-claims, (b) emit a "claim vs reality" report. If the agent said "tests pass" and verify finds them failing, the output flags the false-done explicitly.
- **Steps:**
  1. Edit `commands/techne-verify.md` to add claim-scan step.
  2. Reuse F1's pattern library.
  3. Output: per-claim status (`tests pass: CLAIMED, ACTUAL FAIL — see below`).
  4. Recommend `Stop` hook installation if F1 absent.
- **Touches/replaces:** `commands/techne-verify.md`.

### F5 — New skill `verification-discipline`

- **Surface:** new skill
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** Documents the protocol: before claiming any verifiable state (tests/build/lint), run the command this turn. Cite the exit code. Counter-pattern: "I expect tests to pass because <reasoning>" → forbidden as a substitute for running. Always invoked via `Skill` from `software_engineer_*` agents post-Edit.
- **Steps:**
  1. Create `skills/verification-discipline/SKILL.md`.
  2. Document trigger ("agent about to claim done"), action (run command + cite exit code), forbidden pattern.
  3. Reference from engineering agents.
  4. `trigger_evals.json` with positive cases ("I believe tests pass", "should work now").
- **Touches/replaces:** new skill, engineering agent cross-references.

## Acceptance signal

- F1 hook exit-2 rate on false-done claims trending to zero as agents adapt.
- For sessions where the assistant claims "tests pass", a matching `pytest`/`go test` ToolUse with exit-code 0 exists in the same turn ≥95% of the time.
- User stops reporting "agent said done but build failed" in feedback notes.
- `/techne-verify` claim-vs-reality report shows zero discrepancies on closed PRs.
- Engineering agents emit "tests not run — please verify" when they cannot run tests, instead of false claims.

## Trade-offs and counter-evidence

- F1 risks false positives on phrases like "tests pass on master but my branch fails" — pattern matcher needs context. Use intent-level matching, not bare substring.
- F2 (post-Stop test run) burns wall-clock on every Stop. Mitigated by diff-hashing; still might add 30-120s per Stop for slow test suites. Consider opt-in per-project via `workflow.json`.
- F3 (per-agent prompt rule) is advisory — same ~70% adherence as RC-17 warns. F1+F2 deterministic; F3 reinforces.
- Anthropic [[02-external-research#R2.2]] documents the deeper cause (shallow thinking → cheapest action). The fix attacks symptom not cause; cause is layer-A model behaviour, mitigation is verification gates.
- F4 collides with workflow if `/techne-verify` becomes mandatory — user pays time cost. Counter: cheap as long as F1 catches most false-dones at Stop time.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-027]]
- [[02-external-research#R2.2]]
- [[03-current-config-map#3.15 Self-verification before reporting "done" (S-027)]]
- [[rc-17-advisory-only-rules]]
- [[rc-25-citation-not-enforced]]
