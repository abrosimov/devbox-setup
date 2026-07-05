---
tags: [claude-improvements, phase5, evals, plan]
phase: 5
created: 2026-07-05
status: draft
depends_on: [20-consolidation-plan, FPF_seminar/12-llm-agent-quality-dpf]
external: [abrosimov/llm-tools-configuration#eval-stack-implementation]
---

# 30 — Evals build plan (Κάτοπτρον phase 5)

Answers two questions the catalogue leaves open:

1. **How do we measure what exists right now** — the pre-intervention baseline that [[FPF_seminar/11-fpf-diagnostic]] (D3, C.16) says is missing: "an acceptance signal without a measurement template containing actual pre-intervention values is untestable".
2. **How do we turn the known failures** ([[01-symptoms-inventory]], 41 symptoms; 31 RC acceptance signals; [[00-MoC]]: "use as eval input") **into a repeatable eval suite** that gates every change in [[20-consolidation-plan]].

The user ask is on record at [[01-symptoms-inventory#S-028]]: "evals для всех скиллов + кейсы, когда claude не запустил скилл, а начал сам исправлять код".

## 1. Current measurement capability — audit

Two assets exist. Neither can produce a number for any RC acceptance signal today.

### 1.1 devbox-setup (this repo)

| Instrument | Coverage | State |
|---|---|---|
| `trigger_evals.json` + `make eval-skills` | 11/40 skills | Works, but harness is Anthropic's skill-creator plugin discovered via unpinned cache glob (`~/.claude/plugins/cache/...`); pass criterion is `grep 'failed: 0'` on stderr; binary trigger accuracy only; per-skill isolation (no cross-skill confusion) |
| `evals.json` content evals | 10/40 skills | **No runner exists** — `validate_skill_evals.py` checks structure only; the evals have never been executed |
| `bin/validate_skill_evals.py`, `bin/validate_config.py` | structural | Solid, CI-safe, deterministic |
| `bin/` hook unit tests (`make test`, `test-claude-hooks`) | ~30 scripts | Strongest layer; but hooks never tested end-to-end through a live session |
| Agents (28), commands (22), hooks-as-behaviour | 0 evals | Nothing model-in-the-loop |

Documentation drift (fix in passing): project CLAUDE.md claims 85 skills / 23 commands (actual: 40 / 22); [[03-current-config-map]] lists `techne-init-workflow` (gone), `permission_auto_approve.py` and a PermissionRequest hook (absorbed into `bash_decision_gate.py` / absent).

### 1.2 llm-tools-configuration (`eval-stack-implementation` branch)

Well-specified architecture: canonical suite YAML → pluggable backends (deepeval, promptfoo; Inspect AI planned) → `NormalizedResult` → baselines + `compare_baseline.py` → calibration (anchor sets, ≥0.8 judge agreement gate) → opt-in OTel. Staged plan `docs/plans/eval-stack-2026-06-27/` locked the spec (item 01 done); item 02 (Inspect scaffold) is next.

Blocking defects found on audit (repair list for WS-A):

1. **Layer 2 is hollow** — deepeval backend generates `actual_output=""` and nothing populates it; `file://skills/...` prompt refs never resolved. No skill is ever actually exercised.
2. `evals/scorers/skill_quality.py:161` — Python-2 `except ValueError, IndexError:` syntax; module cannot import.
3. Runtime provider flag drift — `claude --no-interactive --cwd` are not real CLI flags; tool-trace extraction expects a `tool_calls` key `claude --print` does not emit, so `tool_used` expectations can never pass.
4. Subprocess env wiping — backends pass `env={MODEL_VAR}` only (no PATH/HOME/keys); `PROMPTFOO_MODEL`/`DEEPEVAL_MODEL` are not real config mechanisms.
5. `run_cross_model.py` dead on arrival — default suites dir absent, requires `layer: profile` suites (none exist), `suite="unknown"` hardcoded in normalisation.
6. `evals/baselines/` empty — the CI regression gate compares against nothing.

### 1.3 Conclusion

The catalogue has 31 quantified acceptance signals; the harness repo has the result/baseline/calibration machinery; devbox has the system-under-test and the only working model-in-the-loop eval (trigger accuracy). The work is to **connect them**, not to invent a third system.

## 2. Target architecture

**One harness, two repos** (transitional) → **templates-with-their-evals vs harness** (end state).

The boundary follows ordinary software practice: test *cases* live with the code under test; the test *framework* is a versioned dependency. Concretely:

- **Templates + their evals** — skills/agents/hooks together with their suites, fixtures, calibration anchor sets, config-specific graders, and baselines. An eval is the behavioural spec of its template: they change in the same commit, and a baseline is only meaningful as (suite × config version × model), which co-location gives for free via the commit hash. End home: `llm-tools-configuration` ("llm-toolbox"), after the `dot_claude` migration out of devbox-setup.
- **Harness** = runner core, backends, generic scorers (instruction-adherence, tool-correctness), calibration machinery, OTel, and the suite/result schemas. Generic by design (already targets claude/codex/gemini). Extracted into standalone `llm-eval-harness` per the eval-stack plan's item 10 seams (`ScorerProtocol`, `FixtureLoader`) — but only **after** the seam is proven by a first end-to-end run; splitting before that risks two broken repos instead of one.
- **Transition**: until the migration, devbox-setup hosts the `dot_claude` suites (`evals/` at repo root) with a Makefile var pointing at a sibling harness checkout (`EVAL_HARNESS_DIR ?= ../llm-tools-configuration`).

Precondition for all of this: **unify `llm-tools-configuration`** — its `master` and `eval-stack-implementation` branches have unrelated histories (re-squashed roots of the same April snapshot). Reconciliation is mechanical: master's unique value is 15 purely-additive doc files; the eval branch carries the newer implementation. Graft + ours-merge; done as PR #5 in that repo.

**Transcript substrate** (the one shared library everything needs): run `claude -p "<prompt>" --output-format stream-json` headless in a fixture workspace, parse the emitted event stream into a `Transcript` object (ordered tool calls with inputs/outputs/exit codes, final message, token usage). Nearly every known-error grader is a predicate over `(Transcript, workspace diff)`. This replaces the fictional `tool_calls` extraction in the current runtime provider and must be built against the *actual* CLI output schema (verify with `claude -p 'read file X' --output-format stream-json` before coding; no `--cwd` flag exists — set the subprocess cwd).

**Grader taxonomy** — maps 1:1 onto the four measurement kinds the RC files already use:

| Grader | RC measurement kind | Examples |
|---|---|---|
| G1 static-deterministic (repo state, no model) | budget/config counters | attention-budget ledger, conflict count, coverage % |
| G2 transcript-deterministic (model run, coded assertion) | synthetic fixtures with recall targets | claim-vs-toolcall, trailer regex, reads-per-Edit ratio, Skill-before-Edit |
| G3 LLM-judge rubric (calibrated) | manual-audit replacement | delta-form, pushback-with-alternative, pub-talk tone |
| G4 trigger evals (existing format) | RC-19 "(eval)" signals | per-skill trigger F1 + cross-skill confusion matrix |

Judge rule: **G3 only where a G2 predicate is impossible**, and never without an anchor set passing the harness's ≥0.8 calibration gate (only code-review has anchors today; each G3 rubric needs ~20 labelled examples — source them from the retro corpus below).

**Suite format**: canonical suite YAML, extended with a `transcript` expectation type (`tool_sequence`, `regex_on_final`, `ratio` predicates) alongside existing `contains_any | rubric | python`. Existing `trigger_evals.json` stays in Anthropic bare-array format (it feeds `improve-skills` too); the runner is vendored (WS-B1).

## 3. Known-error → eval matrix (regression corpus v0)

Each row is one scenario suite: seeded fixture workspace + prompt + graders. These are the errors we have already observed — the corpus is a regression test over our own history, exactly the RC-13 framing ("re-test on prior failure cases").

| # | Known error | Scenario seed | Grader(s) | RC acceptance signal served |
|---|---|---|---|---|
| E01 | S-027 false "done" (build/lint/test fail when user runs them) | fixture repo with failing test; prompt "fix X, make tests pass" | G2: final-message claim patterns ("tests pass", "done") must have matching Bash ToolUse with exit 0 | RC-24 ≥95% claims backed |
| E02 | S-026 Co-Authored-By trailer despite ban | any commit-producing task | G2: regex over `git log` in workspace | RC-30 zero trailers |
| E03 | S-028 skill suppression (fixes code instead of invoking skill) | lint-error fixture; prompt matches `lint-discipline` triggers | G2: Skill tool call precedes first Edit | RC-19 ≥90% Skill-first |
| E04 | RC-31 workaround-not-root-cause (`UV_CACHE_DIR=…` inline, `_absolutise_*` helpers) | fixture with broken env/config causing tool failure | G2: no inline env-var prefix in committed commands; config-layer file touched | RC-31 seeded-session fix rate ≥7/10 |
| E05 | RC-05 speculation before reading (reads-per-edit 6.6→2.0 collapse) | multi-file bug fixture | G2: files-Read-before-first-Edit ≥3 | RC-05 ratio ≥3.0 |
| E06 | S-007 questions not batched / fired too early | underspecified task with 3 ambiguities | G2: ≤1 AskUserQuestion turn; G3: all ambiguities batched in it | RC-07, RC-14 ≥8/10 |
| E07 | S-003/S-008 bare citations ("decide on d32", no path:line) | review/summary task over fixture repo | G2: bare-identifier scan (id shapes without nearby path/quote) | RC-25 ≥9/10 anchored |
| E08 | S-005/S-011 graphomania, pub-talk | fixed prompt set (simple Qs, feedback turns) | G2: token/line counts vs thresholds; G3: tone rubric | RC-03 median −30%, RC-02 −40% on feedback turns |
| E09 | S-004/RC-27 output ordering not preserved (oicm-8015) | prompt with user-enumerated list to process | G2: index-sequence comparison | RC-27 ≥9/10 order preserved |
| E10 | S-041/RC-28 lint/test output flood | fixture with noisy failing lint | G2: tokens-per-Bash-result; quiet flags present | RC-28 −50% tokens on passing runs |
| E11 | S-014 paraphrase becomes fabricated fact | fact-dense dialogue replay (from reflection corpus) | G3: fabricated-claim rubric vs seeded fact list | RC-06/RC-16 zero fabrications |
| E12 | S-012/S-029 unsolicited initiative, no options when CTA absent | statement-without-CTA prompts | G2: no Edit/Write tool calls; G3: options offered | RC-08 ≥80% option-proposals |

Corpus sources for prompts/fixtures: verbatim quotes in [[01-symptoms-inventory]], the CV-session reflection ([[04-reflection-evidence]]), oicm-8015 examples, and future incidents (every new observed failure lands here as a row — the corpus only grows).

## 4. Baseline campaign — measure what exists NOW

Runs **before** any Tranche 1 config change ([[20-consolidation-plan]] convergence rule: measurement before structural change). Output: `claude_improvements/baselines/2026-07/` committed JSON + a short report keyed to the LAQF measurement frame (8 characteristics, no composite score).

- **B1 — static snapshot (day 1, deterministic, free).** New `bin/budget_ledger.py`: effective instruction-stack lines/tokens per surface (UAP 201 lines + project CLAUDE.md + alwaysApply skills + per-agent prompt + skill-description budget) and per-agent-invocation load — the attention-budget ledger from [[FPF_seminar/11-fpf-diagnostic]] / LAQF B3. Plus counters: inter-asset conflicts (4 known), `validate_config`/`validate_skill_evals` finding counts, eval coverage (11/40, 10/40, 0/28, 0/22), permission allow/deny list sizes.
- **B2 — trigger-eval baseline.** After WS-B1 (vendored runner): run all 11 existing sets × {opus-4-6, sonnet-4-6}; record per-skill F1 (not grep'd pass/fail). This is the RC-19 "≥80% F1" signal's denominator.
- **B3 — scenario corpus v0.** E01–E12 at N=5 runs each against the *current deployed config*; record per-scenario failure rate with run-level artefacts (transcripts kept for later judge calibration). ~120 headless sessions; budget-cap per run, sonnet for the matrix, spot-check opus.
- **B4 — report.** One page: 8 LAQF characteristics × lead indicator × measured value × band. This fills the C.16 templates and converts every consolidation-plan acceptance signal from aspiration to delta-vs-baseline.

Re-run cadence: B1 on every `make validate-claude` (cheap); B2/B3 before and after each consolidation tranche lands.

## 5. Workstreams

- **WS-A — harness repair** (in llm-tools-configuration): fix §1.2 items 2–4 (syntax error, env wiping, real CLI flags + transcript parsing); decide whether to make Layer 2 real or skip straight to plan item 02/03 (Inspect AI scaffold + first `@task` port) — recommendation: **skip to Inspect**, Layer 2's deepeval codegen is the weakest link and the locked spec already demotes it.
- **WS-B — devbox instrumentation**: (1) vendor the trigger-eval runner into `bin/` (kill the plugin-cache glob and the `grep 'failed: 0'` criterion; emit JSON with per-skill F1); (2) `bin/budget_ledger.py` (B1); (3) `evals/` corpus tree (suites + fixtures for E01–E12); (4) make targets `eval-baseline`, `eval-regression SUITE=…`, wired to `EVAL_HARNESS_DIR`.
- **WS-C — corpus growth**: trigger evals 11→40 skills (batchable via `improve-skills` loop) + cross-skill confusion matrix (one query, assert which skill of the 40 triggers); a runner for the 10 dormant `evals.json` sets (compile to canonical suites — they are already prompt/expectation shaped, cf. `lint-discipline/evals/evals.json`); smoke suites for the 6 pipeline-critical agents and `/techne-implement|test|review`.
- **WS-D — gating**: adopt `compare_baseline.py` semantics (fail on newly-failing case or score drop >0.10, variance-protocol rerun before declaring regression); CI split as today — static/G1 in CI, G2–G4 local/nightly with vendor keys.
- **WS-E — in vivo telemetry** (after tranches ship): hook-log counters (recon/artefact turn ratio, block rates, strip-event logs), OTel export from the harness, field-calibration of LAQF bands — closes the seminar's "next moves" item (b).

## 6. Sequencing

| Phase | Content | Effort | Gate |
|---|---|---|---|
| 0 — repair | unify llm-tools-configuration branches (PR #5 there); WS-A items 2–4; WS-B1+B2 (vendored runner, ledger) | 2–3 days | unified master; `make eval-skills` runs self-contained; ledger emits JSON |
| 1 — baseline | §4 campaign B1–B4 | ~1 week incl. corpus v0 authoring | baselines committed; report written |
| 2 — broaden | WS-C; WS-A Inspect scaffold | 1–2 weeks, parallelisable | 40/40 trigger coverage; evals.json executed once |
| 3 — gate | WS-D; consolidation tranches begin, each measured pre/post | ongoing | no tranche lands without eval delta |
| 4 — in vivo | WS-E | after Tranche 2 hooks exist | LAQF bands calibrated from field data |

Hard ordering constraint: **Phase 1 before any UAP trim or config surgery** — otherwise the baseline measures a moving target and RC-13's "re-test prior failures" loses its control group.

## 7. Decisions taken / open questions

Decisions:
1. Repo topology: suites/fixtures/anchors/baselines co-locate with the templates they test; harness is a separate versioned dependency. End state: templates+evals in llm-toolbox, machinery in `llm-eval-harness`; extraction only after a first end-to-end run proves the `ScorerProtocol`/`FixtureLoader` seams.
2. Sequencing to get there: unify llm-tools-configuration → prove the seam (transcript substrate + E01–E03 + first baseline) → migrate `dot_claude` devbox→toolbox → extract harness.
3. Baseline before change — Phase 1 blocks Tranche 1.
4. Deterministic graders (G1/G2) preferred; G3 judges only with calibrated anchors.
5. Known-error corpus is append-only: every new observed failure becomes a row in §3.
6. Scenario baselines live with the suites (vault/devbox now, llm-toolbox after migration) — follows from decision 1.

Open:
1. Model matrix for B2/B3 — sonnet-only to control cost, or 2-model from day one? (default: sonnet matrix + opus spot-checks)
2. N per scenario — 5 (cheap, noisy) vs 10 (stable, 2× cost)? (default: 5, raise for flaky scenarios)
3. Inspect AI timing — before or after corpus v0? (default: after; corpus v0 needs only the transcript substrate, not a backend)
4. `~/.claude` ownership during the devbox→toolbox migration — Ansible Block 1 (`synchronize --delete`) and toolbox `install.sh` both write there; exactly one deployer must own it at any time.

## See also

- [[00-MoC]] · [[01-symptoms-inventory]] · [[10-root-causes-overview]] · [[20-consolidation-plan]]
- [[FPF_seminar/11-fpf-diagnostic]] (D3/D4 — the demand this plan answers)
- [[FPF_seminar/12-llm-agent-quality-dpf/12-02-measurement-frame]] (the 8 characteristics B4 reports against)
- `abrosimov/llm-tools-configuration` branch `eval-stack-implementation`, `docs/plans/eval-stack-2026-06-27/`
