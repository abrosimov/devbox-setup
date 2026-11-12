---
note_id: "202611031506003"
modified: 2026-11-11
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-003"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[stopping-algorithm]]", "[[automation-scripts]]", "[[eval-family-D-stopping]]"]
---
# FTW-D-003: Close research by its result and justified continuation

*Amended in draft on 2026-11-11 following the user's correction.*

The previous edition incorrectly made a mandatory end-to-end wall-clock B/R allowance and process
supervisor the solution to endless research. Withdraw that requirement. The user needs research
per commit, experiment or dataset to pause, resume and close across multiple agent invocations.

Adopt the lifecycle in [[stopping-algorithm]]: stable identity and versioned basis, ACTIVE/PAUSED/CLOSED
states, durable checkpoints, explicit closure reasons, and evidence-backed continuation or reopening.
Another contribution must offer attainable knowledge at proportionate cost. Reconnaissance starts
from concrete material and an executable operation; its exact question or discovery may emerge from
the work. A question-led experiment identifies observations that could resolve its distinction.
An explanation or model discrimination can be the result; an immediate product decision is not
necessary. Mere remaining uncertainty, a fresh session or new technique does not justify work.

**Alternatives considered:** a single wall-clock deadline stops an execution episode but cannot
represent paused research; a per-run reset permits the same investigation to restart indefinitely.
Persistent conclusions and justified transitions address the cross-session problem directly.

**Consequences:** execution limits stay local to experiments and applicable resource policy. Preserve
attempts and cumulative effort, including preparation/triage, without imposing a universal clock
through pauses. A new commit/dataset requires checking which conclusions it affects. Same question
keeps its identity with a revised basis; a changed question has a linked successor within authority.
No mandatory supervisor implementation or process-control proof gates methodology readiness.

**Checks:** [[research-lifecycle-cases]] supplies negative historical cases and a proposed new-corpus
case. [[eval-family-D-stopping]] checks legitimate exploration, preservation, closure, targeted
reopening and refusal of unproductive continuation. These are future behavioural checks.
