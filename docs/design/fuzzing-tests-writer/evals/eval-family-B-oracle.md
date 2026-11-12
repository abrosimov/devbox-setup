---
note_id: "20261103150504"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family B", "Oracle"]
tags: [fuzzing, design/eval]
addresses: ["[[H4-crash-only-oracle]]"]
tests: ["[[oracle-ladder]]", "[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Eval family B — Oracle inside the fuzz target

The selected oracle must be justified by the target contract and independently checked. A stronger
sounding assertion is not necessarily correct. No mutation experiment is required or in scope.

| Case | Expected observable result |
|---|---|
| Parser with a documented canonical formatter | Define semantic round-trip equality or canonicalisation as specified; do not demand raw text identity |
| Two implementations with different documented accepted inputs | Compare only the shared contract and record disagreements; do not swallow every exception |
| Invalid raw bytes supplied to an error-returning parser | Expected parse rejection is handled narrowly; unexpected exceptions remain visible |
| Correct parser and a harness expecting a required field twice | Contract/fixture evidence identifies the false oracle; repair the authored harness within authorised experiment scope and effort, not the product |
| Resource-bound decoder | State the permitted input/resource limit and obtain independent timing or memory evidence; timeout alone is not an infinite-loop diagnosis |
| Native decoder with a crash-only objective | A crash/sanitiser oracle is sufficient for that stated objective when instrumentation is verified |
| Proposed arithmetic check with undocumented tolerance | Do not invent equality or tolerance; retain a justified oracle or report the missing premise |
| Candidate minimisation changes the failure signature | Reject that candidate as a reproducer of the original finding; preserve the original input |

## Evidence

The independent verifier exercises known valid, expected-invalid and contract-violating cases.
It checks the actual target and oracle behaviour, not the number of assertions or comments. The
report names the contract, accepted domain, comparison semantics and limits of each finding.
A judge may assess this mapping but cannot replace execution. See [[oracle-ladder]] and
[[eval-family-G-triage]].
