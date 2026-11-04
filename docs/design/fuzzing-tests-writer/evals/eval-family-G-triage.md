---
note_id: "20261103150509"
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
aliases: ["Eval family G", "Triage false positives"]
tags: [fuzzing, design/eval]
addresses: ["[[H6-crash-counting-reports]]", "[[H4-crash-only-oracle]]"]
tests: ["[[reporting-and-claim-hygiene]]", "[[oracle-ladder]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family G — Triage false positives

Three cases. Sources: R7 E7; R1 case 7; R8 case 13 (shared with family F).

| Input the agent sees | Expected |
|---|---|
| image decoder reports a "hang" after 1 s on a 28-byte input declaring 12043×4098 | measure standalone; if a legitimate large allocation, propose an input-size guard or a decoder limit, do not file "infinite loop"; if unbounded (debug/gosym pattern) file with the reproducer |
| `regexp.MustCompile`-style entry panics under fuzzing | contract permits the panic; exclude the entry, fuzz the `Compile` variant |
| fuzzing run flags a panic that only occurs when a precondition the API documents is violated | encode the precondition in the generator; not a bug |

## Graders

- Regex on the report: no issue filed for the contract panic or the sub-1 s hang.
- LLM judge: reasoning cites the contract or the engine's timeout budget.
