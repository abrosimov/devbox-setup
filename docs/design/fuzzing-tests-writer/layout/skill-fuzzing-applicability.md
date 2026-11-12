---
note_id: "20261103150402"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: skill
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: fuzzing-applicability", "fuzzing-applicability"]
tags: [fuzzing, design/component, design/skill, h1, h4, h7]
addresses: ["[[H1-no-applicability-gate]]", "[[H4-crash-only-oracle]]", "[[H7-no-objective-before-work]]"]
realises: ["[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]", "[[fuzzing-charter]]", "[[oracle-ladder]]"]
tested_by: ["[[eval-family-A-gate]]", "[[eval-family-B-oracle]]", "[[eval-family-H-charter]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]", "[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]", "[[FTW-D-009-charter-before-work]]"]
target_path: "roles/devbox/files/dot_ai/skills/fuzzing-applicability/"
related: ["[[reference-documents]]", "[[pbt-agent-prompts]]"]
---
# Skill `fuzzing-applicability`

This design contract is implemented by
`roles/devbox/files/dot_ai/skills/fuzzing-applicability/SKILL.md`.
See [[authoring-validation]] for verified behaviour and remaining qualification.
Functional descriptions support ordinary discovery; advanced invocation conditions and routing remain deferred. Apply these operations within the
scope and persistent research record in [[agent-procedure]]. A reconnaissance pass may establish
the question before a precise hypothesis exists; it still needs accessible material, a feasible
operation, a possible knowledge contribution and proportionate effort limits.

## Reusable operations

| Operation | Inputs and preconditions | Action | Result and next use | Failure or stop |
|---|---|---|---|---|
| Assess applicability | authorised entry point, repository contract, input domain, existing tests and available instrumentation | apply [[applicability-gate]] with evidence for each relevant prerequisite | supported method/oracle for the charter, a bounded check of a missing prerequisite, or a reasoned non-fuzz disposition | unsupported method or absent decisive evidence is reported; do not author another testing approach |
| Frame the current contribution | initial research record, usable material and available operations | distinguish a question-forming reconnaissance pass from an experiment addressing an established question; complete [[fuzzing-charter]] before harness edits | target, operation, observation basis and effort limits that [[skill-fuzzing-campaign]] can execute | an unknown future discovery is allowed; an unavailable operation or undefined failure assertion remains a specific gap |
| Establish oracle meaning | contract statement, known valid/invalid examples, independently expected results | select applicable checks from [[oracle-ladder]], distinguish expected rejection from product failure and expose oracle limitations | contract-linked assertion and defeating case for language-specific harness qualification; resource observations qualified by environment | an unsupported assertion is not promoted into an oracle; inability to distinguish failures remains explicit |

## Evidence and language variation

Use [[reference-documents]] for chapter-to-operation links and language bug-class evidence. A
round trip, differential result or invariant is useful only when its assumptions and expected
meaning hold; a comparator that shares the same defect is not independent confirmation. Crash-only
checks do not establish semantic correctness. Language-specific failure visibility and toolchain
constraints come from [[skill-go-fuzzing]], [[skill-python-fuzzing]] and [[skill-rust-fuzzing]].

[[fuzzing-vs-pbt-boundary]] supplies the exclusion boundary. PBT and mutation analysis are outside
scope, including bridges that create or run PBT, evaluations and optional roadmap work.
[[pbt-agent-prompts]] is historical context only, not a source of current implementation requirements.
No hand-off or alternate suite is created by a non-fuzz disposition.

## Planned content validation

The content cases in [[eval-family-A-gate]], [[eval-family-B-oracle]] and [[eval-family-H-charter]]
must include a new applicable case: a supported parser and unfamiliar corpus permit reconnaissance
of acceptance and reached behaviour without a predicted defect. A defeating case supplies an
assertion contradicted by independently specified contract examples; the agent returns the oracle
gap rather than classifying the product as faulty. Both require a scoped charter before harness
edits. These cases do not test activation and are not run in this methodology pass.
