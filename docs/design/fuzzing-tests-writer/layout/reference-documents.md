---
note_id: "20261103150408"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: reference-set
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Reference documents"]
tags: [fuzzing, design/component]
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
decided_by: ["[[FTW-D-006-references-beside-skills]]"]
related: ["[[research-index]]", "[[repository-placement]]"]
---
# Reference documents

The authored skills place conditional detail in `<skill>/references/`, following
[[FTW-D-006-references-beside-skills]]. Each entrypoint links directly to its references and states
when to read them. [[authoring-budgets]] separates discovery metadata, loaded bodies and conditional
detail. Historical research annexes remain in this vault; they are not runtime dependencies.

| Authored reference | Owner | Method provenance | Contribution and limit |
|---|---|---|---|
| `oracles.md` | `fuzzing-applicability/references/` | [[oracle-ladder]], [[reporting-and-claim-hygiene]] | Contract-linked oracle selection, independent expected examples and candidate classification; a complex oracle is not automatically stronger |
| `research-record.md` | `fuzzing-campaign/references/` | [[stopping-algorithm]], [[fuzzing-charter]], [[automation-scripts]] | Durable question/aim, evidence and effort; ACTIVE/PAUSED/CLOSED, closure reasons, actual resumed operation and new question versus reopened answer |
| `corpus-and-findings.md` | `fuzzing-campaign/references/` | [[corpus-lifecycle]], [[reporting-and-claim-hygiene]], R5 reduction evidence | Useful inputs retained for replay; original and verified reduced candidates, same-symptom checks and explicit unresolved results |
| `grammar-and-repair.md` | `structured-input-generation/references/` | [[input-shape-triage]], [[05-fuzzingbook-part2-syntactic\|R5]] | Bounded derivation trees, expansion observations, deterministic repair and structured reduction; grammar coverage is not code coverage |

The earlier `fuzzingbook-map.md`, `bug-class-evidence.md`, `engine-output-cheatsheet.md` and
`research-lifecycle.md` names were design proposals, not shipped files. Their relevant operational
content is distributed across the references above and the six skill bodies. Language skills link
to primary engine documentation and require checking the actual toolchain and command help before
relying on version-specific behaviour. No common metric or unverified output legend is introduced.

The corpus reference cites the Fuzzing Book reduction chapter. The structure reference cites
mutation-based input generation, grammar generation, grammar coverage and reduction. These transfer
specific mechanisms into operations; they do not claim to implement every chapter or inherit book
performance results. [[methodology-review]] retains the broader source-coverage assessment.
PBT and mutation analysis remain excluded; ordinary mutation of fuzz inputs remains in scope.

Read oracle detail when an assertion is uncertain, record detail when establishing or recovering
research, corpus detail when importing, moving, reducing or deduplicating inputs, and structure
detail when grammar or repair is useful. Do not preload all references. F.19/A.6.3.CSC preserve the
operation's essential conditions in the entrypoint; C.16.IR prevents stronger conclusions than the
available observations support. Useful coverage and structured inputs remain eligible for replay.

The go-kdl2 and proj attempts supply negative evidence and counterexamples, never normative templates.
Provider syntax and loading have a separate factual basis in [[authoring-budgets]] and
[[repository-placement]]; [[authoring-validation]] records the scope of actual verification.
