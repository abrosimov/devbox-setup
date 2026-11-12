---
note_id: "20261103150006"
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
aliases: ["H5", "Harnesses that do not compile or follow conventions"]
tags: [fuzzing, design/hypothesis, h5]
verdict: "design risk; runtime qualification still pending"
grounded_in: ["[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
addressed_by: ["[[language-facts-go]]", "[[language-facts-python]]", "[[language-facts-rust]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
related: ["[[ontology]]"]
---
# H5 — Harness and replay conventions are not verified

**Status:** design risk; runtime qualification still pending.

A written target may fail to build, fail to reach the intended code, or lose its reproducer.
The language annexes are historical guidance; their presence does not prove a current command or
harness works. Version-sensitive details require verification during authoring.

The three language skills specify real build/execution and seed replay evidence. Static checks
alone, `go vet` alone, or a Python import alone do not qualify a fuzz harness. Use the actual target
runtime and verify the intended oracle path independently. Preserve useful input files under
repository conventions without assuming a Git commit is authorised. Family E checks this on new
fixtures. [[language-facts-go]], [[language-facts-python]] and [[language-facts-rust]] own details.
