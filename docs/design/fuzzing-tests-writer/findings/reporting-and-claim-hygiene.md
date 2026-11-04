---
note_id: "20261103150206"
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
aliases: ["Reporting and claim hygiene"]
tags: [fuzzing, design/finding, h6, h2]
addresses: ["[[H6-crash-counting-reports]]", "[[H2-no-stopping-rule]]"]
grounded_in: ["[[06-fuzzingbook-parts3-5|R6]]", "[[02-stopping-and-corpus-lifecycle|R2]]", "[[01-methods-and-applicability|R1]]"]
realised_by: ["[[skill-fuzzing-campaign]]"]
tested_by: ["[[eval-family-F-reporting]]", "[[eval-family-G-triage]]"]
related: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]"]
---
# Reporting and claim hygiene

## The campaign report (R2 §5.3, R6 §5.3)

1. **Product identifier**: module/crate/package, commit, toolchain version, OS/arch, sanitizer or
   race-detector flags.
2. **Campaign**: engine, harness path, budget class, seed corpus origin and size, dictionary, wall
   time, executions, exec/s (mean and minimum), workers, corpus growth, plateau point, windowed
   discovery rate, Good–Turing/Chao1 where computed with the adaptivity caveat, sanity figures
   (stability, slowest unit, peak RSS), escalation rungs tried, **decision token**.
3. **Buckets, not crashes**: signature = sanitizer/panic type + top frames (lower frames generalised
   as FuzzManager does), count, first seen, reproducible yes/flaky, minimised reproducer path
   (`testdata/fuzz/FuzzX/<hash>`, `fuzz/artifacts/<t>/crash-<sha1>`, `@example`), one-line reproduce
   command, suggested severity; one timeout and one OOM bug per target.
4. **Coverage**: per-file/function coverage of the corpus run, with reachable-but-unreached areas as
   the next seeds.
5. **Corpus committed at** / **working corpus at** (not committed).
6. **What I need from you** — last section (the repository's Stop hook enforces the position).

## Claim hygiene (R1 §5.4; fuzz-evaluator guidelines read in full, Klees abstract level)

- Report bugs, not crashes: group by crash state, reproduce, minimise, then count.
- One short run is not evidence a target is clean; state exec/s, runtime, coverage from a neutral
  build, number of trials.
- Name the saturation signal used (windowed rate, `p0`, quiet AFL++ cycle) and say which.
- Never report corpus size as coverage ("corpus count is a bad indicator" — AFL++).
- Triage out before filing: panics permitted by contract (`Must*`), "hangs" that are legitimate
  work under the engine's 1 s budget (x/image/webp #56932), unreproducible artefacts (listed
  separately).

## Design consequence

The template and rules are the closing section of [[skill-fuzzing-campaign]]; `fuzz_campaign.py`
renders the template from its JSON ([[automation-scripts]]); [[eval-family-F-reporting]] greps for
the bucket table, reproduce command, product id and section order; [[eval-family-G-triage]] checks
that contract panics and sub-second hangs are not filed.
