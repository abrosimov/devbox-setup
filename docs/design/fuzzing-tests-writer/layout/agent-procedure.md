---
note_id: "20261103150401"
created: 2026-11-03
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
addresses: ["[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]"]
realises: ["[[applicability-gate]]", "[[input-shape-triage]]", "[[stopping-algorithm]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-A-gate]]", "[[eval-family-D-stopping]]", "[[eval-family-E-conventions]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]", "[[FTW-D-005-techne-fuzz-command]]"]
target_path: "roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md"
related: ["[[repository-placement]]", "[[automation-scripts]]"]
opens: ["[[FTW-OQ-010-agent-model-cost]]"]
---
# Agent procedure — `fuzzing_tests_writer`

Written per SYSE.47 ([[fpf-framing]]): each step names its evidence in, its return out, and the
predicate that decides the continuation. Limits that matter are enforced outside the model: the
engine cap is a command-line flag, the campaign script refuses to run without one, and the tool
allow-list excludes network and destructive commands.

| Step | Evidence in | Action | Return | Continuation predicate |
|---|---|---|---|---|
| 0 Context | diff or named entry points; language(s) | load the matching language skill and the three methodology skills; read existing `fuzz/`, `testdata/fuzz/`, `tests/fuzz/`, `.clusterfuzzlite/` | inventory of targets and corpora | an existing failing seed entry → step 6 first; never fuzz over an unfixed crasher |
| 1 Gate | one entry point at a time | apply [[applicability-gate]]; write the contract statement | `fuzz(method, oracle)` / `property-test` / `unit-test` / `do-not-fuzz` + quoted row | non-fuzz outcomes end this entry with a one-paragraph recommendation and a hand-off to `unit_tests_writer` when tests are still wanted |
| 2 Shape | input shape, fixtures, grammars, schemas | apply [[input-shape-triage]]; pick technique, seed source, shrinking plan | shape row + seed plan | >~90 % first-check rejection in a one-minute dry run → change row, not budget |
| 3 Harness | language skill template and checklist | write harness, seeds, dictionary; wire the seed corpus into the normal test run | files written | `go vet` / `cargo fuzz build` / import check clean **and** the seed corpus passes as unit tests, else fix before any campaign |
| 4 Campaign | budget class from the caller (default `interactive`) | run `fuzz_campaign.py` with the cap; it samples, applies the sanity gate and the plateau test ([[stopping-algorithm]]) | JSON: decision, counters, artefacts | `BLOCKED_HARNESS` → step 3; `CONTINUE` is impossible past the cap; crash → step 6 |
| 5 Escalate | plateau + coverage report | one rung of the ladder per plateau; at most two rungs in `interactive` | new seeds/dictionary or a new harness entry | rungs 4–6 start a new (target, corpus) ledger entry |
| 6 Triage | artefacts, crash states | minimise, reproduce three times, bucket, convert to the ecosystem's regression fixture ([[corpus-lifecycle]]) | bucket list with reproducers | unreproducible → separate list; contract panics and sub-1 s "hangs" are triaged out, not filed |
| 7 Report | all of the above | fill the template in [[reporting-and-claim-hygiene]]; list decisions needed | report | "What I need from you" is last (Stop hook) |

## Frontmatter decisions (Claude definition; archetype Code-Writing per `agent-builder`)

- `tools: Read, Write, Edit, Grep, Glob, Bash`; no `WebFetch`/`WebSearch`.
- `model: opus` — the gate and shape steps are decision-dense; keep `unit_tests_writer`'s
  complexity-escalation block for parity.
- `permissionMode: acceptEdits`; `maxTurns` set because the campaign is bounded by design.
- `skills:` the six new skills ([[skill-fuzzing-applicability]], [[skill-fuzzing-campaign]],
  [[skill-structured-input-generation]], [[skill-go-fuzzing]], [[skill-python-fuzzing]],
  [[skill-rust-fuzzing]]) plus `agent-communication`, `shared-utils`, `agent-base-protocol`,
  `code-writing-protocols`, `lint-discipline`, `code-comments`, and the existing
  `go-engineer`/`python-engineer`/`go-testing`/`python-testing` for idiom.
- Codex TOML adapter mirrors the Claude file as the other 29 do; the Gemini copy comes from `dot_ai`.

## Relations to existing agents and commands

- `unit_tests_writer` keeps example-based tests and receives the hand-off for non-fuzz outcomes.
- `code_reviewer` gets the three language review checklists appended to its skill list.
- A new `/techne-fuzz` command routes to this agent ([[FTW-D-005-techne-fuzz-command]]).
