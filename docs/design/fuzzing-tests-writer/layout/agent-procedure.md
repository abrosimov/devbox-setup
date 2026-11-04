---
note_id: "20261103150401"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: agent-procedure
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Agent procedure", "fuzzing_tests_writer"]
tags: [fuzzing, design/component]
addresses: ["[[H7-no-objective-before-work]]", "[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]"]
realises: ["[[fuzzing-charter]]", "[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]", "[[input-shape-triage]]", "[[stopping-algorithm]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-H-charter]]", "[[eval-family-A-gate]]", "[[eval-family-D-stopping]]", "[[eval-family-E-conventions]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]", "[[FTW-D-005-techne-fuzz-command]]", "[[FTW-D-008-pbt-out-of-scope]]", "[[FTW-D-009-charter-before-work]]"]
opens: ["[[FTW-OQ-010-agent-model-cost]]"]
target_path: "roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md"
related: ["[[repository-placement]]", "[[automation-scripts]]"]
---
# Agent procedure — `fuzzing_tests_writer`

Limits are enforced outside the model: the engine cap is a command-line flag, the campaign script
refuses to run without one, the tool allow-list excludes network and destructive commands, and no
harness file is written before the charter exists.

| Step | Evidence in | Action | Return | Continuation predicate |
|---|---|---|---|---|
| 0 Context | diff or named entry points; language(s) | load the matching language skill and the three methodology skills; read existing `fuzz/`, `testdata/fuzz/`, `tests/fuzz/`, `.clusterfuzzlite/` | inventory of targets and corpora | an existing failing seed entry → step 7 first; never fuzz over an unfixed crasher |
| 1 Gate | one entry point at a time | apply [[applicability-gate]] with the [[fuzzing-vs-pbt-boundary]] | `fuzz(method, oracle)` / `out-of-scope: pbt-track` / `out-of-scope: unit-tests` / `do-not-fuzz` + quoted row | non-fuzz outcomes end this entry with a one-paragraph reason; `pbt-track` cases are listed for the PBT agent, `unit-tests` cases for `unit_tests_writer`; nothing is written for them |
| 2 Charter | the accepted entry points, code history, input kind | write the [[fuzzing-charter]]: objective with plausible bug classes, oracle rung and contract, out of scope, verifiable result, budget class and stop rule, success/failure criteria | charter (≤ 25 lines) in the report draft or `FUZZING.md` | a charter that cannot name a bug class or whose oracle is crash-only on a typed API goes back to step 1; **no harness `Write` before this step returns** |
| 3 Shape | input shape, fixtures, grammars, schemas | apply [[input-shape-triage]]; pick a fuzzing-side decoder or byte technique, seed source, minimisation plan | shape row + seed plan | >~90 % first-check rejection in a one-minute dry run → change row, not budget |
| 4 Harness | language skill template and checklist | write harness, seeds, dictionary; wire the seed corpus into the normal test run | files written | `go vet` / `cargo fuzz build` / import check clean **and** the seed corpus passes as unit tests, else fix before any campaign |
| 5 Campaign | budget class from the charter | run `fuzz_campaign.py` with the cap; it samples, applies the sanity gate and the plateau test ([[stopping-algorithm]]) | JSON: decision, counters, artefacts | `BLOCKED_HARNESS` → step 4; `CONTINUE` is impossible past the cap; crash → step 7 |
| 6 Escalate | plateau + coverage report | one rung of the ladder per plateau; at most two rungs in `interactive`; each rung is recorded as a charter amendment | new seeds/dictionary or a new harness entry | rungs 4–6 start a new (target, corpus) ledger entry with its own charter line |
| 7 Triage | artefacts, crash states | minimise, reproduce three times, bucket, convert to the ecosystem's regression fixture ([[corpus-lifecycle]]) | bucket list with reproducers | unreproducible → separate list; contract panics and sub-1 s "hangs" are triaged out, not filed |
| 8 Report | all of the above | restate the charter, fill the template in [[reporting-and-claim-hygiene]], mark each verifiable-result item met / not met, list decisions needed | report | "What I need from you" is last (Stop hook) |

The step shape (evidence in, return, continuation predicate) follows SYSE.47 ([[fpf-framing]]).

## Frontmatter decisions (Claude definition; archetype Code-Writing per `agent-builder`)

- `tools: Read, Write, Edit, Grep, Glob, Bash`; no `WebFetch`/`WebSearch`.
- `model: opus` — steps 1–3 are decision-dense; keep `unit_tests_writer`'s complexity-escalation
  block for parity ([[FTW-OQ-010-agent-model-cost]]).
- `permissionMode: acceptEdits`; `maxTurns` set because the campaign is bounded by design.
- `skills:` the six new skills ([[skill-fuzzing-applicability]], [[skill-fuzzing-campaign]],
  [[skill-structured-input-generation]], [[skill-go-fuzzing]], [[skill-python-fuzzing]],
  [[skill-rust-fuzzing]]) plus `agent-communication`, `shared-utils`, `agent-base-protocol`,
  `code-writing-protocols`, `lint-discipline`, `code-comments`, and the existing
  `go-engineer`/`python-engineer` for idiom. The `go-testing`/`python-testing` skills are loaded
  only for the seed-corpus-as-unit-test wiring.
- Codex TOML adapter mirrors the Claude file as the other 29 do; the Gemini copy comes from `dot_ai`.

## Relations to other agents and commands

- `code_reviewer` gets the three language fuzz-review checklists appended to its skill list.
- `/techne-fuzz` ([[FTW-D-005-techne-fuzz-command]]) routes to this agent and passes the budget
  class; the agent writes the charter itself.
