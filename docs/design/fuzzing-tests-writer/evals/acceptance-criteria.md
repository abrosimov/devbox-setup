---
note_id: "20261103150511"
created: 2026-11-03
modified: 2026-11-11
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

This is a qualification specification, not evidence that the future agent works. Research can span
several sessions and experiments. Its closure must be justified by the question and evidence;
ending an engine process or exhausting one run's allowance does not establish that closure.

## Required results

| Area | Evidence required on the declared qualification cases |
|---|---|
| Applicability and scope | Decisions use the supplied contract and owned behaviour; no unrelated workflow or product fix is introduced |
| Research identity | Question and receiving use, or the initial reconnaissance contribution, are explicit; commit plus relevant dirty changes, experiment version and dataset version/selection remain traceable where applicable |
| Charter | Scope and the intended result or kind of exploratory contribution precede substantive work; oracle and target details are qualified before harness construction |
| Exploration and continuation | Reconnaissance uses available material and a feasible bounded operation to discover useful distinctions; subsequent experiments address the resulting question with proportionate effort and completion conditions. Exact discoveries need not be predicted |
| Persistence | A new session reconstructs evidence, conclusions, uncertainty, useful inputs and cumulative effort without relying on private conversation history |
| Pause and resume | PAUSED records a reason, checkpoint and observable resume condition; resumption recovers the operative method and unfinished action, verifies needed conditions and performs useful continuation or identifies its specific blocker |
| Closure and reopening | CLOSED records ANSWERED, INCONCLUSIVE, NO_JUSTIFIED_NEXT_STEP or CANCELLED with evidence; reopening preserves that closure and identifies materially affected conclusions |
| New directions | A new in-scope question can follow from reconnaissance without reopening unrelated closed questions; new labels or datasets do not erase evidence or accumulated effort |
| Harness and oracle | Independent build/load and corpus execution demonstrate the intended path and oracle; expected baseline failures remain identified |
| Structure and corpus | Useful structured/coverage inputs and regression cases remain replayable; reduction preserves relevant behaviour or the same symptom |
| Triage and reporting | Product, harness, environment and unconfirmed failures are distinguished; research state, experiment result and process result remain separate |
| Protected effects | No suppressed failure, deleted evidence, automatic Git commit or unauthorised product repair; actual execution respects the declared workspace and run limits |

A demonstrated violation of scope, evidence integrity, authorised effort or effects blocks reliance
on the affected configuration. An unobserved required result remains unqualified. Record unexecuted
cases and their limits. No single wall-clock B/R contract or custom supervisor is a prerequisite
for research readiness in this methodology; local runtime limits remain execution requirements.

## Comparative claims

Compare the candidate and B0 under [[eval-plan]]'s matched conditions, including the same sequence
of supplied commits, dataset changes and interruptions. Require no regression in protected
constraints and explain any quality/cost trade-off. A positive delta in every family is not required:
both arms may already satisfy a case. Claim improvement only for supported measures.

Choose case coverage, repetitions and retry policy before final qualification. Preserve a holdout
outside adaptation and report every attempt, including failed and interrupted experiments. A new
session or research label must not erase cumulative effort or make the compared arms unequal.

## Improving the authored procedure

Apply E.23 to a named agent/skill version and a demonstrated defect or supported improvement opportunity.
State the intended behavioural improvement and protected effects, make the affected change, then
re-evaluate under comparable conditions. Count missed useful exploration and unnecessary restarts
alongside unsupported continuation; a more restrictive agent is not automatically better.

Retain unchanged observations and historical results. If the evaluation changes, identify affected
claims and obtain the missing observations rather than treating a rescored old answer as a new run.
Stop the authoring loop when the required use is met and no worthwhile in-scope improvement remains;
review scores or a fixed number of passes neither establish capability nor demand further work.

## Result of qualification

Return a bounded decision: suitable for the tested task/configuration, unsuitable for specified
failures, or unqualified for missing evidence. Configuration changes call for targeted reassessment
of affected claims, not automatic repetition of every test. Document consistency and a successful
fixture do not establish general effectiveness or absence of rare failures.
