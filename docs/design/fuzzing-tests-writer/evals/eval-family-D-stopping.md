---
note_id: "20261103150506"
created: 2026-11-03
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family D", "Stopping"]
tags: [fuzzing, design/eval]
addresses: ["[[H2-no-stopping-rule]]"]
tests: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family D — Stopping

Ten recorded-log cases, no live engine. Sources: R2 §6 E1–E4/E6–E8/E10; R6 §6 cases 1–3/10; R7 E5.

| Input the agent sees | Expected decision |
|---|---|
| libFuzzer: `INITED cov: 11 ft: 11`, three minutes of `pulse` with no `NEW`, earlier "no interesting inputs were found so far" | `BLOCKED_HARNESS` at the sanity gate |
| Go: `new interesting: 8 (total: 41)` at 3m45s, last change at 1m10s, `interactive` 10 min | `CONTINUE` to cap, then `STOP_BUDGET_EXHAUSTED` with plateau noted and one escalation rung proposed |
| AFL++ `cycles_wo_finds 2, pending_favs 0, stability 97.5, last_find 7.3 h`, 20 h of 24 h | `STOP_SATURATED_AT_BUDGET`; keep `queue/`; suggest switching secondaries |
| AFL++ exec speed 42/s, stability 61 % | `BLOCKED_HARNESS`; fix persistent mode / non-determinism |
| cargo-fuzz corpus of 48 000 files, CI load 12 min | `cargo fuzz cmin`, commit minimised corpus, nightly batch + daily prune |
| Hypothesis `@settings(max_examples=100000)` on a 50 ms property in the PR suite | reject plateau logic; default profile for PR, nightly for more, HypoFuzz for coverage-guided |
| TLS record parser behind an HMAC: seeded coverage 70 %, empty-corpus 4 % | discoverability failure → `cfg(fuzzing)` bypass or split below the MAC check |
| 12 targets, 2 h nightly budget | allocate by recent discovery rate; saturated targets get a regression slice only |
| Go `new interesting: 0 (total: 202)` for 40 min at 1e5 execs/s | plateau; residual risk not quantifiable from engine output; propose seeds/dictionary/another target |
| own Chao1 says Ŝ = 196 with S(n) = 130 after 100 examples | must not report "66 % done"; cite early-campaign inaccuracy |

## Graders

- Regex on the decision token (`STOP_SATURATED_AT_BUDGET` / `STOP_BUDGET_EXHAUSTED` /
  `BLOCKED_HARNESS` / `CONTINUE`); no re-run of the same command in the trace.
- LLM judge: the justification cites the observable (window, exec/s, stability) and names the next
  escalation rung; Hypothesis cases get no plateau logic.

The same logs are unit-test fixtures for `fuzz_campaign.py`, so the deterministic half of this
family runs without a model. The ◇ defaults are written so that a wrong default flips a decision
([[FTW-D-003-thresholds-as-flags]]).
