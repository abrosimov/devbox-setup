---
note_id: "20261103150503"
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
aliases: ["Eval family A", "Gate"]
tags: [fuzzing, design/eval]
addresses: ["[[H1-no-applicability-gate]]"]
tests: ["[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]", "[[skill-fuzzing-applicability]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Eval family A — Applicability

Evaluate the methodological assessment after the task is explicitly assigned. Invocation and
routing decisions are not tested here. Historical research examples supply candidates, not an
automatic answer key; the fixture's owned behaviour, contract and execution boundary decide.

| Case | Expected observable result |
|---|---|
| Custom binary frame parser with a byte boundary and an encoder | Identify owned behaviour, feasible fuzz target, useful seeds and a justified oracle |
| Supported parser and unfamiliar corpus without a precise hypothesis | Permit scoped inspection/replay to establish input distinctions and a question; qualify any failure assertion independently |
| Thin decoder wrapper without owned transformations | Explain the limited additional fuzzing value; do not create a redundant target merely because parsing exists |
| The same wrapper with custom length or normalisation logic | Assess that owned behaviour separately; do not reject it solely because a dependency is fuzzed upstream |
| Handler requiring unavailable database access | Identify the unavailable boundary; do not run side effects or label the environment as a product defect |
| Small finite domain already exhaustively checked | Explain why fuzzing adds no demonstrated value; do not write unrelated tests |
| Panic-permitting API and an error-returning alternative | Apply each documented contract; do not count expected panics as defects |
| Missing contract for a proposed semantic assertion | Leave that oracle unqualified or choose an independently justified narrower one; do not invent a requirement |
| Request whose objective is outside the fuzzing charter | State the scope mismatch and stop; do not build or prescribe another testing workflow |

## Evidence

Grade the decision against the fixture contract and inspect the workspace diff for unjustified
writes. A decision-token regex can check format, not applicability. A reviewer must identify the
premise that permits or defeats useful fuzzing. No mandatory handoff to another agent or framework
is part of this family. See [[acceptance-criteria]] and [[fuzzing-vs-pbt-boundary]].
