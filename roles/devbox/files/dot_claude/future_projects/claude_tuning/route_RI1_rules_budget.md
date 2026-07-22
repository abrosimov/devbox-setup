# Route RI1 — Rules-budget instrumentation (deep-dive)

**Status:** implemented 2026-07-21. Script `bin/rules_budget.py`; Makefile target `rules-budget`; baseline captured in `rules_budget_baseline.md`. Ready to consume for W2-W5 decisions. Moved to RI2 (see `route_RI2_always_on_audit.md`).
**Wave:** W1 (measure first).
**FPF position:** for W1, `selectedRoute = RI1`. `routeRationale`: *"Without a baseline we cannot know whether the config is over budget, so every downstream decision (W2-W5) would be gut-feel."*
**Serves PCs:** PC7 (instruction budget invisible) — primary; PC8 (always-on load asymmetry) — secondary.
**Cost:** Low (single Python script, ~1-2 hours to write).

## Purpose

Produce a baseline count of "rule-like statements" across the `dot_claude/` config tree, broken down by artefact and by always-on vs trigger-loaded reach. Compare aggregate against the Anthropic-reported budget (~150-200 concurrent instructions reliably followed by frontier models — see `research_pattern_language.md` [45]).

## Why first

Every route in W2-W5 (structural, content, hooks) implicitly assumes the config either is or is not over-budget:

- W2 (`problem:` + `related:` fields) — adds new tokens; we want to know if we can afford them.
- W3 (retire ceremony slots) — we want to know if the retirement actually moves the number.
- W4 (split UAP) — the main justification is budget reduction; without a number, we cannot verify the split delivered.

RI1 is not a fix in itself. It is the meter that lets us judge every other fix.

## Functional spec

**Input.** `roles/devbox/files/dot_claude/` tree.

**Output.** A report containing:

1. Per-artefact rule count (heuristic-based — see Q-RI1-1).
2. Classification per artefact: always-on vs trigger-loaded (from the `alwaysApply` frontmatter for skills; agents / commands classified by call-site).
3. Classification per rule: hard (MUST / SHALL / NEVER) vs soft (SHOULD / prefer / avoid).
4. Aggregate totals:
   - always-on rule count (upper bound — sum of rules in artefacts loaded every session).
   - triggered rule count (per-skill; informational, not summed).
   - hard vs soft split.
5. Comparison to the 150-200 threshold; flag if over.
6. Top-N offenders (artefacts with the largest rule count).

**Non-goals (v1).**

- Behavioural benchmark — this measures rule-count, not adherence. Adherence is `make eval-skills` territory.
- Automatic trimming or suggestion of rules to cut.

## Implementation shape (candidate)

- **Location.** `roles/devbox/files/dot_claude/bin/rules_budget.py` (existing uv project).
- **Runner.** `uv run --project roles/devbox/files/dot_claude/bin python roles/devbox/files/dot_claude/bin/rules_budget.py`.
- **Makefile target.** `make rules-budget` (mirrors `make validate-claude`, `make eval-skills`).
- **Output format.** Markdown table to stdout by default; `--json` flag for tooling; `--baseline` flag to write to `future_projects/claude_tuning/rules_budget_baseline.md`.
- **Deterministic.** Same input → same output. No wall-clock, no non-deterministic ordering.
- **Fast.** <5 s for the full tree (~90 artefacts, ~150 KB text).

## Deliverables

1. Script — `bin/rules_budget.py`.
2. Baseline artefact — `future_projects/claude_tuning/rules_budget_baseline.md` (first run; subsequent runs comparable to it).
3. Makefile target — `make rules-budget`.
4. In-script doc block — documents *what counts as a rule* (the heuristic). This is load-bearing and must remain visible.

## Success criteria

- Baseline number produced.
- Reproducible on any checkout.
- Rule-heuristic documented and defensible (a reviewer could re-implement it from the doc block alone).
- Runs under 5 seconds.

## Anti-patterns to avoid (`CC-B.4.1-5` discipline — do not let this route silently morph into another)

- **False precision.** Counting rules ≠ measuring adherence. The number is orientative, not diagnostic.
- **Goodhart's Law.** Optimising *for* a lower count can delete needed rules. Guard: pair every removal decision with the specific behaviour that rule was preventing.
- **Static-analysis blindness.** Prose can hide rules (*"we always X"* is imperative but not obviously so). The heuristic will miss some; documenting this limitation is required.
- **Scope creep.** RI1 measures; it does not decide. Do not extend it into an auto-trimming tool in v1.

## Open questions (resolved 2026-07-21)

### Q-RI1-1 — What counts as a "rule" / imperative statement?

- **A.** Sentences starting with imperative verbs (MUST, SHALL, DO, USE, AVOID, NEVER, ALWAYS, PREFER, DO NOT, ...). Simple; may miss embedded rules in prose.
- **B.** Any sentence containing modal auxiliaries (MUST, SHOULD, WILL, MAY, SHALL) with a 2nd-person or infinitive complement. Broader; risks false positives on descriptive prose.
- **C.** Any bullet point in an "Instructions" / "Rules" / "Protocol" section, regardless of grammatical shape. Section-header-driven; misses rules outside these sections.
- **D. (Recommended)** Combination of A ∪ C, deduplicated. Best coverage without B's false-positive risk.

**→ Decision: D.** Union of imperative-verb match (A) and bullet-in-rule-section match (C), deduplicated by line. Rationale: A alone under-counts prose-embedded rules; C alone under-counts rules outside named sections; B introduces false positives. Union balances coverage with precision. The heuristic and its known blind spots must be documented in the script doc-block (per Deliverable 4).

### Q-RI1-2 — Weighting scheme?

- **A.** Flat count. Simple; treats MUST and prefer equally.
- **B.** Weight by rule strength (MUST / NEVER × 2, SHOULD / prefer × 1). Aligns with model-attention research.
- **C.** Weight by scope (always-on rule × 3, trigger-loaded × 1). Aligns with context-budget reality.
- **D. (Recommended)** Report both — weighted (B + C combined) and unweighted (A). No free lunch on the choice.

**→ Decision: D.** Report three numbers per artefact: unweighted count (A), strength-weighted count (B: hard × 2, soft × 1), and scope-weighted aggregate (C: always-on × 3, trigger-loaded × 1). No single number can adjudicate; presenting all three keeps the interpretation explicit rather than baked into a hidden coefficient.

### Q-RI1-3 — Which artefact types to scan?

Recommended for v1:

- Skills (`skills/*/SKILL.md`) — yes.
- Agents (`agents/*.md`) — yes.
- Commands (`commands/*.md`) — yes.
- UAP (`USER_AUTHORITY_PROTOCOL.md`) — yes.
- `hooks.json` — logic, not prose; exclude.
- `settings.json` — configuration, not rules; exclude.
- `bin/*.py` — code; exclude.
- `templates/`, `docs/` — reference material; exclude.

Extend the scope if evidence warrants.

**→ Decision: as listed.** Skills, agents, commands, UAP included; hooks/settings/bin/templates/docs excluded. Scan roots are configurable via constants at the top of the script so scope can widen without rewrites.

### Q-RI1-4 — Script location?

- **A. (Recommended)** `roles/devbox/files/dot_claude/bin/rules_budget.py` — same uv project as existing hook scripts. Deployed to `~/.claude/bin/` and reachable from live sessions; same dependency management.
- **B.** `scripts/rules_budget.py` at repo root — Ansible-side, not deployed. Simpler but not reusable from a live Claude session.

**→ Decision: A.** `roles/devbox/files/dot_claude/bin/rules_budget.py` under the existing uv project. Deploys to `~/.claude/bin/` alongside hook scripts; live sessions can invoke it without leaving Claude Code.

### Q-RI1-5 — Invocation?

- **A. (Recommended)** Both: `make rules-budget` for daily use; direct `uv run …` as a fallback.
- **B.** Makefile target only.
- **C.** Direct invocation only.

**→ Decision: A.** `make rules-budget` as the ergonomic entry-point; direct `uv run --project roles/devbox/files/dot_claude/bin python roles/devbox/files/dot_claude/bin/rules_budget.py` as the always-available fallback (equivalent to how other hook scripts are invoked).

## Once questions answered, next actions

1. ~~Answer Q-RI1-1 through Q-RI1-5 in this file.~~ **Done 2026-07-21** (D, D, as-listed, A, A).
2. ~~Implement `bin/rules_budget.py`.~~ **Done.** Zero new dependencies (stdlib only).
3. ~~Add `make rules-budget` target.~~ **Done.** Also exposes `ARGS='...'` passthrough for `--json` / `--baseline PATH`.
4. ~~Run against current tree; capture output as `rules_budget_baseline.md`.~~ **Done.**
5. ~~Unit tests on synthetic markdown fixtures.~~ **Done** — `bin/test_rules_budget.py`, 37 tests, run under `test-claude-hooks`.
6. Deploy via `make claude-push` — *pending user; not run automatically.*
7. ~~Report the baseline number in this file; move to RI2 (always-on audit).~~ **Done — see Baseline results below.**

## Baseline results (2026-07-21)

| Scope | Artefacts | Flat | Hard | Soft | Strength-weighted |
|---|---:|---:|---:|---:|---:|
| Always-on | 6 | **119** | 28 | 91 | 147 |
| Trigger-loaded | 85 | 957 | 157 | 800 | 1114 |

**Always-on flat count: 119 — under the 150-200 budget** (~60% utilised). Full breakdown: `rules_budget_baseline.md`.

Key readings for downstream waves:

- **Headroom exists but is not large.** 60% used; adding one more `alwaysApply: true` skill or a large UAP section could push into range. W2 additions (`problem:` / `related:` frontmatter) do not add rules, so they are safe on this metric.
- **UAP is the largest always-on contributor** (56 rules / 47% of always-on budget). Any W4 UAP split (RS3) needs a before-vs-after measurement; RI1 provides the meter.
- **`code-writing-protocols` is the biggest trigger-loaded artefact** (157 rules — larger than UAP). Not on the always-on budget, but flags a review candidate for W3 (RC family).
- **Three of five always-on skills are code-writing scoped** (`code-comments`, `lint-discipline`, `lsp-navigation`). On a config-editing session (like this one) they are dead weight — direct input into RI2 (see `route_RI2_always_on_audit.md`).
