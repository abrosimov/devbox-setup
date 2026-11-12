---
note_id: "20261103150501"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: eval-plan
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval plan"]
tags: [fuzzing, design/eval]
patterns: ["SYSE.46"]
tests: ["[[agent-procedure]]"]
decided_by: ["[[FTW-D-004-evals-as-plugin]]"]
related: ["[[eval-fixtures]]", "[[eval-tooling]]", "[[acceptance-criteria]]"]
---
# Eval plan

## Claim under test

This specifies evaluation of the future configured agent, skills, tools, repository materials and
execution support together (SYSE.46). It does not establish that they already work.

For an explicitly assigned Go, Python or Rust fuzzing investigation, the agent must maintain a
scoped research question or reconnaissance aim and subject snapshot, justify work, qualify harness/oracle work,
retain useful inputs, and make evidenced continuation, pause, closure and reopening decisions.
Research can span multiple sessions. Ending a process or session is not a research conclusion.
Invocation, discovery, routing and trigger tests remain deferred; PBT and mutation analysis are excluded.

## Fixed conditions and baseline

Before a trial, declare the question/use or reconnaissance material/aim, source/experiment/dataset versions,
relevant dirty changes, supplied contracts, initial corpus, evidence and event sequence. Record model,
instruction/skill revisions, toolchain, executor, available support, permissions and the independent
correctness basis. Keep consequential conditions equal across compared arms and explain differences.

**B0** uses the same model, tools, research fixtures, persisted materials and resource constraints
without the proposed fuzzing skills. It is an actual measured alternative. Both arms receive the
same initial evidence and subsequent commit/dataset changes and interruptions. Additional baselines
need a named unresolved comparison rather than becoming a permanent extra workflow.

Declare proportionate effort/run limits for the trial and each experiment, including preparation,
retries and triage. Record cumulative actual effort across sessions; changing a label or starting a
new session does not erase it. The evaluator's own orchestration and grading cost is separate and
cannot complete missing agent work then credit it to the agent. There is no mandatory single B/R
wall-clock budget across the entire research lifetime and no process-supervisor readiness gate.

## Representative cases

| Family | Addresses | Specification |
|---|---|---|
| A — Applicability | [[H1-no-applicability-gate]] | [[eval-family-A-gate]] |
| B — Oracle | [[H4-crash-only-oracle]] | [[eval-family-B-oracle]] |
| C — Structure and seeds | [[H3-random-seeds-for-structured-input]] | [[eval-family-C-structure]] |
| D — Research lifecycle | [[H2-no-stopping-rule]] | [[eval-family-D-stopping]] |
| E — Conventions and execution | [[H5-harness-conventions]] | [[eval-family-E-conventions]] |
| F — Reporting | [[H6-crash-counting-reports]] | [[eval-family-F-reporting]] |
| G — Triage | [[H6-crash-counting-reports]], [[H4-crash-only-oracle]] | [[eval-family-G-triage]] |
| H — Charter | [[H7-no-objective-before-work]] | [[eval-family-H-charter]] |

Include evidence that answers a question, a valid inconclusive experiment, no useful next step, an
observable pause condition, a new session reading a checkpoint, irrelevant and relevant changes,
and repeated invalid work. Include new-corpus reconnaissance that forms a question, useful intermediate
inputs, and a new question while an earlier one remains closed. Reconnaissance needs concrete material,
an executable operation and a possible kind of knowledge gain; it need not predict the discovery.
A question-led experiment names the observation that could change its answer. Both account for cost.

The independent runner records supplied events, checkpoint editions, commands, process outcomes,
workspace diffs, raw logs and resource use. Its verifier builds the target and replays the relevant
corpus. A model claim, regex match or agent-authored exit-code file is not independent execution
evidence. Assessment of research decisions uses fixture facts and alternative outcomes; a judge
cannot invent missing evidence. Lifecycle tests inspect work actually performed after a claimed stop.

## Holdout and reporting

Keep final fixtures, event sequences and expected results outside adaptive development. Declare
case selection, repetitions and retry policy before qualification and retain every attempt. No
universal score, case count or holdout percentage is calibrated here.

Report separately: applicability, oracle/harness correctness, useful input retention, research
continuation/closure quality, checkpoint recovery, evidence reuse, finding classification, report
fidelity, elapsed execution time, cumulative cost and protected effects. A tied ceiling result is
not a regression; comparative claims name supported cases and conditions. [[acceptance-criteria]]
defines the qualification return.

The failed `go-kdl2` and `proj` attempts supply negative cases for unending investigation, false
oracles and scope/interpretation errors. Retrospective walkthroughs test whether a proposed rule
would distinguish those decisions; they do not demonstrate future agent effectiveness.
[[research-lifecycle-cases]] Case 5 is a proposed connected scenario, not another historical success.
Use its flow for development; reserve independently specified unfamiliar cases for qualification.
