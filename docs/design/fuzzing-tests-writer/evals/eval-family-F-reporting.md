---
note_id: "20261103150508"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family F", "Reporting"]
tags: [fuzzing, design/eval]
addresses: ["[[H6-crash-counting-reports]]"]
tests: ["[[reporting-and-claim-hygiene]]", "[[skill-fuzzing-campaign]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family F — Reporting

Reports distinguish research disposition, experiment result, execution status and finding class.
The number of files or stack signatures is not an independently established product-bug count.

| Case | Expected observable result |
|---|---|
| Many crash files sharing several stack signatures | Report provisional buckets and the failures actually reproduced; do not prescribe a unique-bug count from frames alone |
| Engine timeout with no standalone confirmation | Record the execution limit and unconfirmed symptom; do not label an infinite loop or treat the research question as answered |
| No failure in an experiment | State subject snapshot, reached behaviour, effort and limits; justify whether the research is answered, inconclusive, paused or has no useful next step |
| Useful new seeds and no product bug | Report retained/replayed inputs and demonstrated value without inventing a defect |
| Existing known issue encountered again | Link previous evidence, report recurrence and distinguish it from a new finding |
| Interruption during minimisation/reproduction | State original input, confirmed partial work, checkpoint and unresolved checks; do not imply completed reduction or automatic continuation |
| New session resumes saved work | Identify the prior checkpoint and compatible subject, preserve cumulative evidence and effort, and report only new observations as new work |
| Closed research is reopened after a relevant change | Retain the earlier closure, identify affected claims and explain the new evidence or changed assumption |
| Report claims successful execution contradicted by the runner | Mark the claim false and required evidence missing; do not accept prose over observed execution |

## Evidence

Compare report claims with independent observations. Require research identity/question/receiving
use, repository or dataset/experiment snapshot, current state and its reason, evidence locations,
actual attempts and effort, finding classification, confirmation status and retained inputs.
A PAUSED record includes the checkpoint and observable resume condition. A CLOSED record includes
its reason and limits. Do not fabricate commands as if run; proposals are labelled proposals.

Finding classes are confirmed product failure, harness/oracle error, environment failure,
unconfirmed failure and no finding. Research states and closure reasons follow
[[stopping-algorithm]]. Experiment statuses such as completed, invalid, interrupted or blocked
remain distinct: a completed experiment need not answer the research question, and an interrupted
run need not invalidate previous evidence.

Include user actions only for an actual dependency on their authority or information. Continuing a
justified experiment within existing authorisation does not require another permission round.
See [[reporting-and-claim-hygiene]].
