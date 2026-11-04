---
note_id: "20261104100005"
created: 2026-11-04
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family H", "Charter"]
tags: [fuzzing, design/eval]
addresses: ["[[H7-no-objective-before-work]]"]
tests: ["[[fuzzing-charter]]", "[[agent-procedure]]", "[[skill-fuzzing-applicability]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family H — Charter before work

Six cases over the existing fixtures ([[eval-fixtures]]); no new fixture needed.

| Input the agent sees | Expected |
|---|---|
| "Fuzz the frame parser" on the binary-frame fixture | a charter (entry point, objective naming OOB/length-field allocation/round trip, oracle rung, out of scope, verifiable result, budget class) exists before the first harness file; the final report restates it and ticks each result item |
| "Add fuzzing" with no entry point named, on the Go fixture | the agent enumerates candidates, runs the gate per candidate, and writes one charter per accepted entry point before any harness; rejected candidates are listed with their gate row |
| A charter whose objective is "find bugs" and oracle "does not panic" on the typed money API | returned to the gate as not a fuzzing task; `out-of-scope: pbt-track` with the reason |
| Mid-campaign plateau on the config-parser fixture | any harness change is recorded as a charter amendment via the escalation ladder; a new (target, corpus) entry with its own charter line |
| A campaign that ends with no findings at `smoke` budget | the report states "no findings at smoke; residual risk not quantified; coverage of `parse_body` reached/not reached" against the charter's verifiable result, not "clean" |
| Caller supplies a charter with budget `deep` in a PR context | the agent does not run `deep` in the PR job; it records the mismatch and runs `smoke`, leaving `deep` to a scheduled job |

## Graders

- `tool_order`: the charter write (file or report section) precedes the first harness `Write` in the
  trace.
- Regex on the charter: all seven fields present; the budget class and cap flag named; "Verifiable
  result" lists at least a harness path, a seed command and a decision token.
- Regex on the final report: opens with the charter restatement; each result item marked met / not
  met.
- LLM judge: objective names plausible bug classes grounded in the code's input kind; out-of-scope
  list is consistent with the gate decisions.
