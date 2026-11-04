---
note_id: "20261103150511"
created: 2026-11-03
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
| A Gate | no false "fuzz" on a do-not-fuzz case in any run |
| E Conventions | compiles and passes the seed corpus in every run |
| B, C, D, F, G | plugin-eval aggregate ≥ 0.8 per family |
| all | the with-plugin delta over B0 is positive on every family |

## What the evals tune (non-holdout only)

The proposed defaults (◇ in [[stopping-algorithm]]): plateau window `max(10 min, 25 % elapsed)`,
the 10⁶-execution floor, the 2-minute sanity gate, the 50 % discoverability criterion, the ≤10 %
triage budget, the 90 % first-check rejection trigger. Each is a `fuzz_campaign.py` flag; family D
cases are written so that a wrong default flips a decision.

## Reporting

Results kept as `aggregate-result.json` per run with model and date; a dashboard shows the
separated measures of [[eval-plan]] and never a single scalar.
