---
note_id: "20261104100001"
created: 2026-11-04
modified: 2026-11-11
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
verdict: "user requirement; procedure and check specified"
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[02-stopping-and-corpus-lifecycle|R2]]"]
addressed_by: ["[[fuzzing-charter]]", "[[agent-procedure]]", "[[skill-fuzzing-applicability]]"]
tested_by: ["[[eval-family-H-charter]]"]
related: ["[[ontology]]", "[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]"]
---
# H7 — Work starts without a defined result

**Status:** user requirement; persistent charter and checks specified.

Before investigation, identify the bounded subject and question/use, or concrete material and a
learning aim for initial reconnaissance. A precise question may emerge from that work. Before
harness construction, settle the contract-backed oracle and checkable result. These are recorded
in [[fuzzing-charter]], with unknowns explicit rather than replaced by invented requirements.

The charter persists across experiments and agent invocations. A resumed session recovers prior
results and remaining uncertainty. Another experiment needs a named useful contribution; another
agent run does not reset the objective or erase previous effort.

[[agent-procedure]] and family H check this continuity. SYSE.47 supplies procedure framing; it
does not establish local causality for every past failure. A research question may close answered
or with limitations; finding a new bug is not a mandatory completion condition.
