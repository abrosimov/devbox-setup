---
tags: [claude-improvements, phase3, root-cause, layer-C, layer-E]
phase: 3
rc-id: RC-31
layer: C
created: 2026-06-30
symptoms: [S-018, S-024, S-027]
---

# RC-31 — Agent satisficing: workarounds in code instead of root-cause fix in config

## Mechanism

When an agent's command fails for an environmental reason — wrong `UV_CACHE_DIR`, missing `GOCACHE`, sandbox-blocked path, project-toolchain mismatch — the cheapest action is to wrap the failure inside the user's code or inside the next Bash invocation. Concrete shapes observed: inline env-var prefixes in commands (`UV_CACHE_DIR=$PWD/.cache uv run pytest`), "corrective" helper functions in source (`_absolutise_path`, `_ensure_dir`, `_normalise_module_path`), defensive `mkdir -p` before every command, hard-coded path normalisation that papers over a broken `pyproject.toml` or `settings.json` env block. The visible artefact (a code change in the file the user named) satisfies the turn-output gradient ([[rc-02-helpfulness-as-artefact]]); the invisible structural fix (a one-line edit to `settings.json` env, a missing entry in `pyproject.toml`, a sandbox writable-dir addition) does not. Compounded by [[rc-05-tool-calling-preference-drop]]: investigating the config requires extra Read/Bash calls; patching in place requires only one Edit. Result: the user accumulates load-bearing workarounds in committed code, the underlying config stays broken, every new session repeats the patch. The three `software_engineer_*` agents inherit `code-writing-protocols` skill which has a Pre-Implementation Verification section but no Definition-of-Done gate that explicitly forbids env-prefix patterns in committed shell commands or `_absolutise_*`-shaped helpers in source.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-018]] (reinvents wheels — applies here as "invents helper instead of fixing config"); [[01-symptoms-inventory#S-024]] (external locus of control — "the env is broken, let me work around it" instead of "the env is broken, let me fix it"); [[01-symptoms-inventory#S-027]] (false done — patched workaround declared "fixed" without touching root cause).
- Upstream model causes: [[rc-02-helpfulness-as-artefact]] (visible patch beats invisible config edit on the helpfulness gradient); [[rc-05-tool-calling-preference-drop]] (4.8 prefers to reason about the patch over running extra investigation calls); [[rc-07-asymmetric-ask-vs-guess]] (asking "is your env var set?" feels like stalling).
- Adjacent posture gaps: [[rc-15-engineering-attitude-skill-missing]] (Fisher's-maxim and locus-of-control encoding absent — the constructive third option here is "fix the config and delete the workaround"); [[rc-08-sycophantic-gap-filling]] (terse "make it work" feedback triggers patch-in-place).
- Verification gap: [[rc-24-done-without-verification]] — agent claims fix complete without re-running with the workaround removed.
- Config gap: no `code-writing-protocols` clause explicitly listing workaround anti-patterns (env-var inlining, `_absolutise_*` helpers, defensive `mkdir -p` chains). `code-writing-protocols` Pre-Implementation Verification covers "is the toolchain working" but not "is your fix in the right layer".
- User source: explicit Fix 8 framing — "это самая дорогая для исправления причина" — agent ships workarounds, user re-discovers the broken config weeks later.

## Fix proposals

### F1 — Definition-of-Done block in `code-writing-protocols` skill

- **Surface:** existing skill extension
- **Effort:** low
- **Impact:** high (cascades to all 3 SE agents)
- **Risk:** low — additive section, no rule conflict
- **Approach:** Add a `## Definition of Done` section near the end of `code-writing-protocols/SKILL.md`. Verbatim content from user's Fix 8a, sharpened:
  ```
  ## Definition of Done
  Before claiming "done":
  1. `git status` — no unexpected files (cache dirs, lock files moved, `.venv` regenerated outside repo).
  2. Project verification command exits 0 (e.g. `make verify`, `pnpm verify`, project-specific).
  3. No inline env-var prefixes in committed Bash commands (`UV_CACHE_DIR=…`, `GOCACHE=…`, `PYTHONPATH=…`).
     If you wrote one — STOP. The cause is in settings.json / pyproject.toml / .envrc, not in the command.
  4. No "corrective" helpers in source (`_absolutise_path`, `_ensure_dir`, `_normalise_*`).
     If they appear necessary — STOP. The config that should produce absolute/normalised values is broken; fix the producer, delete the corrector.
  5. The fix removed at least one workaround it didn't replace (net workaround count ≤ before).
  ```
- **Steps:**
  1. Edit `roles/devbox/files/dot_claude/skills/code-writing-protocols/SKILL.md` — add the section above the existing "Anti-Laziness Protocol" or equivalent tail.
  2. Reference from each `software_engineer_*` agent's "After Completion" section (one-line pointer; no duplication).
  3. Add positive-trigger evals: assistant turn proposing `UV_CACHE_DIR=...` inline should match.
- **Touches/replaces:** `skills/code-writing-protocols/SKILL.md`; three SE agent files (one-line each).

### F2 — PostToolUse hook flagging workaround patterns in Edit/Write payload

- **Surface:** new bin script + hooks.json registration
- **Effort:** medium
- **Impact:** high (deterministic)
- **Risk:** medium — false positives on legitimate `UV_*=` lines in `.env.example`, integration test fixtures
- **Approach:** PostToolUse hook on Edit/Write/MultiEdit. Scans new content for workaround signatures:
  - `(UV_CACHE_DIR|UV_PYTHON_INSTALL_DIR|UV_PROJECT_ENVIRONMENT)=` outside `.env*` / `pyproject.toml` / `settings.json`
  - `(GOCACHE|GOMODCACHE|GOTOOLCHAIN)=` outside same allowlist
  - `def _absolutise_|def _ensure_|def _normalise_path` followed by `os.path.abspath` / `Path.resolve` (Python)
  - `func absolutise|func ensure(Dir|Path)` (Go)
  - Repeated `mkdir -p` in shell strings immediately before each command
  - On match, emit non-blocking warning via `additionalContext`: "Potential workaround detected at `<file>:<line>`: `<pattern>`. Verify the root cause is not in `settings.json` env block / `pyproject.toml` / sandbox config before committing. See RC-31 / code-writing-protocols DoD."
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/bin/post_edit_workaround_guard.py`.
  2. Pattern library as data, with allowlist for fixture/example paths.
  3. Tests in `bin/tests/test_post_edit_workaround_guard.py` covering true/false positives.
  4. Register in `hooks.json` under `PostToolUse.Edit|Write|MultiEdit`.
  5. Non-blocking by default (warning only); add `BLOCK_ON_WORKAROUND=1` env var for strict mode.
- **Touches/replaces:** new `bin/post_edit_workaround_guard.py`; `bin/tests/`; `hooks.json`.

### F3 — Workflow-memory: "diff-first when a test breaks after agent run"

- **Surface:** skill content + new skill + UserPromptSubmit hook
- **Effort:** low (F3a) + medium (F3b)
- **Impact:** medium
- **Risk:** low
- **Approach:** Encode the user's Fix 8c rule: when a test fails after an agent edit, the first move is `git diff` + read of the touched config files, **not** `make clean`. Delivered in two complementary layers that ship together (decision per [[20-consolidation-plan#Decisions taken]]):
  - **F3a (advisory layer, ships in Tranche 1):** Add a "Debugging discipline" paragraph to `skills/code-writing-protocols/SKILL.md`. The skill loads whenever SE / test-writer / reviewer agents fire — exactly the target context for this rule. Deliberately not in `USER_AUTHORITY_PROTOCOL.md` because UAP is being aggressively trimmed in the same tranche; the SE-loaded skill is the cheaper carrier.
  - **F3b (deterministic layer, ships in Tranche 4):** New skill `root-cause-discipline` (small, on-demand) plus a UserPromptSubmit hook that detects destructive-cleanup intent (`make clean`, `rm -rf`, `regenerate`, `nuke .venv`, etc.) in the user prompt and injects `additionalContext`: "Before destructive cleanup, run `git diff` and read the relevant config. See `root-cause-discipline` skill." Covers contexts where `code-writing-protocols` is not loaded (TPM, planner, ad-hoc shell sessions).
- **Steps (F3a):**
  1. Edit `roles/devbox/files/dot_claude/skills/code-writing-protocols/SKILL.md` — add a "Debugging discipline" subsection (≤5 lines) near the Pre-Implementation Verification section.
  2. Mention from each SE agent's "After Completion" pointer (one-line each).
- **Steps (F3b):**
  1. Create `skills/root-cause-discipline/SKILL.md` with diff-first rule, two concrete examples (UV cache + Go toolchain), three anti-patterns.
  2. Extend `proposal_discipline.py` (or new `bin/pre_prompt_diff_first_guard.py`) with destructive-cleanup intent detection.
  3. Register UserPromptSubmit hook in `hooks.json`.
  4. Add positive trigger evals (`make clean` + `rm -rf node_modules` + `regenerate the venv` should all match).
- **Touches/replaces:** `skills/code-writing-protocols/SKILL.md` (F3a); new `skills/root-cause-discipline/SKILL.md`, hook script, `hooks.json` (F3b).

### F4 — `code-writing-protocols` Pre-Implementation Verification — add "Layer Check"

- **Surface:** existing skill subsection
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** The skill already has Pre-Implementation Verification that probes the toolchain. Add a "Layer Check" rule: before writing any code that touches paths, env vars, or shell command construction, answer in one line: "Is the bug in this layer (code) or below (config / sandbox / toolchain)? If below, fix below." Forces the model to articulate the layer choice before acting. Pairs with F1 (DoD) and F2 (hook) — F4 is the upfront prompt, F1 is the post-implementation gate, F2 is the deterministic check.
- **Steps:**
  1. Edit `skills/code-writing-protocols/SKILL.md` — add 3-line "Layer Check" subsection inside Pre-Implementation Verification.
  2. Reference one concrete example: "If `uv run pytest` fails with permission error on cache, the fix is in `settings.json` env, not in `pytest.ini` or in inlined `UV_CACHE_DIR=...`."
- **Touches/replaces:** `skills/code-writing-protocols/SKILL.md`.

### F5 — Output-style `layer-tagged` for engineering turns

- **Surface:** new output-style
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low (opt-in)
- **Approach:** Lightweight output style users can switch into for debugging-heavy tasks. Forces the model to prefix code changes with a `<layer>` tag: `<layer>code|config|toolchain|sandbox</layer>`. Reading the tag, the user immediately sees whether the agent chose the right layer. Pairs with F1's DoD audit.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/layer-tagged.md`.
  2. Document trigger in `commands/techne-implement.md` as opt-in flag.
- **Touches/replaces:** new output-style file; `commands/techne-implement.md`.

### F6 — `/techne-debug` command enforcing diff-first protocol

- **Surface:** new command
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** Wrap F3 in a dedicated command. `/techne-debug` runs `git diff HEAD~1`, lists touched files, asks "which of these are config vs source?", and only after that opens the debugging session. Prevents the satisficing default by making the diff-first move the literal first action.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/commands/techne-debug.md`.
  2. Reference `root-cause-discipline` skill (F3b).
  3. Add to `make validate-claude` cross-reference list.
- **Touches/replaces:** new command file; validation script awareness.

## Acceptance signal

- F1 lands: all 3 SE agents reference the DoD section; engineering-task evals fail when the assistant output contains an inline env-var prefix in a committed command.
- F2 hook fires non-blocking warning in ≥80% of synthetically-constructed workaround edits; <5% false positive on a sample of `.env.example` / fixtures.
- In 10 fresh sessions where the broken-config scenario is seeded, ≥7 agents fix the config layer instead of patching the symptom in code.
- The number of `_absolutise_*` / `_ensure_*` helpers committed across user's repos trends to zero on new code.
- User reports: "agent stopped shipping workarounds; when env-var hack feels right, it pauses and asks about settings.json instead."

## Trade-offs and counter-evidence

- **Workarounds are sometimes correct.** Inline env vars are legitimate in scratch scripts, fixture setup, container entrypoints. F2's pattern matching must allowlist `.env*`, `docker-compose*`, `Dockerfile`, `tests/fixtures/`. False positives erode trust.
- **F1 cascade depends on `code-writing-protocols` being loaded.** Skill activation is advisory ([[rc-19-skill-invocation-advisory]]). If the SE agent skips the skill, DoD never fires. Mitigated by per-agent body reference (F1 step 2).
- **F2 cannot tell "fixing a workaround" from "writing a new one".** A diff that deletes an old `_absolutise_path` and adds a fixed-config edit looks similar at PostToolUse time to one that adds a new helper. Pattern matcher needs to compare net workaround count (additions vs deletions), not raw additions.
- **RLHF helpfulness pressure is upstream** ([[rc-02-helpfulness-as-artefact]]). The model wants to produce a visible artefact in the file the user named. Skill + hook intervention does not eliminate the pressure; it raises the cost of yielding to it. Expect partial mitigation, not solution.
- **The "Layer Check" (F4) burns thinking tokens.** Every engineering turn now articulates layer before acting. Most turns the answer is "code" and the line is wasted. Counter: explicit-articulation cost is low (one line); satisficing-cost is days of accumulated technical debt. Trade favours articulation.
- **F6 (`/techne-debug` command) competes with `/techne-implement`.** User must remember to type the right command. Friction. Counter: optional; `/techne-implement` still works, F6 is for high-stakes debugging.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-018]] · [[01-symptoms-inventory#S-024]] · [[01-symptoms-inventory#S-027]]
- [[rc-02-helpfulness-as-artefact]] — upstream gradient toward visible artefact
- [[rc-05-tool-calling-preference-drop]] — investigation cost asymmetry
- [[rc-07-asymmetric-ask-vs-guess]] — asking-about-config feels like stalling
- [[rc-08-sycophantic-gap-filling]] — terse "make it work" → patch-in-place
- [[rc-15-engineering-attitude-skill-missing]] — locus-of-control and Fisher's maxim
- [[rc-19-skill-invocation-advisory]] — F1 cascade depends on skill activation
- [[rc-24-done-without-verification]] — false-done pattern at the verification stage
- [[20-consolidation-plan]] — placement of this RC in the prioritised tranches
