---
tags: [claude-improvements, phase3, root-cause, layer-E]
phase: 3
rc-id: RC-28
layer: E
created: 2026-06-27
symptoms: [S-041]
---

# RC-28 — Lint/test stdout floods context every run

## Mechanism

Lint and test commands dump full text output into the assistant's context every invocation, even on success. Modern toolchains have JSON / quiet flags but the agent invokes them with defaults. On a 1M-token-window-but-30%-denser tokenizer ([[02-external-research#R1.4]]) and a soft cliff at 50-60% ([[02-external-research#R4.5]]), each routine `ruff check`, `pytest`, `go test ./...`, `eslint .` invocation consumes hundreds-to-thousands of tokens for no signal value when the run succeeded. The user explicitly named the corrective: "first run silent, on failure rerun with JSON output" ([[01-symptoms-inventory#S-041]]). Surface: verification layer — no PreToolUse hook injects quiet flags; no PostToolUse hook truncates and offers JSON re-run; no env vars steer JSON output. The existing `pre_bash_toolchain_guard.py` corrects project-toolchain invocations (e.g. `pytest` → `uv run pytest`) but does not strip verbosity.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-041]]
- External: [[02-external-research#R1.4]] (tokenizer 30% denser), [[02-external-research#R4.5]] (soft cliff at 50-60%), [[02-external-research#R2.1]] (April postmortem — repetition + odd tool choices on full context)
- Config gaps: [[03-current-config-map#3.1 Context-window management]] — `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` "too late"; no proactive bash-output trimming

## Fix proposals (≥5)

### F1 — PreToolUse Bash hook injecting quiet flags for known commands

- **Surface:** hook (new `bin/pre_bash_quiet_inject.py`, registered on `PreToolUse(Bash)`)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — risk of suppressing useful signal when user explicitly wanted verbose output; mitigate via `-v` detector
- **Approach:** Mirror the `pre_bash_toolchain_guard.py` pattern. Match command head against an allowlist: `pytest` → add `-q --tb=line --no-header`; `ruff check` → add `--quiet`; `eslint` → add `--format=compact`; `go test` → add `-count=1` (no `-v` injection — go test is already quiet on pass); `npm test` / `pnpm test` → add `--silent`; `cargo test` → add `--quiet`. Skip injection when command already contains a verbose flag (`-v`, `--verbose`, `-vv`). Modify the command via the hook's command-rewrite mechanism.
- **Steps:**
  1. Implement `roles/devbox/files/dot_claude/bin/pre_bash_quiet_inject.py`.
  2. Define `QUIET_FLAGS` map: `{"pytest": ["-q", "--tb=line"], "ruff check": ["--quiet"], …}`.
  3. Register under `PreToolUse(Bash)` matcher in `hooks.json` after `pre_bash_toolchain_guard`.
  4. Tests in `bin/tests/test_pre_bash_quiet_inject.py` covering each toolchain.
- **Touches/replaces:** `hooks.json`, sibling to `pre_bash_toolchain_guard.py`.

### F2 — PostToolUse Bash hook truncating output above threshold

- **Surface:** hook (new `bin/post_bash_truncate.py`, registered on `PostToolUse(Bash)`)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — truncation can hide the actual error; mitigate by always keeping tail (last 50 lines)
- **Approach:** When stdout+stderr combined exceeds N lines (default 200) AND exit-code is 0, replace with `[truncated N lines; rerun with --format=json for structured output]`. On non-zero exit, keep last 50 lines + first 20 lines + truncated middle marker. Emit `additionalContext` with the JSON-rerun suggestion specific to the toolchain detected.
- **Steps:**
  1. Implement `post_bash_truncate.py`.
  2. Use the same toolchain detection as F1 to suggest the correct JSON re-run (`pytest --json-report`, `ruff check --output-format=json`, `eslint --format=json`).
  3. Register under `PostToolUse(Bash)` matcher.
- **Touches/replaces:** `hooks.json`.

### F3 — settings.json env vars for JSON-by-default tool output

- **Surface:** settings.json (edit `roles/devbox/files/dot_claude/settings.json`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — env vars only affect tools that read them; no rule conflicts
- **Approach:** Add to `env`: `RUFF_FORMAT=json` (when supported), `PYTEST_ADDOPTS=-q --tb=line`, `NO_COLOR=1` (strips ANSI from all toolchains — major byte savings), `FORCE_COLOR=0`, `CI=1` (many tools auto-quiet under CI). No-code change to behaviour layer.
- **Steps:**
  1. Edit `settings.json` env block (currently contains `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`).
  2. Verify each env var against current toolchain versions.
  3. Document in `editing-claude-config` skill cross-reference.
- **Touches/replaces:** `roles/devbox/files/dot_claude/settings.json` env block.

### F4 — Per-SE-agent system-prompt clause

- **Surface:** agent body (edit `agents/software_engineer_*.md`, `agents/integration_tests_writer_*.md`, `agents/unit_tests_writer.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — text-only
- **Approach:** Add `## Tool output discipline` block: "Default to silent invocations: `pytest -q`, `go test ./...` (silent on pass), `ruff check --quiet`. On failure, re-run with structured JSON output: `pytest --json-report`, `ruff check --output-format=json`, `eslint --format=json`. Never dump raw lint/test stdout into your final message — summarise failures by file:line." No-code, low-impact rule reminder.
- **Steps:**
  1. Add the clause to 5 SE/test agent files.
  2. Cross-reference the new `tool-output-discipline` skill (F5).
- **Touches/replaces:** 5 agent files.

### F5 — New skill `tool-output-discipline`

- **Surface:** skill (new `skills/tool-output-discipline/SKILL.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory
- **Approach:** Skill (≤80 lines) listing per-toolchain quiet/JSON flags, default-silent-then-JSON-on-failure pattern, and how-to-summarise-failures-by-file-line template. `alwaysApply: false`; triggered when prompt or context contains `pytest`, `ruff`, `eslint`, `go test`, `cargo test`, `mypy`, `tsc`.
- **Steps:**
  1. Scaffold via `skill-builder` under `skills/tool-output-discipline/`.
  2. Frontmatter: `triggers: [pytest, ruff, eslint, go test, mypy, lint, test, cargo]`.
  3. Worked example: failing pytest run → JSON re-run → summary table.
- **Touches/replaces:** none.

### F6 — Stop hook flagging assistant message that contains raw lint/test stdout

- **Surface:** hook (extend `bin/stop_lint_gate.py`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — warn-only
- **Approach:** Add a regex detector to `stop_lint_gate.py` that matches typical lint/test stdout shapes in the final assistant message (pytest dotty progress lines, ruff `--- file ---` headers, eslint `error  Definition` lines). Warn when detected: "raw tool output in final message — summarise by file:line instead". No new hook file; extends existing.
- **Steps:**
  1. Add `RAW_TOOL_STDOUT_REGEXES` to `bin/stop_lint_gate.py`.
  2. Emit `additionalContext` warning if matched.
- **Touches/replaces:** `bin/stop_lint_gate.py`.

## Acceptance signal

- Average tokens-per-Bash-invocation drops measurably on a sample of 10 routine lint/test runs (target: ≥50% reduction on passing runs).
- `pytest`/`ruff`/`eslint` invocations in transcript inspection always carry quiet flags after F1 ships.
- Failing-test re-runs use `--json-report` / `--output-format=json` ≥9 of 10 times.
- `post_bash_truncate.py` activates only on >200-line outputs and preserves error tails.
- Raw-stdout warning from F6 fires <1 per session after first week.

## Trade-offs and counter-evidence

Quiet-flag injection (F1) can mask warnings the user wanted to see — explicit `-v` already bypasses, but partial-verbose flags (`-vv`) need careful handling. Truncation (F2) is reversible — the agent can rerun. JSON re-run is more tokens than silent-quiet on failure but still less than raw stdout; net positive. F3 (`NO_COLOR=1`) is the highest-impact-lowest-risk fix in this RC — ANSI escapes are ~10-20% byte overhead on coloured tool output. Anthropic guidance ([[02-external-research#R1.1]]) confirms reasoning-vs-tool-calls trade-off — fewer tokens spent on stdout means more headroom for reads. No Anthropic counter-evidence on this RC. Risk to watch: `CI=1` env var may change toolchain behaviour beyond quietness (some test runners skip slow paths under CI); verify per-toolchain before global enablement.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-09-long-context-soft-cliff]] (context budget pressure)
- [[rc-24-done-without-verification]] (sibling — claims vs runs)
