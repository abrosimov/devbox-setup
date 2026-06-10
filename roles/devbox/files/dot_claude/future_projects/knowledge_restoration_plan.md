# Knowledge Restoration & Self-Improvement Loop

## Overview

This plan addresses a fundamental tension in the Claude Code agent/skill system: content was deleted because "Claude already knows this," but Claude's training data is dominated by mediocre patterns. "Knows" does not equal "will do correctly." The deleted content was not redundant — it was corrective.

The plan restores corrective knowledge, hardens enforcement through model-independent tools (linters, hooks), and builds a measurement-first self-improvement infrastructure grounded in external signals rather than self-reflection.

### Goals

1. **Measure before changing**: Establish baselines so every subsequent change has quantified impact
2. **Enforce through tools, not instructions**: Linters and hooks are deterministic; skill instructions are probabilistic
3. **Restore corrective knowledge**: Small, high-signal "Prefer X over Y" reference tables — not tutorials
4. **Harden reviewers**: Blind review protocol, forced justification, concrete binary checks
5. **Build externally-grounded self-reflection**: Every reflection loop must consume external signals (eval results, linter output, test failures)

### Non-Goals

- Agent templatisation (separate project, clear ROI but independent concern)
- Recursive/hierarchical planning (no evidence of improvement over current planner)
- Cross-model review (weaker model reviewing stronger model = shallower reviews)
- Memory MCP feedback loops (adds coupling without evidence of benefit)
- LLM-based prompt hooks for semantic checks (guidance dressed as enforcement)
- Gate logic consolidation (deferred — 24 agents with duplicated patterns)

### Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Trigger eval pass rate | 2/11 skills (18%) | 8/11 skills (73%) | `make eval-skills` |
| Skills with trigger evals | 11/42 | 30/42 | `make validate-skills` |
| Skills with content evals | 0/42 | 10/42 | `make validate-skills` |
| Description budget utilisation | Unknown | < 80% (< 12,800 chars) | `bin/audit-skill-budget` |
| alwaysApply total lines | ~502 | < 400 | `wc -l` on 5 skills |
| Go linter rules enabled | baseline | +5 rules (wrapcheck, nilnil, noctx, errorlint, forbidigo) | `.golangci.yml` |
| pre-edit-lint-guard patterns | 2 layers | 3 layers (+security patterns) | `bin/pre-edit-lint-guard` |

## Prerequisites

1. **Symlink deployment is active** — changes in `roles/devbox/files/dot_claude/` propagate to `~/.claude/` without `make run` (DONE)
2. **`make eval-skills` works** — Anthropic's `run_eval.py` is installed and functional (DONE)
3. **`make validate-skills` works** — structural validation passes (DONE)
4. **`make validate-claude` works** — cross-reference validation passes (DONE)
5. **`claude-diff` / `claude-pull` works** — root file sync for non-symlinked files (DONE)

## Phase 0: Foundation (Measurement & Testability)

Everything else depends on Phase 0. No changes to skills, agents, or hooks until measurement infrastructure exists.

### 0.1 Skill Description Budget Audit Script

- **What**: Create `bin/audit-skill-budget` — a script that parses every `SKILL.md` frontmatter, extracts the `name` and `description` fields, computes the character count for each skill's entry in the system prompt (format: `- {name}: {description}`), and reports total utilisation against the 16,000-character budget.
- **Why**: The 16K budget was cited in research but never audited. If we exceed it, skills are silently excluded from the system prompt — invisible and catastrophic. Every subsequent phase that adds or modifies skills MUST run this script to verify headroom. The description field uses YAML multiline folded scalar syntax (`description: >`), which makes naive extraction unreliable.
- **How**:
  1. Write a Python script (no external deps beyond stdlib) that:
     - Walks `skills/*/SKILL.md`
     - Parses YAML frontmatter between `---` markers (use `re` + manual parsing, not `pyyaml`, for CI portability — match the pattern in `validate-skill-evals`)
     - Extracts `name` and `description` fields, handling multiline folded scalars (`>`, `|`, `>-`)
     - Computes `len(f"- {name}: {description}")` per skill
     - Outputs: per-skill breakdown sorted by size, total chars, budget remaining, utilisation percentage
     - Exit code 1 if utilisation > 90% (warning) or > 100% (error)
  2. Add to `Makefile` as `make audit-budget`
  3. Integrate into `make validate-claude` (run as part of standard validation)
- **Files touched**:
  - `bin/audit-skill-budget` (new)
  - `Makefile` (add target)
  - `bin/validate-config.py` (optional: call audit as sub-check)
- **Acceptance criteria**:
  - Script outputs correct char counts for all 42 skills
  - Multiline YAML folded scalar descriptions are correctly unfolded
  - `make audit-budget` runs in < 1 second
  - Exit code 1 when budget exceeds 90%
- **Depends on**: none
- **Estimated effort**: S

### 0.2 Baseline Measurement on Real Tasks

- **What**: Define 5-10 representative tasks across Go, Python, and Frontend. Run each through the agent pipeline (`/implement`). Collect the agent output (code produced, reviewer findings, lint results, test results). Store as baseline artifacts.
- **Why**: The research conversation (13K lines) never asked "what is actually failing right now?" All proposed changes were driven by theoretical concerns. Without baselines, we cannot measure whether changes help or hurt. Huang et al. (ICLR 2024) found that self-correction without external feedback sometimes degrades performance — we need concrete external signals.
- **How**:
  1. Create `future_projects/baseline_tasks.md` listing 5-10 tasks:
     - Go: HTTP handler with error handling, concurrent service with context propagation, database layer with transactions
     - Python: REST endpoint with validation, async service with retry logic
     - Frontend: React component with state management, form with accessibility
     - Cross-cutting: task requiring timeout configuration, task requiring proper logging
  2. For each task, define:
     - Input prompt (what to tell the agent)
     - Expected quality signals (what the output should contain)
     - Anti-patterns to watch for (what the output should NOT contain)
  3. Run each task with current agents, save full output to `future_projects/baselines/`
  4. Score each output against the quality signals manually (human evaluation)
  5. Record scores in a summary table
- **Files touched**:
  - `future_projects/baseline_tasks.md` (new)
  - `future_projects/baselines/` (new directory with output artifacts)
- **Acceptance criteria**:
  - 5+ tasks defined with concrete input prompts and expected signals
  - Each task run at least once with output saved
  - Summary table with scores exists
  - At least 2 tasks per language (Go, Python, Frontend)
- **Depends on**: none
- **Estimated effort**: L (requires running agents and human evaluation)

### 0.3 Expand Eval Coverage: Outcome Evals for Top 10 Skills

- **What**: Add `evals/evals.json` (content evals) to the 10 most impactful skills. Each eval tests whether the skill's instructions actually appear in agent output — not just whether the skill triggers, but whether it changes behaviour.
- **Why**: Trigger evals (11 skills) only test "did Claude load the skill?" Content evals test "did the skill change the output?" This is the critical gap. Self-Refine (Madaan et al., NeurIPS 2023) showed gains only in iterations 1-2 with concrete feedback signals. Evals ARE the concrete feedback.
- **How**:
  1. Priority order for content evals (skills most likely to produce measurable output changes):
     - `code-comments` — test: output should NOT contain narration comments
     - `project-preferences` — test: output should use specified libraries (zerolog not slog, testify not stdlib)
     - `lint-discipline` — test: output should NOT contain suppression directives
     - `go-engineer` — test: output should wrap errors, use context propagation
     - `python-engineer` — test: output should have type hints, use structlog
     - `frontend-engineer` — test: output should use TypeScript strict mode
     - `code-writing-protocols` — test: output should include approval validation
     - `go-review-checklist` — test: reviewer output should cover all checkpoint categories
     - `go-testing` — test: test output should use testify suites, table-driven tests
     - `frontend-testing` — test: test output should use React Testing Library, not enzyme
  2. Each `evals.json` must have:
     - Minimum 3 evals (per `validate-skill-evals` requirement)
     - At least 1 negative test (non-interference check)
     - `must_contain` and `must_not_contain` expectations tied to the skill's actual rules
  3. Validate with `make validate-skills`
- **Files touched**:
  - `skills/{name}/evals/evals.json` (new, 10 files)
- **Acceptance criteria**:
  - 10 skills have content evals
  - `make validate-skills` passes with 0 errors
  - Each eval has >= 3 test cases with >= 1 negative
  - Total expectations >= 50
- **Depends on**: none
- **Estimated effort**: L

### 0.4 Eval Comparison Framework (Before/After Measurement)

- **What**: Create a script `bin/eval-compare` that runs trigger evals (and optionally content evals) twice — once with current skill definitions, once with modified ones — and produces a side-by-side comparison showing which skills improved, degraded, or stayed the same.
- **Why**: Every subsequent phase modifies skills. Without before/after comparison, we cannot tell if changes help. Self-Preference Bias (Wataoka et al., 2024) means the model will overrate its own output — we need automated comparison, not self-assessment.
- **How**:
  1. Script takes two directories as input (e.g., `skills/` and `skills-modified/`)
  2. Runs `make eval-skills` against each
  3. Parses output into structured results (skill name, pass/fail per query, pass rate)
  4. Outputs diff table: skill | before_rate | after_rate | delta
  5. Highlights regressions in red (if terminal supports it)
  6. Exit code 1 if any skill regressed by > 10%
- **Files touched**:
  - `bin/eval-compare` (new)
  - `Makefile` (add `eval-compare` target)
- **Acceptance criteria**:
  - Script produces readable comparison table
  - Detects regressions and improvements
  - Integrates with existing `make eval-skills` infrastructure
- **Depends on**: 0.3 (needs content evals to compare)
- **Estimated effort**: M

## Phase 1: Model-Independent Enforcement

These changes work regardless of which model runs. Linters are faster, deterministic, community-maintained, and do not consume tokens.

### 1.1 Enable Go Linter Rules

- **What**: Add 5 golangci-lint rules to the recommended project configuration AND to the `go-engineer` skill's reference section: `wrapcheck` (error wrapping), `nilnil` (nil, nil returns), `noctx` (HTTP without context), `errorlint` (error comparison), `forbidigo` (forbidden functions like `fmt.Print` in production).
- **Why**: These linters enforce patterns that were previously enforced only through skill instructions (which the model may ignore). Linters are deterministic — they catch 100% of violations, not the ~70% that skill instructions achieve. The `stop-lint-gate` hook already runs `golangci-lint` on modified files, so enabling these rules provides enforcement with zero additional infrastructure.
- **How**:
  1. Document the recommended `.golangci.yml` additions in `go-engineer/SKILL.md` under a new "Recommended Linter Config" section (~20 lines):
     ```yaml
     linters:
       enable:
         - wrapcheck
         - nilnil
         - noctx
         - errorlint
         - forbidigo
     linters-settings:
       forbidigo:
         forbid:
           - pattern: 'fmt\.Print.*'
             msg: use zerolog instead of fmt.Print in production code
     ```
  2. Add a `go-engineer/references/golangci-recommended.yml` file as a copy-paste starter config
  3. Update `project-preferences` skill Go section to mention these linters
- **Files touched**:
  - `skills/go-engineer/SKILL.md` (add ~20 lines)
  - `skills/go-engineer/references/golangci-recommended.yml` (new)
  - `skills/project-preferences/SKILL.md` (add reference to recommended linter config)
- **Acceptance criteria**:
  - Running `golangci-lint` with the recommended config catches: unwrapped errors, nil-nil returns, HTTP without context, wrong error comparisons, fmt.Print in production
  - `stop-lint-gate` automatically enforces these when the project adopts the config
  - `make audit-budget` still shows < 80% utilisation
- **Depends on**: 0.1 (budget check)
- **Estimated effort**: S

### 1.2 Enable Python Linter Rules

- **What**: Add 3 ruff rules to the recommended project configuration AND to the `python-engineer` skill: `BLE001` (blind exception catching), `S307` (eval usage), `S602` (subprocess with shell=True).
- **Why**: Same rationale as 1.1 — deterministic enforcement of patterns that skills can only suggest. The `stop-lint-gate` already runs `ruff check` on Python files.
- **How**:
  1. Document recommended `pyproject.toml` additions in `python-engineer/SKILL.md`:
     ```toml
     [tool.ruff.lint]
     extend-select = ["BLE", "S", "ANN", "RET", "SIM", "TCH"]
     ```
  2. Add `python-engineer/references/ruff-recommended.toml` as starter config
  3. Update `project-preferences` skill Python section
- **Files touched**:
  - `skills/python-engineer/SKILL.md` (add ~15 lines)
  - `skills/python-engineer/references/ruff-recommended.toml` (new)
  - `skills/project-preferences/SKILL.md` (add reference)
- **Acceptance criteria**:
  - `ruff check` with recommended config catches: bare except, eval(), shell=True
  - `make audit-budget` still shows < 80%
- **Depends on**: 0.1
- **Estimated effort**: S

### 1.3 Add Semgrep Custom Rules for Cross-Cutting Patterns

- **What**: Create a `.semgrep/` directory with custom rules for patterns that linters cannot catch: HTTP client without timeout, context not propagated to downstream calls, missing `defer cancel()` after `context.WithTimeout`.
- **Why**: These are patterns the model frequently gets wrong (from baseline observations). Semgrep rules are AST-aware (more precise than regex), free for local use, and can be integrated into `stop-lint-gate`. They bridge the gap between what linters check and what reviewers check.
- **How**:
  1. Write 3-5 semgrep rules:
     - `go-http-no-timeout`: HTTP client created without explicit timeout
     - `go-context-not-propagated`: function receives `context.Context` but calls downstream without passing it
     - `go-missing-defer-cancel`: `context.WithTimeout`/`WithCancel` without `defer cancel()`
     - `python-http-no-timeout`: `requests.get/post` without `timeout` parameter
     - `python-subprocess-no-timeout`: `subprocess.run` without `timeout`
  2. Store rules in `skills/go-engineer/references/semgrep-rules.yml` and `skills/python-engineer/references/semgrep-rules.yml`
  3. Document integration with `stop-lint-gate` (optional — semgrep is slower than linters, may be better as a reviewer pre-check)
- **Files touched**:
  - `skills/go-engineer/references/semgrep-rules.yml` (new)
  - `skills/python-engineer/references/semgrep-rules.yml` (new)
  - `skills/go-engineer/SKILL.md` (reference the rules, ~5 lines)
  - `skills/python-engineer/SKILL.md` (reference the rules, ~5 lines)
- **Acceptance criteria**:
  - `semgrep --config skills/go-engineer/references/semgrep-rules.yml` catches the target patterns
  - Rules have test cases (semgrep supports inline test annotations)
  - No false positives on common patterns (e.g., `http.DefaultClient` is flagged but custom clients with timeouts are not)
- **Depends on**: 0.2 (baseline tasks show which patterns are most common failures)
- **Estimated effort**: M

### 1.4 Pin Model Versions in Agent Frontmatter

- **What**: Change all agent `model:` fields from `opus` / `sonnet` to dated versions like `claude-opus-4-6-20260301` (or whatever the current latest dated version is).
- **Why**: Model upgrades can break optimised prompts. A model upgrade changes the distribution of outputs, which means carefully tuned skill instructions may stop working. Pinning prevents silent regressions. Upgrades become explicit, testable events (run evals before/after).
- **How**:
  1. Determine current dated model IDs (check Anthropic API docs or `claude --version`)
  2. Update all 33 agent `.md` files: replace `model: opus` with `model: claude-opus-4-6-YYYYMMDD`
  3. Document the pinning policy in `skills/workflow/SKILL.md`
  4. Add a `make check-model-pins` target that verifies all agents use dated versions (grep for `model:` without date suffix)
- **Files touched**:
  - `agents/*.md` (all 33 files, 1-line change each)
  - `skills/workflow/SKILL.md` (add pinning policy, ~10 lines)
  - `Makefile` (add `check-model-pins` target)
- **Acceptance criteria**:
  - All agents use dated model versions
  - `make check-model-pins` passes
  - Model upgrade process documented (update pin, run evals, compare)
- **Depends on**: 0.4 (eval comparison framework must exist before upgrading)
- **Estimated effort**: S

### 1.5 Extend pre-edit-lint-guard with Security Patterns

- **What**: Add a Layer 3 to `pre-edit-lint-guard` that blocks common security anti-patterns at write time: hardcoded secrets (API keys, passwords in string literals), `eval()` in Python/JS, `shell=True` in subprocess calls, `dangerouslySetInnerHTML` in React.
- **Why**: Security patterns are binary (present or absent), making them ideal for deterministic hook enforcement. Constitutional AI research confirms that self-critique works best for "concrete binary criteria" — does this violate rule X? These patterns should never appear in new code.
- **How**:
  1. Add to `pre-edit-lint-guard` (Node.js):
     ```javascript
     const SECURITY_PATTERNS = {
       py: [
         { regex: /eval\s*\(/, directive: "eval()", fix: "Use ast.literal_eval() or a proper parser" },
         { regex: /shell\s*=\s*True/, directive: "shell=True", fix: "Use shell=False with a list of args" },
       ],
       ts: [
         { regex: /dangerouslySetInnerHTML/, directive: "dangerouslySetInnerHTML", fix: "Use DOMPurify or a safe rendering approach" },
       ],
       // Common patterns (all languages)
       all: [
         { regex: /(api[_-]?key|password|secret)\s*=\s*['"][^'"]{8,}['"]/, directive: "hardcoded secret", fix: "Use environment variables or a secrets manager" },
       ],
     };
     ```
  2. Apply `all` patterns to every file extension
  3. Language-specific patterns apply based on file extension (same logic as existing Layer 2)
  4. Same exemption logic: if `old_string` already contains the pattern (Edit tool), skip
- **Files touched**:
  - `bin/pre-edit-lint-guard` (add ~40 lines)
  - `skills/lint-discipline/SKILL.md` (document Layer 3, ~10 lines)
- **Acceptance criteria**:
  - `eval("code")` in a `.py` file is blocked
  - `shell=True` in a `.py` file is blocked
  - `dangerouslySetInnerHTML` in a `.tsx` file is blocked
  - Hardcoded API keys are blocked in all file types
  - Existing patterns in `old_string` are exempted (no false positives on edits that preserve existing code)
- **Depends on**: none
- **Estimated effort**: S

## Phase 2: Knowledge Restoration

Small, high-signal corrective references. Format: "Prefer X over Y" decision tables, 30-50 lines each. Research finding: "Claude knows this" means "Claude knows the popular (often wrong) version." Corrective references steer toward expert patterns.

### 2.1 Distill Philosophy to alwaysApply Version

- **What**: Create a new `skills/philosophy/SKILL.md` (the original was deleted during trimming) as a ~40-line alwaysApply skill containing only corrective principles — things Claude systematically gets wrong.
- **Why**: The original philosophy skill was 375 lines (trimmed to 229, then deleted entirely). The research found that Claude's training data biases toward complexity, over-engineering, and "impressive" solutions. A short corrective version counters these specific biases without the context overhead.
- **How**:
  1. Create `skills/philosophy/SKILL.md` with:
     ```yaml
     ---
     name: philosophy
     alwaysApply: true
     description: >
       Core engineering philosophy — simplicity over cleverness, fail-fast over
       defensive, concrete over abstract. Corrects common LLM biases toward
       over-engineering and complexity.
     ---
     ```
  2. Body (~30 lines) as a "Prefer X over Y" table:
     | Prefer | Over | Why |
     |--------|------|-----|
     | Delete code | Add code | Less code = fewer bugs |
     | Concrete types | Generic abstractions | Abstractions should be discovered, not designed upfront |
     | Fail at compile time | Fail at runtime | Earlier failure = cheaper fix |
     | Return error | Panic/throw | Caller decides recovery, not callee |
     | One obvious way | Multiple clever ways | Cleverness is a maintenance liability |
     | Boring technology | Exciting technology | Boring means battle-tested |
     | Explicit dependency | Hidden magic | DI frameworks obscure control flow |
     | 10 lines of duplication | 1 abstraction serving 2 callers | Abstract when 3+ callers exist |
     | Flat structure | Deep nesting | Each nesting level doubles cognitive load |
  3. Add self-check: "Before completing, ask: did I add complexity that wasn't requested?"
- **Files touched**:
  - `skills/philosophy/SKILL.md` (new, ~40 lines)
- **Acceptance criteria**:
  - `make audit-budget` shows < 80% utilisation
  - `make validate-skills` passes
  - Skill is < 50 lines total
  - Every entry in the table corrects a known LLM bias (not generic advice)
- **Depends on**: 0.1 (budget check)
- **Estimated effort**: S

### 2.2 Go Corrective References (Error Handling, Concurrency, Testing)

- **What**: Add a `skills/go-engineer/references/corrective-patterns.md` file (~50 lines) with "Prefer X over Y" tables for the 3 areas where Go agents most commonly deviate from expert practice.
- **Why**: The go-engineer skill body is only 136 lines after trimming. The deleted content included specific error handling patterns, concurrency safety patterns, and testing patterns that corrected the model's bias toward popular-but-wrong approaches. Reference files are lazy-loaded (only when the skill is active), so they do not count toward the 16K budget.
- **How**:
  1. Create `skills/go-engineer/references/corrective-patterns.md` with three tables:
     - **Error Handling** (~15 entries): `fmt.Errorf("failed: %w", err)` over `return err`, structured error types over string matching, sentinel errors over string comparison, `errors.As` over type assertion
     - **Concurrency** (~10 entries): `errgroup.Group` over naked goroutines, `context.WithTimeout` over `time.After`, channel-of-one over mutex for simple sync, `sync.Once` over init flags
     - **Testing** (~10 entries): table-driven over individual cases, `require` over `assert` (fail fast), `testify/suite` over `TestMain`, `t.Cleanup` over `defer` in tests, `httptest.NewServer` over mocking HTTP
  2. Reference from `go-engineer/SKILL.md`: add a line "See `references/corrective-patterns.md` for expert patterns."
- **Files touched**:
  - `skills/go-engineer/references/corrective-patterns.md` (new, ~50 lines)
  - `skills/go-engineer/SKILL.md` (add 1 reference line)
- **Acceptance criteria**:
  - Each entry is a concrete "Prefer X over Y" with a brief rationale
  - No entries that duplicate what linters enforce (Phase 1 handles those)
  - No generic Go advice — only patterns where LLMs systematically choose the wrong option
- **Depends on**: 0.2 (baseline tasks reveal which patterns agents get wrong)
- **Estimated effort**: S

### 2.3 Python Corrective References

- **What**: Add `skills/python-engineer/references/corrective-patterns.md` (~40 lines) for type hints, error handling, and async patterns.
- **Why**: Same rationale as 2.2. Python agents frequently produce code with `Any` types, bare excepts, and synchronous-style async code.
- **How**:
  1. Create reference file with tables:
     - **Type Hints** (~10 entries): `str | None` over `Optional[str]` (3.10+), `list[int]` over `List[int]`, `Protocol` over `ABC` for structural typing, `TypeVar` with bounds over `Any`
     - **Error Handling** (~10 entries): specific exceptions over `Exception`, `ExceptionGroup` over nested try/except (3.11+), custom exception hierarchy over string messages, `contextlib.suppress` over empty except
     - **Async** (~10 entries): `asyncio.TaskGroup` over `gather` (3.11+), structured concurrency over fire-and-forget, `async with` for resource management, timeout on every `await`
  2. Reference from `python-engineer/SKILL.md`
- **Files touched**:
  - `skills/python-engineer/references/corrective-patterns.md` (new, ~40 lines)
  - `skills/python-engineer/SKILL.md` (add 1 reference line)
- **Acceptance criteria**: Same as 2.2 but for Python patterns
- **Depends on**: 0.2
- **Estimated effort**: S

### 2.4 Frontend Corrective References

- **What**: Add `skills/frontend-engineer/references/corrective-patterns.md` (~40 lines) for React patterns, state management, and accessibility.
- **Why**: Frontend agents commonly produce code with excessive `useEffect`, prop drilling where context suffices, missing ARIA attributes, and uncontrolled-vs-controlled component confusion.
- **How**:
  1. Create reference file with tables:
     - **React Patterns** (~10 entries): derived state over `useEffect` + `useState`, `useMemo`/`useCallback` only when measured, composition over inheritance, server components over client when no interactivity needed
     - **State** (~10 entries): URL state over local state for shareable views, `useReducer` over complex `useState` chains, Zustand/Jotai over Redux for new projects (per project prefs), form libraries over manual form state
     - **Accessibility** (~10 entries): semantic HTML over `div` + ARIA, `button` over `div[onClick]`, visible focus indicators, skip navigation links, `aria-live` for dynamic content
  2. Reference from `frontend-engineer/SKILL.md`
- **Files touched**:
  - `skills/frontend-engineer/references/corrective-patterns.md` (new, ~40 lines)
  - `skills/frontend-engineer/SKILL.md` (add 1 reference line)
- **Acceptance criteria**: Same as 2.2 but for Frontend patterns
- **Depends on**: 0.2
- **Estimated effort**: S

### 2.5 Security Reference Skill

- **What**: Create `skills/security-reference/SKILL.md` (~120 lines) as an on-demand skill (NOT alwaysApply) that provides positive-framing security patterns: "use X" rather than "don't use Y."
- **Why**: The original security content was deleted during trimming. Security patterns are corrective by nature — the model's training data includes both secure and insecure patterns, and the insecure ones are more common (Stack Overflow). Pink elephant research shows "don't use eval" is less effective than "use ast.literal_eval for parsing untrusted strings." Positive framing avoids the priming effect.
- **How**:
  1. Create skill with:
     - Description: trigger on security-related queries, auth, encryption, input validation
     - Body: "Use X for Y" tables organised by concern:
       - **Input Validation**: parameterised queries for SQL, allowlists for file paths, JSON schema validation for API input
       - **Authentication**: bcrypt/argon2 for passwords, JWT with short expiry + refresh tokens, CSRF tokens for state-changing forms
       - **Secrets**: environment variables for runtime secrets, secrets manager for production, `.env` + `.gitignore` for development
       - **HTTP**: HTTPS everywhere, CORS allowlist (not wildcard), CSP headers, rate limiting
       - **Crypto**: `crypto/rand` not `math/rand` for tokens, AES-GCM for symmetric, RSA-OAEP/ECDSA for asymmetric
  2. Reference files for language-specific patterns (Go, Python, TS)
- **Files touched**:
  - `skills/security-reference/SKILL.md` (new, ~120 lines)
  - `skills/security-reference/references/` (optional language-specific files)
- **Acceptance criteria**:
  - Every entry uses positive framing ("use X for Y")
  - No "don't" or "never" as primary instruction (those go in hooks)
  - `make audit-budget` shows < 80%
  - `make validate-skills` passes
- **Depends on**: 0.1
- **Estimated effort**: M

### 2.6 Reliability Reference Skill

- **What**: Create `skills/reliability-reference/SKILL.md` (~100 lines) as an on-demand skill for timeouts, retries, circuit breakers, and graceful degradation.
- **Why**: Reliability patterns are among the most commonly omitted by LLMs — the model produces code that works in happy paths but fails in production under load, partial failure, or network issues. These patterns are corrective (not tutorials).
- **How**:
  1. Create skill with "Use X for Y" tables:
     - **Timeouts**: every outbound call gets a timeout, context propagation through the call chain, deadline-aware middleware
     - **Retries**: exponential backoff with jitter, retry budget (max 3), idempotency keys for retried writes
     - **Circuit Breakers**: per-dependency circuit breakers, half-open probe strategy, fallback responses
     - **Graceful Degradation**: health check endpoints, readiness vs. liveness probes, graceful shutdown with drain period
  2. Language-specific examples in `references/` subdirectory
- **Files touched**:
  - `skills/reliability-reference/SKILL.md` (new, ~100 lines)
  - `skills/reliability-reference/references/` (optional)
- **Acceptance criteria**:
  - Every entry is actionable ("add timeout to HTTP client" not "consider adding timeouts")
  - No overlap with semgrep rules from Phase 1.3 (those enforce, this guides)
  - `make audit-budget` shows < 80%
- **Depends on**: 0.1
- **Estimated effort**: M

### 2.7 Budget Recheck After All Additions

- **What**: Run `make audit-budget` after all Phase 2 additions and verify the 16K budget is not exceeded.
- **Why**: Phase 2 adds 1 alwaysApply skill (philosophy) and 2 on-demand skills (security-reference, reliability-reference). The corrective reference files are lazy-loaded and do NOT count toward the budget, but the descriptions do.
- **How**:
  1. Run `make audit-budget`
  2. If utilisation > 80%, trim descriptions of least-triggered skills (check eval data from Phase 0)
  3. If utilisation > 90%, merge or remove low-value skills
- **Files touched**: potentially any `SKILL.md` description (only if budget exceeded)
- **Acceptance criteria**: Budget utilisation < 80%
- **Depends on**: 0.1, 2.1, 2.5, 2.6
- **Estimated effort**: S

## Phase 3: Reviewer Hardening

Research shows blind review + adversarial persona is the strongest evidence-based approach for reducing self-preference bias (192K assessments, Science Advances). This phase applies those findings to the 3 reviewer agents.

### 3.1 Blind Review Protocol for All Reviewer Agents

- **What**: Add a "Blind Review Protocol" section to all 3 reviewer agents (`code_reviewer_go.md`, `code_reviewer_python.md`, `code_reviewer_frontend.md`) that instructs the reviewer to:
  1. Read the code without knowing who/what wrote it
  2. Adopt an adversarial persona: "Your job is to find problems, not confirm quality"
  3. Assume the code is wrong until proven otherwise
  4. Check against concrete criteria (not vibes)
- **Why**: Wataoka et al. (2024) demonstrated systematic self-preference bias in LLMs — they overrate their own output. Blind review strips authorship cues. Adversarial framing counters the model's default sycophantic tendency. This is the single highest-evidence intervention for review quality.
- **How**:
  1. Add ~20 lines to each reviewer agent after the existing review modes section:
     ```markdown
     ## Blind Review Protocol

     1. **Strip authorship**: Do not consider who wrote this code. Treat it as anonymous.
     2. **Adversarial stance**: Your job is to find problems. A review that finds nothing is suspicious — re-examine with fresh eyes.
     3. **Concrete criteria only**: Every finding must reference a specific rule, pattern, or principle. "This looks wrong" is not a finding.
     4. **Evidence for PASS**: If a checkpoint passes, state WHY it passes (what you verified). PASS without justification is not allowed.
     ```
  2. Update the checkpoint format to require justification on PASS (see 3.2)
- **Files touched**:
  - `agents/code_reviewer_go.md` (add ~20 lines)
  - `agents/code_reviewer_python.md` (add ~20 lines)
  - `agents/code_reviewer_frontend.md` (add ~20 lines)
- **Acceptance criteria**:
  - Each reviewer has the blind review protocol section
  - Protocol requires concrete criteria for every finding
  - Protocol requires evidence for PASS verdicts
- **Depends on**: none
- **Estimated effort**: S

### 3.2 Forced Explanation Requirement on PASS Checkpoints

- **What**: Modify the checkpoint format in all reviewer agents so that PASS verdicts MUST include a justification statement. "PASS" alone is rejected — it must be "PASS: verified X by doing Y."
- **Why**: The model's path of least resistance is to say "PASS" and move on. Requiring explanation forces actual verification. Reflexion (Shinn et al., NeurIPS 2023) showed that concrete external signals anchor self-reflection — the explanation itself becomes the external signal (it either makes sense or it doesn't).
- **How**:
  1. Update the checkpoint tables in all 3 reviewers. Change format from:
     ```
     | F3 | Error Handling | Every error return has context wrapping | PASS/FAIL |
     ```
     to:
     ```
     | F3 | Error Handling | Every error return has context wrapping | PASS: [evidence] or FAIL: [finding] |
     ```
  2. Add instruction: "A PASS without evidence is treated as SKIP. You must state what you checked and what you found."
- **Files touched**:
  - `agents/code_reviewer_go.md` (modify checkpoint tables)
  - `agents/code_reviewer_python.md` (modify checkpoint tables)
  - `agents/code_reviewer_frontend.md` (modify checkpoint tables)
- **Acceptance criteria**:
  - Every checkpoint in every reviewer requires evidence for PASS
  - "PASS" without colon is documented as invalid
- **Depends on**: 3.1 (part of blind review protocol)
- **Estimated effort**: S

### 3.3 Downgrade Coverage from Gate to Diagnostic

- **What**: In test writer agents and reviewer checkpoints, change test coverage from a gate (blocks completion) to a diagnostic (reported but does not block).
- **Why**: 100% coverage can yield 4% mutation score. Coverage measures execution, not verification. Using coverage as a gate incentivises the model to write tests that execute code without actually testing it. Coverage as a diagnostic still provides information without creating perverse incentives.
- **How**:
  1. In `unit_tests_writer_go.md`, `unit_tests_writer_python.md`, `unit_tests_writer_frontend.md`:
     - Change coverage from "must be >= X%" to "report coverage percentage"
     - Add note: "Coverage is informational. High coverage with weak assertions is worse than moderate coverage with strong assertions."
  2. In reviewer agents: remove coverage threshold checks from FAIL criteria
  3. Add to `code-writing-protocols/SKILL.md`: "Coverage is a diagnostic, not a target. Focus on assertion quality."
- **Files touched**:
  - `agents/unit_tests_writer_go.md`
  - `agents/unit_tests_writer_python.md`
  - `agents/unit_tests_writer_frontend.md`
  - `agents/code_reviewer_go.md`
  - `agents/code_reviewer_python.md`
  - `agents/code_reviewer_frontend.md`
  - `skills/code-writing-protocols/SKILL.md` (~3 lines)
- **Acceptance criteria**:
  - No agent uses coverage as a gate condition
  - Coverage is still reported (not removed)
  - Assertion quality is emphasised over coverage quantity
- **Depends on**: none
- **Estimated effort**: S

### 3.4 Self-Critique Checklist in code-writing-protocols

- **What**: Add a 5-item self-critique checklist to `code-writing-protocols/SKILL.md` that agents run before declaring completion. Each item is a concrete binary check (yes/no), not a subjective quality assessment.
- **Why**: Constitutional AI research shows self-critique works for concrete binary criteria. The checklist must be things the model CAN self-verify (unlike "is this good code?"). Madaan et al. (Self-Refine, NeurIPS 2023) showed iteration 1-2 gains with concrete feedback.
- **How**:
  1. Add to `code-writing-protocols/SKILL.md`:
     ```markdown
     ## Pre-Completion Self-Critique (5 Binary Checks)

     Before declaring task complete, answer each YES or NO:

     1. **Does every outbound call have a timeout or context?** (grep for http.Get, requests.get, fetch without timeout)
     2. **Does every error path wrap with context?** (grep for `return err` without fmt.Errorf)
     3. **Did I add any code that wasn't requested?** (compare diff against task requirements)
     4. **Are there any narration comments in my changes?** (re-read diff for "// Get", "# Create", "// Initialize")
     5. **Does the code compile/type-check cleanly?** (run build/typecheck command)

     If ANY answer is wrong, fix before completing. Do not explain — just fix.
     ```
  2. These checks overlap with hooks intentionally (defence in depth) — hooks catch at write time, checklist catches at completion time
- **Files touched**:
  - `skills/code-writing-protocols/SKILL.md` (add ~15 lines)
- **Acceptance criteria**:
  - Each check is binary (yes/no)
  - Each check is mechanically verifiable (grep, build, diff)
  - No subjective quality assessments
- **Depends on**: none
- **Estimated effort**: S

## Phase 4: Self-Reflection Infrastructure

All self-reflection is grounded in external signals per Huang et al. (ICLR 2024). No self-correction without tool interaction.

### 4.1 Instruction Adherence Tracking

- **What**: Create `bin/track-skill-adherence` — a script that analyses agent output (from a completed task) and checks which loaded skills had their instructions reflected in the output.
- **Why**: We need to know which skills actually influence agent behaviour and which are ignored. This is the "dark skills" problem — skills that are loaded but produce no observable effect. Without this data, we cannot prioritise skill improvements.
- **How**:
  1. Script takes a conversation transcript (from `claude --output-format json`) as input
  2. For each skill that was loaded (visible in system prompt), checks for adherence signals:
     - `code-comments`: no narration comments in produced code
     - `project-preferences`: correct libraries used (zerolog, testify, etc.)
     - `lint-discipline`: no suppression directives added
     - `go-engineer`: errors wrapped, context propagated
     - etc.
  3. Output: per-skill adherence score (0-1) based on signal detection
  4. Aggregate across multiple runs to build a profile
- **Files touched**:
  - `bin/track-skill-adherence` (new)
  - `future_projects/adherence-signals.md` (new, defines signals per skill)
- **Acceptance criteria**:
  - Script processes a real conversation transcript
  - Produces per-skill adherence scores
  - Identifies at least 1 "dark skill" (loaded but 0 adherence signals)
- **Depends on**: 0.2 (needs baseline task outputs to analyse)
- **Estimated effort**: L

### 4.2 "Dark Skills" Report

- **What**: Using data from 4.1, generate a report identifying skills that are loaded but never influence output. These are candidates for removal, rewrite, or merging.
- **Why**: Skills that don't influence output are pure cost (context tokens) with zero benefit. Removing or rewriting them frees budget and reduces noise. Wataoka et al. (2024) noted that more instructions can degrade performance when they're not acted upon.
- **How**:
  1. Run 4.1 across all baseline tasks from 0.2
  2. Aggregate results into `future_projects/dark-skills-report.md`
  3. For each dark skill, recommend: remove, rewrite description (trigger problem), merge into another skill, or convert to reference file
  4. Prioritise rewrites by eval data (Phase 0.3/0.4)
- **Files touched**:
  - `future_projects/dark-skills-report.md` (new)
- **Acceptance criteria**:
  - Report covers all 42 skills
  - Each dark skill has a concrete recommendation
  - Recommendations are backed by adherence data, not guesses
- **Depends on**: 4.1, 0.2
- **Estimated effort**: M

### 4.3 Failure-Driven Skill Refinement (Reflexion Pattern)

- **What**: Create a command `/refine-skill` that takes a skill name and a failing eval, analyses why the skill failed, and proposes a targeted fix to the skill description or body.
- **Why**: Reflexion (Shinn et al., NeurIPS 2023) works when anchored in concrete external signals. Eval failures ARE concrete signals. The loop: eval fails -> analyse failure -> propose skill fix -> re-run eval -> verify improvement. This is the only self-improvement pattern with strong evidence.
- **How**:
  1. Create `commands/refine-skill.md` that:
     - Takes skill name as argument
     - Runs trigger evals for that skill
     - Identifies failing queries
     - Reads the skill's SKILL.md
     - Proposes a targeted fix (description change, body change, or both)
     - Runs eval again to verify improvement
     - Uses `eval-compare` (from 0.4) to confirm no regressions
  2. The command MUST NOT auto-apply changes — it proposes and waits for approval (per User Authority Protocol)
- **Files touched**:
  - `commands/refine-skill.md` (new)
- **Acceptance criteria**:
  - Command runs evals, identifies failures, proposes fixes
  - Proposals include before/after eval comparison
  - Changes require explicit user approval
  - At least 1 skill improved by >= 1 passing eval after refinement
- **Depends on**: 0.3, 0.4
- **Estimated effort**: M

### 4.4 Pairwise Contradiction Detection

- **What**: Create `bin/detect-contradictions` that scans all skill SKILL.md files for contradictory instructions (e.g., one skill says "use interfaces sparingly" while another says "define interfaces for every service boundary").
- **Why**: With 42 skills, contradictions are inevitable and invisible. When contradictory instructions are both loaded, the model resolves the conflict unpredictably. Detection allows intentional resolution.
- **How**:
  1. Script extracts all imperative statements from skills (lines starting with "Use", "Never", "Always", "Prefer", "Avoid")
  2. Groups statements by topic (error handling, interfaces, testing, etc.)
  3. Uses keyword overlap to identify potential contradictions within each topic
  4. Outputs pairs with the conflicting text for human review
  5. NOTE: This is a heuristic approach (keyword-based), not LLM-based — per research, the model cannot reliably identify its own blind spots
- **Files touched**:
  - `bin/detect-contradictions` (new)
- **Acceptance criteria**:
  - Script finds at least 1 real contradiction (verified by human review)
  - False positive rate < 50% (most flagged pairs are actual conflicts or near-conflicts)
  - Runs in < 5 seconds
- **Depends on**: none
- **Estimated effort**: M

### 4.5 Shadow Evaluation: A/B Test Skill Removal

- **What**: Create a process for testing the impact of removing individual skills by running the same task with and without the skill, then comparing output quality.
- **Why**: Some skills may be net negative (adding noise without improving output). The only way to know is to test removal. This is the strongest form of external validation — does the output get better or worse without this skill?
- **How**:
  1. Document the process in `future_projects/shadow-eval-protocol.md`:
     - Select a skill to test
     - Temporarily rename/move its SKILL.md
     - Run baseline tasks from 0.2
     - Compare output quality (eval scores, human review)
     - Restore the skill
     - Record results
  2. Start with skills identified as "dark" in 4.2
  3. This is a manual process (no automation needed — the value is in the judgment, not the tooling)
- **Files touched**:
  - `future_projects/shadow-eval-protocol.md` (new)
- **Acceptance criteria**:
  - Protocol is documented and reproducible
  - At least 3 skills tested via shadow evaluation
  - Results recorded with clear better/worse/same verdict
- **Depends on**: 4.2, 0.2
- **Estimated effort**: L (requires multiple task runs and human evaluation)

## Phase 5: Testing Methodology (Deferred)

These steps are deferred pending Phase 0 data. If baseline measurements show that test quality is NOT a primary issue, deprioritise this phase entirely.

### 5.1 Test-First Flow (Test Writer Before SE)

- **What**: Modify the `/implement` command flow to optionally run the test writer BEFORE the software engineer, producing test skeletons that the SE must make pass.
- **Why**: Test-first (TDD-like) flow means the SE has concrete targets. This anchors implementation in external signals (test failures) rather than internal judgment. However, this only helps if baseline data shows SE agents produce code that passes tests but misses requirements.
- **How**: Add `--test-first` flag to `/implement` that reverses the SE/test-writer order
- **Files touched**: `commands/implement.md`, `skills/workflow/SKILL.md`
- **Acceptance criteria**: `/implement --test-first` runs test writer first, SE second
- **Depends on**: 0.2 (baseline data must show this is needed)
- **Estimated effort**: M

### 5.2 Mutation-Resistant Test Writing

- **What**: Add mutation awareness to test writer skills — instruct test writers to write tests that verify behaviour, not just exercise code paths.
- **Why**: Mutation score > coverage for measuring test quality. But per research, full mutation testing is too slow for the agent pipeline (1000 mutants x 30s = 8h). Instead, teach the test writer to think about mutations: "Would this test still pass if I changed `>` to `>=`?"
- **How**: Add ~15 lines to each test writer skill about mutation-resistant assertions
- **Files touched**: `skills/go-testing/SKILL.md`, `skills/python-testing/SKILL.md`, `skills/frontend-testing/SKILL.md`
- **Acceptance criteria**: Test writers produce tests with boundary-value assertions
- **Depends on**: 0.2
- **Estimated effort**: S

### 5.3 Fuzz Testing Gate

- **What**: Add optional fuzz testing step to Go test writers for functions that parse external input.
- **Why**: Go has built-in fuzz testing. 60 seconds of fuzzing with 0 crashes is a meaningful signal.
- **How**: Add fuzz test templates to `go-testing` skill references
- **Files touched**: `skills/go-testing/SKILL.md`, `skills/go-testing/references/fuzz-templates.go`
- **Acceptance criteria**: Test writer produces fuzz tests for parsing functions
- **Depends on**: 0.2
- **Estimated effort**: S

### 5.4 Mutation Testing Gate (Changed Files Only)

- **What**: Add optional mutation testing step that runs only on changed files with a 60-second cap.
- **Why**: Full mutation testing is prohibitive, but scoped mutation testing on a few changed files is feasible. 60s cap prevents blocking.
- **How**: Integrate `go-mutesting` or `mutmut` (Python) as optional post-test step
- **Files touched**: `bin/mutation-gate` (new), reviewer agent checkpoint tables
- **Acceptance criteria**: Runs in < 60s, reports mutation score for changed files only
- **Depends on**: 0.2, 5.2
- **Estimated effort**: M

### 5.5 Information Barriers (Conditional)

- **What**: If Phase 0 data shows that SE agents produce better code when they cannot see existing tests (or vice versa), implement file-level access restrictions.
- **Why**: Theoretical benefit from blind implementation. But research evidence is limited for AI agents, and the risk of wrong function signatures and imports is high. Only proceed if baseline data supports it.
- **How**: Use `allowed-tools` restrictions in agent frontmatter to limit file access patterns
- **Files touched**: Agent frontmatter modifications
- **Acceptance criteria**: A/B test shows measurable improvement
- **Depends on**: 0.2 (must have evidence this helps)
- **Estimated effort**: M

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | 16K budget overflow — skills silently dropped from system prompt | Medium | Critical | Phase 0.1 audit script, 2.7 recheck after every addition, CI integration |
| R2 | Complexity explosion — 30+ changes constitute a rewrite | High | High | Strict phase gating. Phase 0 must complete before Phase 1 starts. Each phase has concrete acceptance criteria. Skip phases that baseline data doesn't support |
| R3 | Self-improvement loop amplifying bad signals | Medium | High | All reflection grounded in external signals (evals, linters, human review). No self-assessment without tool verification. Huang et al. constraint enforced |
| R4 | Model upgrade breaks optimised prompts | Medium | Medium | Phase 1.4 pins model versions. Upgrades become explicit events with eval comparison (0.4) |
| R5 | Eval harness testing the wrong things | Medium | Medium | Phase 0.2 baselines from real tasks, not synthetic benchmarks. Content evals (0.3) test actual output, not just triggering |
| R6 | Analysis paralysis — researching without shipping | High | High | Each step has concrete deliverables and acceptance criteria. Time-box Phase 0 to 2 weeks. If baselines aren't done in 2 weeks, proceed with Phase 1 anyway (linter rules are safe without baselines) |
| R7 | Corrective references become tutorials | Medium | Low | Hard limit: 50 lines per reference file. "Prefer X over Y" format only. No explanations longer than 1 sentence per entry |
| R8 | Reviewer hardening makes reviews too slow | Low | Medium | Blind review adds ~20 lines per agent. Forced explanation is a format change, not additional work. Monitor review completion times |
| R9 | Dark skills report recommends removing useful skills | Medium | Medium | Shadow evaluation (4.5) tests removal impact before committing. No skill removed without A/B evidence |
| R10 | Eval comparison shows no improvement from changes | Medium | Low | This is actually a good outcome — it means the current system is better than expected. Document and redirect effort elsewhere |

## Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| D1 | Phase 0 before any changes | Measure first, then improve. The previous research session spent 100% on analysis and 0% on implementation because it never established what was actually failing | Jump straight to fixes (rejected: no way to measure impact) |
| D2 | Linters over LLM-based hooks for pattern detection | Model-independent, faster (ms vs seconds), community-maintained, deterministic. Linters catch 100% of violations; skill instructions catch ~70% | Haiku prompt hooks (rejected: guidance dressed as enforcement, adds latency, consumes tokens, subjective) |
| D3 | Blind review over cross-model review | Strongest evidence base (192K assessments, Science Advances). No capability loss — same model, different framing | Sonnet reviewing Opus (rejected: weaker model reviewing stronger = shallower reviews) |
| D4 | Mutation score over coverage as quality metric | Coverage measures execution, mutation score measures verification. 100% coverage can yield 4% mutation score | Coverage gates (rejected: creates perverse incentive to write tests that execute but don't verify) |
| D5 | External signals required for all self-reflection | Huang et al. (ICLR 2024): LLMs cannot self-correct reasoning without external feedback. Performance sometimes degrades with pure self-reflection | Self-critique without tools (rejected: same blind spots in execution and evaluation) |
| D6 | Corrective references as lazy-loaded files, not skill body | Reference files don't count toward 16K budget. They're loaded only when the skill is active. This allows richer content without budget pressure | Inline in SKILL.md (rejected: inflates always-loaded content), separate skills (rejected: more descriptions = more budget) |
| D7 | Positive framing for security ("use X") over negative ("don't use Y") | Pink elephant effect: "don't use eval" primes the model on eval. "Use ast.literal_eval for untrusted strings" provides the correct action directly | Negative framing (rejected: research shows it primes the unwanted behaviour) |
| D8 | Symlinks for deployment (already done) | Bidirectional editing, zero-cost propagation. Changes in repo immediately visible in `~/.claude/` | rsync --delete (rejected: one-directional, requires `make run`) |
| D9 | Defer testing methodology (Phase 5) pending data | No evidence that test quality is the primary issue. If baselines show agents produce good tests, Phase 5 ROI is low | Implement immediately (rejected: premature without evidence of need) |
| D10 | No agent templatisation in this plan | Clear ROI but orthogonal concern. Can be done independently without affecting knowledge restoration or self-improvement | Include in this plan (rejected: scope creep, different skill set needed) |

## References

### Self-Reflection Research

1. **Huang et al.** "Large Language Models Cannot Self-Correct Reasoning Yet." ICLR 2024. — LLMs cannot self-correct without external feedback. Performance sometimes degrades.
2. **Gou et al.** "CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing." ICLR 2024. — Self-correction only works with tool interaction. Without tools: +0 or negative.
3. **Madaan et al.** "Self-Refine: Iterative Refinement with Self-Feedback." NeurIPS 2023. — Most gains in iterations 1-2. Diminishing returns after.
4. **Shinn et al.** "Reflexion: Language Agents with Verbal Reinforcement Learning." NeurIPS 2023. — Works when anchored in concrete external signals (test pass/fail).
5. **Wataoka et al.** "Self-Preference Bias in LLM-as-a-Judge." 2024. — LLMs systematically overrate their own outputs.

### Constitutional AI & Instruction Following

6. **Bai et al.** "Constitutional AI: Harmlessness from AI Feedback." Anthropic, 2022. — Self-critique works for concrete binary criteria, not vague quality.
7. **Lee Han Chung.** "Claude Skills Deep Dive." 2025. — 15,000-character (now 16,000) limit for skill descriptions. Description is the primary trigger mechanism.

### Review & Testing Research

8. **Blind Review Study.** Science Advances, 192K assessments. — Blind review + adversarial persona strongest for bias reduction.
9. **Mutation Testing.** Various. — Mutation score > coverage for measuring test quality. Runtime prohibitive for CI (1000 mutants x 30s = 8h).

### Internal References

10. `future_projects/getting_back_old_knowledge.md` — Contradiction analysis from the original research session (12 risks, 8 wrong assumptions identified)
11. `future_projects/conversation.md` — Full 13K-line research conversation with findings on knowledge restoration, enforcement architecture, and self-improvement loops
12. `skills/skill-builder/references/anthropic-skill-authoring.md` — Official Anthropic guidance on skill descriptions, trigger mechanisms, and context budget