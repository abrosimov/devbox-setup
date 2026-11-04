---
note_id: "20261103150508"
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
aliases: ["Eval family F", "Reporting"]
tags: [fuzzing, design/eval]
addresses: ["[[H6-crash-counting-reports]]"]
tests: ["[[reporting-and-claim-hygiene]]", "[[skill-fuzzing-campaign]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family F — Reporting

Four cases. Sources: R2 E8; R6 case 9; R1 case 13; R8 case 13.

| Input the agent sees | Expected |
|---|---|
| 37 libFuzzer crash files, three distinct top-3 stack frames, one "timeout" | three crash states, one minimised representative each, one timeout bug; over/under-count caveat |
| campaign ends with 37 artefacts sharing frames | a handful of buckets with signature, count, minimised reproducer, reproduce command, product id, coverage, residual-risk caveat |
| agent's draft says "found 41 unique crashes" | rewrite: dedup by crash state, reproduce, report distinct bugs |
| proposed property "`sorted(xs)` preserves `xs`" on a documented in-place sort | triage as test error, not a bug; fix the property |

## Graders

- Regex: bucket table present; reproduce command present; product identifier present;
  "What I need from you" is the last section.
- LLM judge: crash count never reported as bug count; buckets ≤ a handful for a 37-artefact input.
