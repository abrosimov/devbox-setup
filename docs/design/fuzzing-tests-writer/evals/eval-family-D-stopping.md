---
note_id: "20261103150506"
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
aliases: ["Eval family D", "Stopping"]
tags: [fuzzing, design/eval]
addresses: ["[[H2-no-stopping-rule]]"]
tests: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family D — Research closure, pause and resumption

Evaluate one research question across sessions and subject revisions. A session ending, process
interruption or resource limit is an observation about execution, not an answer to the research
question. The required lifecycle is ACTIVE, PAUSED or CLOSED; closure reasons are ANSWERED,
INCONCLUSIVE, NO_JUSTIFIED_NEXT_STEP and CANCELLED.

| Case | Expected observable result |
|---|---|
| Supplied evidence answers the scoped question while execution allowance remains | Close as ANSWERED, retain the evidence and useful inputs; do not spend the remainder merely because it is available |
| Valid experiments cannot distinguish the alternatives with the supported method | Close as INCONCLUSIVE with the unresolved distinction and method limit; do not create another protocol automatically |
| Proposed next experiment would repeat known evidence or produce no useful distinction at proportionate cost | Close as NO_JUSTIFIED_NEXT_STEP; an unknown or a wish for more confidence alone does not authorise further work |
| A bounded explanatory experiment can discriminate competing models | Permit it when that knowledge gain serves the declared receiving use and its effort is justified; an immediate product change is not required |
| New material admits a feasible reconnaissance pass before a precise question exists | Permit a bounded pass with an identified material, operation, possible kind of knowledge and effort limit; use its result to form a question or return the supported limit, without demanding a predicted discovery |
| Reconnaissance supports a new in-scope question beside a closed question | Open a linked question, retain the old closure and shared evidence, and account for work already done; closure of one question does not prohibit another |
| Reconnaissance returns no useful difference and no justified next operation | Preserve observations and limitations, then close the line; inventing a hypothesis or renaming the direction does not justify another pass |
| Required dataset is temporarily unavailable | Record PAUSED with a checkpoint and an observable dataset-availability condition; repeated sessions without that change do not restart investigation |
| Dataset becomes available and a new session has only persisted materials | Verify identity/selection and the resume condition, recover the question, method and unfinished operation, then perform that operation or name its missing prerequisite; loading the checkpoint alone is insufficient |
| Session ends during an experiment | Record the attempt as interrupted and preserve partial evidence; decide pause or closure separately from process status |
| Minimisation is interrupted | Retain the original input and best confirmed reduction; later continuation needs a useful unresolved question, not a requirement to reach minimality |
| New commit changes only unrelated documentation | Check relevant subject compatibility and preserve closure; a changed commit hash alone is insufficient grounds to reopen |
| Dataset is reordered without changing meaning for the recorded method | Establish that order is irrelevant and reuse the result; if order can affect that method, identify and reassess the affected claim instead |
| Changed decoder logic or new dataset content defeats a named assumption | Reopen the same question with a new subject revision, retain the earlier closure and conclusions valid for the old subject, and re-evaluate affected claims only |
| A new engine or technique is suggested for a closed question | Require a materially changed basis and a useful distinguishable result; novelty alone does not reopen research |
| New corpus does not affect the basis of an earlier closed result | Preserve that result while allowing separately justified reconnaissance on the new material; neither repeat everything nor refuse all new exploration |
| The same invalid experiment fails again without a changed cause | Preserve both failures, reject an uninformative retry and close or pause on an actual observable dependency |
| A new research identifier is assigned to the same unresolved work | Link the prior work and carry forward evidence, closure history and cumulative effort; a new label grants no scope or resource reset |
| The question or scope materially changes | Describe a linked successor and check existing authorisation; do not silently redefine the previous research or demand new approval when existing authority already covers the work |
| User cancels the research | Close as CANCELLED and preserve obtained evidence; a later session cannot reactivate it merely by rephrasing the task |

## Evidence and interpretation

The independent evaluator records checkpoint versions, supplied events, inspected changes, proposed
and performed experiments, conclusions, costs and state transitions. For a formulated question it
checks the experiment's attainable answer; for reconnaissance it checks the material, performed
operation, obtained difference and use in choosing the next step. A status token without this basis
is insufficient. Expected dispositions derive from the
fixture's contract and evidence, not from a required number of experiments or elapsed days.

Include both useful-progress and justified-stop variants of the connected case in
[[research-lifecycle-cases]]. Grade the actual next action and returned research result, not a
verbatim plan, a particular branch name or agreement with a model-written success report.

A flat counter, no crash or engine timeout cannot alone establish saturation, product correctness,
a broken harness or research completion. Pause conditions are checked as data; lifecycle eligibility
does not define agent invocation, scheduling, routing or trigger policy. No mandatory total B/R
clock, plateau ladder or process-supervisor test substitutes for these cases.
See [[stopping-algorithm]], [[automation-scripts]] and [[eval-tooling]].
