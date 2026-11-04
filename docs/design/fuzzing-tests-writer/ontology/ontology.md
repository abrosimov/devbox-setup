---
note_id: "20261103150001"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: ontology
note_role: artifact
artifact_kind: schema
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW ontology"]
tags: [fuzzing, design/ontology]
related: ["[[fuzzing-tests-writer]]"]
---
# Ontology of the design vault

## Note types (`type: design`, by `subtype`)

| `subtype` | Folder | One note is… | Id / alias |
|---|---|---|---|
| `hub` | root | a map of content | name |
| `ontology` | `ontology/` | this schema | — |
| `hypothesis` | `ontology/` | one named cause of past failure, with verdict and evidence | `H1`–`H7` |
| `framing` | `framing/` | receiving use, FPF pattern binding, system boundary, corpus description, the PBT agent prompts | name |
| `finding` | `findings/` | one evidence-backed conclusion with its design consequence | name |
| `component` | `layout/` | one thing to build: agent procedure, skill, reference set, script, placement | name; skills carry their future directory name |
| `eval` | `evals/` | plan, fixtures, one case family, tooling, acceptance | family letter `A`–`H` |
| `decision` (`type: meta`) | `decisions/` | one design choice, alternatives, consequences, reopen condition | `FTW-D-NNN` |
| `open-question` (`type: meta`) | `open_questions/` | one unverified item or risk with its resolution path | `FTW-OQ-NNN` |
| `plan` | `next/` | ordered steps for the next iteration and refresh triggers | name |
| `research` / `annex` | `research/` | one research report: ledger, claim sheets, implications, eval cases | `R1`–`R10` |

## Relation fields (frontmatter, wikilinks as quoted strings)

| Field | From → to | Meaning |
|---|---|---|
| `addresses` | finding, component, eval → hypothesis | the note exists to remove that failure cause |
| `grounded_in` | finding, hypothesis, decision → annex (`[[07-lang-go\|R7]]`) | the evidence; cite section in the body |
| `realised_by` | finding → component | which skill, script or procedure step carries the finding |
| `realises` | component → finding | inverse of `realised_by` |
| `tested_by` | finding, component → eval family | where the behaviour is graded |
| `tests` | eval family → finding, component, hypothesis | inverse of `tested_by` |
| `decided_by` | finding, component → decision | the choice that fixed the shape |
| `opens` | any → open question | an unresolved item the note depends on |
| `blocks` | open question → component, eval | what cannot be finished until resolved |
| `supersedes` / `superseded_by` | decision → decision | immutability of landed notes: a change is a successor |
| `related` | any → any | weak link, used sparingly |

## Tags

`fuzzing` on every note; `design/<subtype>`; `lang/go`, `lang/python`, `lang/rust` on
language-specific notes; `h1`…`h7` on notes that address a hypothesis; `verified` / `unverified`
on claims where the distinction matters inside a note body (not on the note). In Obsidian's graph
view the `fuzzing` tag selects the whole study; `design/finding` and `design/component` select the
build map.

## Conventions

- Filenames are kebab-case and unique across the folder; readable names are `aliases`.
- While `publication_status: draft`, a note may be amended in place; an amendment that changes a
  decision is marked in the body (*Amended by [[FTW-D-008-pbt-out-of-scope]]* is the form). Once a
  note leaves draft, its body is immutable and a change is a successor note linked by `supersedes`.
- British English. Numbers in tables, not prose. Every load-bearing claim names an annex section.
- The annexes keep their own internal source ids (`S1`, `H1`… inside R8, `C1`… inside R9); this
  vault's `H1`–`H7` are the failure hypotheses, and an annex-internal id is always qualified by
  its annex (`R8 §3.1 claim 5`).
