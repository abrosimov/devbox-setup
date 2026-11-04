---
note_id: "20261103150003"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H2", "No stopping rule, no corpus switch"]
tags: [fuzzing, design/hypothesis, h2]
verdict: "confirmed-and-sharpened"
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]"]
addressed_by: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
tested_by: ["[[eval-family-D-stopping]]"]
related: ["[[ontology]]"]
---
# H2 — No stopping rule, no corpus switch

**Hypothesis.** Earlier agents either ran the engine until interrupted or stopped arbitrarily; they had no notion of a saturated corpus, of a blocked harness, or of when to move to another seed corpus or target.

**Verdict.** Confirmed and sharpened: no source gives a numeric threshold, engines expose plateau proxies only, and the correct output is a decision with a recorded budget, not an open-ended run. The thresholds [[stopping-algorithm]] proposes are therefore marked sourced or proposed ([[FTW-D-003-thresholds-as-flags]]).

## Evidence

- Theory: Good–Turing `p0 = f1/n` bounds residual risk and `1/p0` is the expected inputs to the next discovery; Chao1 is unreliable early; greybox adaptivity biases the estimate downward — R2 §3.1, R6 §3 (WhenToStopFuzzing), Böhme 2021 abstract-level.
- Practice: AFL++ "at least one queue cycle without new finds" and "a day or a week… often this just means switch strategy"; Go "it is up to you"; libFuzzer only `-max_total_time`/`-runs`; Hypothesis stops at `max_examples` and has no plateau notion — R2 §3.2.
- Budgets in use: ClusterFuzzLite 600 s PR / 3 600 s batch; cargo-fuzz book 300 s smoke; research ≥ 24 h — R2 §3.4.
- Plateau ≠ saturation: OSS-Fuzz names four causes of "no new coverage for days" — R2 §3.4 F6.
