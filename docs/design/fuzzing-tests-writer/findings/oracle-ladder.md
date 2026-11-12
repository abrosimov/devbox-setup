---
note_id: "20261103150202"
created: 2026-11-03
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
aliases: ["Oracle ladder"]
tags: [fuzzing, design/finding, h4]
addresses: ["[[H4-crash-only-oracle]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-B-oracle]]"]
related: ["[[applicability-gate]]", "[[reporting-and-claim-hygiene]]", "[[pbt-agent-prompts]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Oracle selection

The historical filename is retained for links. There is no universal ranking that makes a model
oracle automatically stronger than every other check. Select an executable oracle that can
identify the charter's failure class, state its assumptions, and validate it with known cases
before using its output as product evidence.

| Check | What a failure may show | Required qualification |
|---|---|---|
| Crash, panic or uncaught exception | Unexpected termination on a contract-admissible call | Distinguish expected rejection and permitted precondition failures |
| Resource bound | A specified limit was exceeded under the recorded conditions | Isolate per-input behaviour from setup, engine minimisation and environment failure |
| Round trip or canonicalisation | A specified relation between transformations is violated | Define semantic equality, normalisation and lossy behaviour |
| Differential comparison | Implementations disagree on a shared input domain | Disagreement alone does not identify which implementation is wrong |
| Invariant/postcondition | A documented output or state condition is violated | Checker and assumptions must be independently inspectable |
| Metamorphic relation or existing reference model | Related executions violate an established relation | Use only an already-grounded relation within the fuzzing task; no separate PBT/model project |
| Sanitizer | Instrumented execution detected its reported class of problem | Record build/instrumentation coverage and reproduce the diagnostic |

Use multiple checks when they add relevant evidence cheaply. Crash/resource checks may be
sufficient for a charter specifically concerned with those failures; availability of a more
complex relation does not compel its implementation. Conversely, a crash-only harness cannot
claim to have checked round-trip correctness.

## Validate and classify

- Exercise known valid input, expected invalid input and a known failing example where one
  exists. Do not invent a product fault or add mutation analysis to validate the checker.
- Compare assertions with the product specification and ordinary tests. An unexpected assertion
  is initially a candidate failure, not proof of a product defect.
- Catch only expected domain exceptions; broad suppression can hide the sought failure. A
  permitted panic or invalid API precondition is not automatically a bug.
- Preserve the original input and diagnostic. Reproduce independently of the search loop where
  possible, within the admitted experiment limits. Minimisation must retain the relevant symptom.
- If the authored oracle is wrong, correct that harness within scope and recheck the evidence.
  Product repair is outside this agent's work. Unresolved disagreements remain unconfirmed.

The failed `go-kdl2` attempt includes an oracle expecting a required-field diagnostic twice when
the library correctly produced it once
([frontier inventory, O-9](https://github.com/abrosimov/go-kdl2/blob/f345e460f4cbe71020775802f5c90c9a5082f0f7/docs/roadmaps/kdl2-go-full-implementation/research/fuzz-frontier-phase-0-inventory.md#L405-L416)).
Its original artefact came from excluded PBT work: the transferable lesson is checker fallibility, not a PBT
workflow. [[reporting-and-claim-hygiene]] keeps product, harness and environment results separate.
Language-specific diagnostic behaviour is verified at authoring using the primary sources in
the language notes; historical engine defaults are not this oracle contract.
