---
note_id: "20261103150204"
created: 2026-11-03
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Stopping algorithm"]
tags: [fuzzing, design/finding, h2]
addresses: ["[[H2-no-stopping-rule]]"]
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
tested_by: ["[[eval-family-D-stopping]]"]
decided_by: ["[[FTW-D-003-thresholds-as-flags]]"]
related: ["[[corpus-lifecycle]]", "[[reporting-and-claim-hygiene]]"]
---
# Stopping algorithm

What is sourced (✓) and what is a proposed default (◇). R2 §5.1 holds the full procedure and the
per-engine threshold table; R6 §5.2 maps "species" per engine.

## What the sources give

- **Theory** ✓: species = coverage element; Good–Turing `p0 = f1/n` (singletons / inputs) is the
  probability that the next input discovers something new and an upper bound on residual risk;
  `1/p0` is the expected inputs to the next discovery; Chao1 `Ŝ = S(n) + f1²/(2f2)` estimates the
  asymptote and is unreliable early (R6 §0; notebook verified). Greybox adaptivity biases the
  estimate downward (Böhme 2021, abstract level — [[FTW-OQ-001-unverified-paper-bodies]]).
- **Observables** ✓: no engine prints `f1`. Go: `new interesting: k (total: T)`, also as `output`
  events under `-json` (1.27 adds `OutputType`). libFuzzer: `cov`, `ft`, `corp`, `NEW`/`REDUCE`,
  `-print_final_stats=1`. AFL++: `fuzzer_stats` with `cycles_wo_finds`, `last_find`, `pending_favs`,
  `stability`. Hypothesis: "Stopped because settings.max_examples=N" / "nothing left to do" /
  "< 1 % of test cases satisfied assumptions" (R2 §3.2; R8 §3.1).
- **Sourced rules** ✓: AFL++ at least one queue cycle without finds; "a day or a week" without a
  new path means not fruitful, "but often this just means switch strategy". Go: "it is up to you".
  Hypothesis is budgeted by count and must get no plateau logic. libFuzzer has only
  `-max_total_time`/`-runs`. Sanity: <10 exec/s (libFuzzer guidance) or <100 (AFL++) is a broken
  harness; stability <90 % invalidates results; "no interesting inputs were found so far" means
  uninstrumented or all-rejecting.
- **Budgets in practice** ✓: ClusterFuzzLite 600 s per PR (quits on first crash), 3 600 s batch,
  daily prune; cargo-fuzz book 300 s smoke; research ≥ 24 h with many trials.
- **Plateau ≠ saturation** ✓: OSS-Fuzz names four causes of "no new coverage for days" (all
  reachable code covered, weak seeds, checksum/crypto blockers, too slow).

## The procedure

1. **Budget class first**, cap passed to the engine: `interactive` 10 min ◇, `smoke` 300–600 s ✓,
   `batch` 3 600 s ✓, `deep` 24 h ✓.
2. **Sanity gate at 2 min** ◇ (bars ✓): abort as `BLOCKED_HARNESS` on no interesting inputs, too
   slow, stability <90 %, or a crash/timeout on the seeds.
3. **Discoverability check** once per new harness ✓ (criterion 50 % ◇): empty-corpus coverage far
   below the seeded run means the target is not fuzzable as written.
4. **Sample counters every 60 s** ◇; declare a plateau when no new coverage for
   `W = max(10 min, 25 % of elapsed)` ◇ and ≥10⁶ executions in the window ◇ (AFL++ additionally
   ≥1 quiet cycle ✓).
5. **Residual-risk estimate, report-only**: windowed discovery rate `p̂_W`; Good–Turing and Chao1
   only where a per-feature dump exists; always with the adaptivity caveat.
6. **Decide**: `STOP_SATURATED_AT_BUDGET` when plateau holds, `1/p̂_W` exceeds the remaining
   executions, and the escalation ladder is exhausted for the class; `STOP_BUDGET_EXHAUSTED` at the
   cap otherwise; `CONTINUE` else. Smoke class runs to the cap.
7. **Crash path pre-empts**: stop in smoke ✓; elsewhere minimise and deduplicate by crash state
   within ≤10 % of the budget ◇, verify reproduction three times, report unreproducible separately.
8. **Escalation ladder on plateau** (one rung per plateau; order from AFL++ §3h, google/fuzzing,
   OSS-Fuzz FAQ): seeds from the coverage report → dictionary → schedule/engine → structure-aware
   generator or mutator → split target → fuzzing-cfg bypass. Rungs 4–6 start a new (target, corpus)
   ledger entry.
9. **Attention across targets**: next slice to the target with the highest recent discovery rate
   discounted by how often it was already scheduled (AFLFast energy idea); targets touched by the
   diff get a mandatory slice (ClusterFuzzLite affected-fuzzer rule).

## Design consequence

[[skill-fuzzing-campaign]] carries the procedure and the ✓/◇ table; `fuzz_campaign.py` in
[[automation-scripts]] samples the counters and emits the decision token so the model never parses
logs by eye. The ◇ defaults are script flags and the first tuning target of
[[eval-family-D-stopping]].
