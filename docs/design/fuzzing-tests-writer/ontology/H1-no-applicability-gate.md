---
note_id: "20261103150002"
created: 2026-11-03
modified: 2026-11-10
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
verdict: "design risk; historical dominance unproven"
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[07-lang-go|R7]]"]
addressed_by: ["[[applicability-gate]]", "[[skill-fuzzing-applicability]]", "[[agent-procedure]]"]
tested_by: ["[[eval-family-A-gate]]"]
related: ["[[ontology]]"]
---
# H1 — Suitability must precede harness work

**Status:** design risk; historical dominance unproven.

Earlier wording called lack of an applicability gate the dominant confirmed cause. The source
survey cannot establish that causal ranking for the user's projects. Keep suitability as a design
risk and operation, not as a measured explanation of all past failure.

Check the scoped entry point, oracle, observable work and controllable effects before constructing
a harness ([[applicability-gate]]). Neither low throughput alone nor already having a corpus proves
fuzzing is useless. Conversely, a technically fuzzable function does not justify spending the budget.
The failed attempts and transfer limits are recorded in [[methodology-review]]. Family A checks
supported acceptance and refusal cases; it does not require broad project exploration.
