---
note_id: "20261103150101"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: fpf-frame
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FPF framing"]
tags: [fuzzing, design/framing]
related: ["[[system-characterisation]]", "[[research-corpus]]", "[[fuzzing-tests-writer]]"]
patterns: ["G.2", "RMP.7", "SYSE.47", "SYSE.46", "C.11.DUA"]
---
# FPF framing

## Receiving use

One piece of future work consumes this study ([[next-iteration]]): authoring, for the `dot_ai`
pipeline of this repository, an agent definition with a Codex TOML adapter, a set of skills, their
reference documents, supporting scripts under `dot_claude/bin/`, and the evals that gate them. The
study is sufficient (`C.39`) when that work can start without re-harvesting sources and every rule
it writes can be traced to an annex entry ([[research-corpus]]).

## Entry patterns

| Pattern | Why it governs | What it produced |
|---|---|---|
| `G.2` SOTA-PORTFOLIO (Core) | The field is plural (greybox, grammar, property-based, symbolic, differential/metamorphic, stateful) and the user asked where fuzzing applies and where it does not; a single-winner answer cannot give that. | The annexes: corpus ledgers, claim sheets per tradition, disagreements kept visible, candidate inventories (skills, eval cases) as stubs. |
| `RMP.7` Synthesize a research evidence corpus | Tool docs, a textbook and papers are different evidence kinds; several blog posts restate one paper. | Independence notes per annex; this synthesis counts traditions, not documents. |
| `SYSE.47` Construct an agent's execution procedure | The deliverable is a procedure with observable inputs, returns and continuation predicates, with limits enforced outside the model's narrative. | [[agent-procedure]]. |
| `SYSE.46` Test an agent in representative work | Earlier attempts failed; the eval must contrast with a real baseline, include bounded-stop cases, keep final cases outside tuning. | [[eval-plan]]. |
| `C.11.DUA` | No evidence is demanded beyond what a decision needs; a threshold without a source is a proposed default, not a citation. | The ✓/◇ marking in [[stopping-algorithm]] and [[FTW-D-003-thresholds-as-flags]]. |

## Result test

- **Result kind**: a source-linked plural view of fuzzing methods with validity regions, a
  construction specification for one agent and its support, and an eval design.
- **Receiving use**: the authoring work in [[next-iteration]].
- **Binding**: each finding note cites annex sections; each component note cites the findings it
  realises; each eval family cites what it tests. Where a governor is missing the note says so
  (`open_questions/`) and the claim is not weakened to produce an answer.
