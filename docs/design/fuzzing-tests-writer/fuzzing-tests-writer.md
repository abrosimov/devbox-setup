---
note_id: "20261103150000"
created: 2026-11-03
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
and Rust. Earlier attempts at such an agent went badly; this study names why (six hypotheses),
grounds the answer in a source-linked research pack, and lays out what the next iteration builds.
Nothing under `roles/devbox/files/` is changed by this study.

Goal in the user's words: *restrict fuzzing to the places where it pays off rather than applying it
everywhere; produce an agent plus skills, including per-language ones.*

## How to read

Every note carries its own frontmatter relations (see [[ontology]]). Start with a chapter hub,
follow `addresses` / `grounded_in` / `realised_by` / `tested_by` links; the research annexes are the
audit trail and are cited as `R1`–`R10`.

## Chapters

| # | Chapter | Entry note | What it answers |
|---|---|---|---|
| 0 | Ontology | [[ontology]] | note types, relations, ids; the six failure hypotheses [[H1-no-applicability-gate\|H1]]–[[H6-crash-counting-reports\|H6]] |
| 1 | Framing | [[fpf-framing]] · [[system-characterisation]] · [[research-corpus]] | receiving use, FPF patterns, boundary, what was read |
| 2 | Findings | [[applicability-gate]] · [[oracle-ladder]] · [[input-shape-triage]] · [[stopping-algorithm]] · [[corpus-lifecycle]] · [[reporting-and-claim-hygiene]] · [[language-facts-go]] · [[language-facts-python]] · [[language-facts-rust]] | the evidence that drives each design choice |
| 3 | Layout | [[agent-procedure]] · six `skill-*` notes · [[reference-documents]] · [[automation-scripts]] · [[repository-placement]] | what the agent, skills, docs and scripts must cover |
| 4 | Evals | [[eval-plan]] · [[eval-fixtures]] · seven `eval-family-*` notes · [[eval-tooling]] · [[acceptance-criteria]] | how the agent is tested against baselines |
| 5 | Decisions | `decisions/` (FTW-D-001 … 007) | design choices with alternatives and consequences |
| 6 | Open questions | `open_questions/` (FTW-OQ-001 … 010) | unverified items and risks with a resolution path |
| 7 | Next | [[next-iteration]] | ordered plan for writing prompt, skills, scripts, evals |
| R | Research | [[research-index]] | annexes R1–R10 with corpus ledgers and claim sheets |

## Executive summary

- **Gate first.** Fuzzing pays off on deterministic, fast, in-process code that consumes untrusted or format-defined input and has an oracle stronger than "crash"; everything else gets property tests, unit tests or nothing → [[applicability-gate]], [[FTW-D-001-gate-is-first-step]].
- **Oracle ladder.** In memory-safe languages crash-only harnesses find a bounded bug set; logic bugs need round-trip, differential, metamorphic or model-based properties → [[oracle-ladder]].
- **Shape before bytes.** Byte mutation stalls at the first checksum, magic or parse step; the remedy is a generator over the byte stream, a repairing mutator, or a fuzzing-build bypass, chosen by input shape → [[input-shape-triage]].
- **Stop by decision, not by exhaustion.** No engine stops itself and no source gives a threshold; the agent uses budget classes, a sanity gate, a windowed discovery rate and an escalation ladder, and records the decision → [[stopping-algorithm]], [[FTW-D-003-thresholds-as-flags]].
- **Conventions are the compile step.** Each ecosystem has three or four non-obvious rules that decide whether a harness is a regression suite or noise → the three `language-facts-*` notes and `skill-*-fuzzing` notes.
- **Evals as a plugin.** Behavioural evals run through `claude plugin eval` on fixture repositories with deterministic graders; skill triggering keeps the repository's existing eval machinery → [[eval-plan]], [[FTW-D-004-evals-as-plugin]].

## Status and provenance

Research annexes frozen 2026-11-03. Several documentation hosts were unreachable from the research
session; sources were read from their GitHub repositories and paper-only claims are marked
UNVERIFIED (see [[research-corpus]] and the `open_questions/`). Refresh triggers are listed in
[[next-iteration]].

## Decisions

- [[FTW-D-001-gate-is-first-step]] — the applicability gate is a skill and step 1 of the procedure
- [[FTW-D-002-six-skills]] — three methodology + three language skills; no separate PBT skill
- [[FTW-D-003-thresholds-as-flags]] — stopping thresholds marked ✓/◇ and exposed as script flags
- [[FTW-D-004-evals-as-plugin]] — behavioural evals via `claude plugin eval`; triggering via existing machinery
- [[FTW-D-005-techne-fuzz-command]] — a new `/techne-fuzz` command rather than a `/techne-test` argument
- [[FTW-D-006-references-beside-skills]] — references beside skills; annexes stay in this vault
- [[FTW-D-007-go-target-version]] — Go facts target 1.27.3, verified against sources

## Open questions

- [[FTW-OQ-001-unverified-paper-bodies]] · [[FTW-OQ-002-libfuzzer-legend]] · [[FTW-OQ-003-go-skip-and-minimisation]] · [[FTW-OQ-004-go-ossfuzz-shim]] · [[FTW-OQ-005-cargo-fuzz-on-stable]]
- [[FTW-OQ-006-hypofuzz-licence]] · [[FTW-OQ-007-per-language-yield-statistics]] · [[FTW-OQ-008-corpus-commit-policy]] · [[FTW-OQ-009-plugin-eval-prerequisites]] · [[FTW-OQ-010-agent-model-cost]]

## Graph conventions

Relations are frontmatter fields ([[ontology]]): hypothesis ← `addresses` ← finding ← `realised_by`
→ component ← `tested_by` → eval family; `decided_by` and `opens` attach decisions and open
questions. Obsidian's graph view with the `fuzzing` tag shows the whole study; filtering on
`design/finding` and `design/component` gives the build map.
