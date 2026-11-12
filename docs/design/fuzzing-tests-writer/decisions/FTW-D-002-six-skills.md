---
note_id: "202611031506002"
created: 2026-11-03
modified: 2026-11-10
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-002"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[skill-fuzzing-applicability]]", "[[skill-fuzzing-campaign]]", "[[skill-structured-input-generation]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]", "[[FTW-D-008-pbt-out-of-scope]]"]
---
# FTW-D-002: Six skills with concrete operation contracts

*Amended in draft on 2026-11-10 by the methodology revision ([[methodology-review]]).*

Retain `fuzzing-applicability`, `fuzzing-campaign`, `structured-input-generation`, `go-fuzzing`,
`python-fuzzing` and `rust-fuzzing`. The first three supply methodology; the other three specialise
execution and replay conventions. Each layout note specifies inputs, preconditions, action, output,
failure/stop behaviour and evidence. Shared operations must not acquire different meanings by language.

**Basis:** existing decomposition plus SYSE.48; [[methodology-review]]. PBT and mutation analysis
are excluded by [[FTW-D-008-pbt-out-of-scope]]. The six documents are specifications, not installed
skills or demonstrated capability.

**Alternatives:** one monolith mixes method with language detail; many smaller skills add discovery
and maintenance cost without an evidenced need. No line-count ceiling, automatic loading policy,
trigger condition or Codex allowlist entry is adopted here. Those depend on actual authoring and the
separate invocation decision. Revisit boundaries if an operation has conflicting ownership or a
representative task cannot use the decomposition; do not merge/split just to meet an arbitrary size.
