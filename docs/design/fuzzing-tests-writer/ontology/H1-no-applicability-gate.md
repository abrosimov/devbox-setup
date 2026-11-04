---
note_id: "20261103150002"
created: 2026-11-03
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H1", "Fuzzing applied everywhere, no gate"]
tags: [fuzzing, design/hypothesis, h1]
verdict: "confirmed"
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[07-lang-go|R7]]"]
addressed_by: ["[[applicability-gate]]", "[[skill-fuzzing-applicability]]", "[[agent-procedure]]"]
tested_by: ["[[eval-family-A-gate]]"]
related: ["[[ontology]]"]
---
# H1 — Fuzzing applied everywhere, no gate

**Hypothesis.** Earlier agents wrote a fuzz target for every function they were pointed at, including glue code, thin wrappers over already-fuzzed libraries, and code with network or clock dependence.

**Verdict.** Confirmed as the dominant risk. Independent traditions agree on the hard stops and on where the yield is.

## Evidence

- The Fuzzing Book's own evidence puts the yield at the input-processing boundary ("bugs fuzzers find are mainly due to errors and deficiencies in input processing") and says an already-fuzzed target returns nothing ("all errors found are already fixed") — R4 §5.1, R1 §3.1.
- Google's harness guidance and the AFL++ docs enumerate hard stops: non-determinism, persistent threads, <10 exec/s, network services, GUI — R1 §5.1 (S1, S7, S30).
- The Go issue tracker shows almost every fuzzing find in `debug/*`, `archive/*`, `encoding/*`, `image/*`, `regexp`: format readers, not business logic — R7 §3.6.
- Configuration/option spaces are finite and belong to pairwise testing, not fuzzing — R6 §5.4 (ConfigurationFuzzer).

## Addressed by

[[applicability-gate]] (the decision table), carried by [[skill-fuzzing-applicability]] and run as step 1 of [[agent-procedure]].

## Tested by

[[eval-family-A-gate]]: twelve cases, half of which expect "do not fuzz"; any false "fuzz" fails acceptance ([[acceptance-criteria]]).
