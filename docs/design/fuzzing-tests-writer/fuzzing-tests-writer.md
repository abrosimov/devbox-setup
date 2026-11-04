---
note_id: "20261103150000"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: hub
note_role: artifact
artifact_kind: map-of-content
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Fuzzing Tests Writer", "FTW hub"]
tags: [fuzzing, design/hub]
status: research-synthesis
related: ["[[ontology]]", "[[fpf-framing]]", "[[next-iteration]]"]
---
# Fuzzing Tests Writer — design hub

Design study (2026-11-03) for a *fuzzing tests writer* agent and its skills for Go 1.27.3, Python
and Rust. Earlier attempts at such an agent went badly; the hypothesis notes name why, the findings
ground the answer in a source-linked research pack, and [[next-iteration]] lays out what is built
next. Nothing under `roles/devbox/files/` is changed by this study.

Goal in the user's words: *restrict fuzzing to the places where it pays off rather than applying it
everywhere; produce an agent plus skills, including per-language ones.*

## How to read

Every note carries its relations in frontmatter ([[ontology]]); start with a chapter's entry note and
follow `addresses` / `grounded_in` / `realised_by` / `tested_by`. The research annexes `R1`–`R10` are
the audit trail behind every finding.

## Chapters

| # | Chapter | Entry note | What it answers |
|---|---|---|---|
| 0 | Ontology | [[ontology]] | note types, relations, ids; the failure hypotheses [[H1-no-applicability-gate\|H1]]–[[H7-no-objective-before-work\|H7]] |
| 1 | Framing | [[fpf-framing]] · [[system-characterisation]] · [[research-corpus]] · [[pbt-agent-prompts]] | receiving use, FPF patterns, boundary, what was read |
| 2 | Findings | [[fuzzing-charter]] · [[fuzzing-vs-pbt-boundary]] · [[applicability-gate]] · [[oracle-ladder]] · [[input-shape-triage]] · [[stopping-algorithm]] · [[corpus-lifecycle]] · [[reporting-and-claim-hygiene]] · [[language-facts-go]] · [[language-facts-python]] · [[language-facts-rust]] | the evidence that drives each design choice |
| 3 | Layout | [[agent-procedure]] · the `skill-*` notes · [[reference-documents]] · [[automation-scripts]] · [[repository-placement]] | what the agent, skills, docs and scripts must cover |
| 4 | Evals | [[eval-plan]] · [[eval-fixtures]] · the `eval-family-*` notes · [[eval-tooling]] · [[acceptance-criteria]] | how the agent is tested against baselines |
| 5 | Decisions | `decisions/` (FTW-D-001 … 009) | design choices with alternatives and consequences |
| 6 | Open questions | `open_questions/` (FTW-OQ-001 … 011) | unverified items and risks with a resolution path |
| 7 | Next | [[next-iteration]] | ordered plan for writing prompt, skills, scripts, evals |
| R | Research | [[research-index]] | annexes R1–R10 with corpus ledgers and claim sheets |

## Executive summary

- **Charter first.** No harness is written before a charter fixes the entry point, the objective, the oracle and contract, the scope, the verifiable result and the budget and stop rule; the report is compared against it → [[fuzzing-charter]], [[FTW-D-009-charter-before-work]].
- **Fuzzing, not property-based testing.** The agent writes fuzz targets, seed corpora and campaigns; typed-API laws, metamorphic numerics and model-based state machines leave the gate as `out-of-scope: pbt-track`; the boundary, tool by tool, is in [[fuzzing-vs-pbt-boundary]], [[FTW-D-008-pbt-out-of-scope]].
- **Gate before harness.** Sourced preconditions and documented hard stops decide applicability per entry point; the bug record concentrates in input-processing code and no yield study exists ([[FTW-OQ-007-per-language-yield-statistics]]) → [[applicability-gate]].
- **Oracle ladder inside the fuzz target.** Crash-only harnesses find a bounded bug set in memory-safe code; round-trip, differential and invariant checks written into the target find the logic bugs → [[oracle-ladder]].
- **Shape before bytes.** Byte mutation stalls at the first checksum, magic or parse step; a fuzzing-side decoder (`arbitrary`, go-fuzz-headers, `FuzzedDataProvider`), a repairing mutator or a fuzzing-build bypass is chosen by input shape → [[input-shape-triage]].
- **Stop by decision, not by exhaustion.** No engine stops itself and no source gives a threshold; budget classes, a sanity gate, a windowed discovery rate and an escalation ladder decide, and the decision is recorded → [[stopping-algorithm]], [[FTW-D-003-thresholds-as-flags]].
- **Conventions are the compile step.** Each ecosystem has three or four non-obvious rules that decide whether a harness is a regression suite or noise → the `language-facts-*` and `skill-*-fuzzing` notes.
- **Evals as a plugin.** Behavioural evals run through `claude plugin eval` on fixture repositories with deterministic graders, including a charter-order grader → [[eval-plan]], [[FTW-D-004-evals-as-plugin]].

## Status and provenance

Research annexes frozen 2026-11-03; several documentation hosts were unreachable, so sources were
read from their GitHub repositories and paper-only claims are marked UNVERIFIED ([[research-corpus]],
`open_questions/`). Refresh triggers are in [[next-iteration]].

## Decisions

- [[FTW-D-001-gate-is-first-step]] — the applicability gate is a skill and the first procedure step
- [[FTW-D-002-six-skills]] — three methodology + three language skills; no separate PBT skill
- [[FTW-D-003-thresholds-as-flags]] — stopping thresholds marked ✓/◇ and exposed as script flags
- [[FTW-D-004-evals-as-plugin]] — behavioural evals via `claude plugin eval`; triggering via existing machinery
- [[FTW-D-005-techne-fuzz-command]] — a new `/techne-fuzz` command rather than a `/techne-test` argument
- [[FTW-D-006-references-beside-skills]] — references beside skills; annexes stay in this vault
- [[FTW-D-007-go-target-version]] — Go facts target 1.27.3, verified against sources
- [[FTW-D-008-pbt-out-of-scope]] — property-based testing is a separate track; strict boundary
- [[FTW-D-009-charter-before-work]] — objective, scope and verifiable result fixed before any harness

## Open questions

- [[FTW-OQ-001-unverified-paper-bodies]] · [[FTW-OQ-002-libfuzzer-legend]] · [[FTW-OQ-003-go-skip-and-minimisation]] · [[FTW-OQ-004-go-ossfuzz-shim]] · [[FTW-OQ-005-cargo-fuzz-on-stable]]
- [[FTW-OQ-006-hypofuzz-licence]] · [[FTW-OQ-007-per-language-yield-statistics]] · [[FTW-OQ-008-corpus-commit-policy]] · [[FTW-OQ-009-plugin-eval-prerequisites]] · [[FTW-OQ-010-agent-model-cost]] · [[FTW-OQ-011-agentic-pbt-validity]]
