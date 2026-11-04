---
note_id: "20261103150501"
created: 2026-11-03
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

Per SYSE.46 §4.1: state the claim, choose a real baseline, protect the consequential effects,
separate the measures.

## Claim under test

Given a Go, Python or Rust repository and an entry point, the agent (a) decides correctly whether
to fuzz and how, (b) produces a harness that compiles, whose seed corpus passes as unit tests, and
that carries an oracle beyond crash where one exists, (c) runs a bounded campaign and stops with a
defensible decision, (d) follows the ecosystem's corpus and CI conventions, (e) reports buckets
with reproducers.

## Baselines

- **B0** — the bare model with no skills and the same tools. `claude plugin eval` runs a
  without-plugin arm natively, so B0 is free ([[eval-tooling]]).
- **B1** — the current `unit_tests_writer` asked to "add fuzz tests"; one extra arm driven
  headlessly.

## Protected effects

No network, no writes outside the fixture workspace, no engine run without a cap. Enforced by the
eval sandbox and by `fuzz_campaign.py`; graded as failures if the trace shows them.

## Separated measures

Decision quality · artefact quality · convention compliance · stop decision · report quality ·
cost and turns. Combined only in a dashboard, never into one scalar.

## Case families

| Family | Addresses | Note |
|---|---|---|
| A Gate | [[H1-no-applicability-gate]] | [[eval-family-A-gate]] |
| B Oracle | [[H4-crash-only-oracle]] | [[eval-family-B-oracle]] |
| C Structure and seeds | [[H3-random-seeds-for-structured-input]] | [[eval-family-C-structure]] |
| D Stopping | [[H2-no-stopping-rule]] | [[eval-family-D-stopping]] |
| E Conventions and compile | [[H5-harness-conventions]] | [[eval-family-E-conventions]] |
| F Reporting | [[H6-crash-counting-reports]] | [[eval-family-F-reporting]] |
| G Triage false positives | [[H6-crash-counting-reports]] | [[eval-family-G-triage]] |

≈59 cases; 30 % tagged `holdout` and run only before a release. Three runs per case per arm (the
tool's default; "one run tells you little"). Grader policy: deterministic for long artefacts, LLM
judge for decision prose and the report (R10).

## Contrasts the families must contain (SYSE.46 §4.2)

Cases that admit useful progress and cases that require a bounded stop; a sufficient supplied
premise (fixtures with a grammar), a decisive fact reachable only through a tool (the recorded log,
the coverage report), and offered material that is irrelevant or misleading (a `Must*` panic, a
legitimate 2.5 s decode reported as a hang). Final cases stay outside tuning ([[acceptance-criteria]]).
