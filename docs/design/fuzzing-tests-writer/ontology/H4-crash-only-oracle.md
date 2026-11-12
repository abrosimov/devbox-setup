---
note_id: "20261103150005"
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
aliases: ["H4", "Crash as the only oracle"]
tags: [fuzzing, design/hypothesis, h4]
verdict: "design risk; oracle adequacy requires task evidence"
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
addressed_by: ["[[oracle-ladder]]", "[[skill-fuzzing-applicability]]"]
tested_by: ["[[eval-family-B-oracle]]"]
related: ["[[ontology]]"]
---
# H4 — The oracle does not detect the intended failure

**Status:** design risk; oracle adequacy requires task evidence.

A no-crash oracle observes some failures but cannot establish semantic correctness. A stronger
assertion is useful only if the contract supports it; copying an attractive invariant can create
false bugs. R1 and the language annexes contain examples, not a cross-language ranking of yields.

[[oracle-ladder]] specifies oracle selection inside a fuzz target. Expected parse rejection and
contractual panics must not become findings automatically. Check a decisive expected value or
reference independently; disagreement alone is not proof which side is wrong. The false-oracle
example from go-kdl2 is negative evidence, with its PBT provenance explicitly excluded from the
current workflow ([[methodology-review]]). Family B checks the distinction.
