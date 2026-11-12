---
note_id: "20261104100003"
created: 2026-11-04
modified: 2026-11-11
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Fuzzing versus PBT boundary", "Fuzzing vs property-based testing"]
tags: [fuzzing, design/finding, h1, h3, lang/go, lang/python, lang/rust]
addresses: ["[[H1-no-applicability-gate]]", "[[H3-random-seeds-for-structured-input]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[03-structure-aware-generation|R3]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-A-gate]]", "[[eval-family-C-structure]]"]
decided_by: ["[[FTW-D-008-pbt-out-of-scope]]"]
related: ["[[applicability-gate]]", "[[input-shape-triage]]", "[[pbt-agent-prompts]]"]
---
# Fuzzing versus property-based testing — current scope

The deliverable is a fuzzing methodology and six fuzzing skill specifications. PBT and mutation
analysis are excluded from this project, including implementation, evaluation obligations,
bridges that execute PBT tests and an optional future-work roadmap. This supersedes the earlier
permission to use existing PBT artefacts through hybrid integrations.

A name or library label does not decide the boundary. For this method, an in-scope operation
runs a bounded fuzzing experiment over engine inputs with an explicit target contract, oracle,
replay record and justified experiment limits within the persistent research scope. Checking a round trip or invariant inside that harness
is allowed; it does not authorise developing a separate PBT suite.

| Operation | Current disposition |
|---|---|
| Go native fuzz target, byte/primitive arguments and replay corpus | In scope |
| Atheris byte target and fuzzing-side data decoder | In scope |
| Rust cargo-fuzz target and `arbitrary` decoder | In scope |
| Grammar seeds, dictionaries, bounded input repair or custom input mutation | In scope where supported and justified by the charter |
| Byte-decoded operation sequence with existing contract checks | In scope when bounded, resettable and tied to the target objective |
| Hypothesis/rapid/proptest strategies, properties, state-machine suites and shrinking workflows | Out of scope |
| `rapid.MakeFuzz`, Hypothesis `fuzz_one_input`, HypoFuzz over a PBT suite | Out of scope, including pre-existing suites |
| Mutation analysis or mutation-testing quality gates | Out of scope |

Mutating fuzz inputs remains an ordinary fuzzing technique; mutation analysis changes the
program to assess tests and is the excluded activity. Do not infer that all PBT lacks feedback
or that all fuzzing requires untyped bytes; those broad definitions are unnecessary here.

An unsuitable target receives a reasoned assessment under [[applicability-gate]]. The agent does
not create another agent, write a PBT hand-off specification or extend the charter to compensate.
Historical PBT material in [[pbt-agent-prompts]] and the research annexes remains source history,
not a normative dependency. [[FTW-D-008-pbt-out-of-scope]] governs this boundary.
