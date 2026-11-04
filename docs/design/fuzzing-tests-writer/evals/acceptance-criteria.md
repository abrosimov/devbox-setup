---
note_id: "20261103150511"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: acceptance
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Acceptance criteria"]
tags: [fuzzing, design/eval]
related: ["[[eval-plan]]", "[[next-iteration]]"]
---
# Acceptance criteria

A release of the agent is acceptable when, on the hold-out set, at the pinned model, three runs per
case:

| Family | Criterion |
|---|---|
| A Gate | no false "fuzz" on a do-not-fuzz or out-of-scope case in any run; no property-based test file written in any run |
| H Charter | charter precedes the first harness write in every run |
| E Conventions | compiles and passes the seed corpus in every run |
| B, C, D, F, G | plugin-eval aggregate ≥ 0.8 per family |
| all | the with-plugin delta over B0 is positive on every family |

## What the evals tune (non-holdout only)

The ◇ defaults of [[stopping-algorithm]], each a `fuzz_campaign.py` flag, tuned on family D cases
([[FTW-D-003-thresholds-as-flags]]).

## Reporting

Results kept as `aggregate-result.json` per run with model and date; a dashboard shows the
separated measures of [[eval-plan]], never one scalar.
