---
note_id: "20261104100001"
created: 2026-11-04
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
aliases: ["H7", "Work started without a defined objective and a checkable result"]
tags: [fuzzing, design/hypothesis, h7]
verdict: "stated by the user; consistent with H1, H2 and H6"
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[02-stopping-and-corpus-lifecycle|R2]]"]
addressed_by: ["[[fuzzing-charter]]", "[[agent-procedure]]", "[[skill-fuzzing-applicability]]"]
tested_by: ["[[eval-family-H-charter]]"]
related: ["[[ontology]]", "[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]"]
---
# H7 — Work started without a defined objective and a checkable result

**Hypothesis.** Earlier agents began writing harnesses and running engines before stating what the
fuzzing was meant to establish and what observable result would count as "done". Without that
charter there is nothing to compare the work against, and H1 (fuzz everything), H2 (never stop)
and H6 (report crash counts) follow.

**Verdict.** Stated by the user as a requirement for this iteration; the research supports it
indirectly, since every sourced stopping, harness and reporting rule presupposes something the
charter fixes. The [[fuzzing-charter]] is written at the charter step of [[agent-procedure]]
(step 2, after the gate), and no harness file is written before it
([[FTW-D-009-charter-before-work]]).

## Evidence

- R2 §5.1 step 1: the stopping procedure cannot start without a budget class and a cap passed to
  the engine; "stop at this budget and record it" is only meaningful against a declared budget.
- R1 §5.1 preconditions 4–5: an oracle named explicitly and a contract statement are inputs to the
  harness, not outputs of the campaign.
- R6 §5.3 (FuzzingInTheLarge): the report's first items are product identifier and campaign
  definition — they exist before any crash does.
- SYSE.47 §4.1: "recover the required result, supplied domain operations, actual interface
  conditions and observable evidence of completion" before constructing the procedure.
