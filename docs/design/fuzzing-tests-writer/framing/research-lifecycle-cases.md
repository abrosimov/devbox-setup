---
note_id: "20261111160000"
created: 2026-11-11
modified: 2026-11-11
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: research-lifecycle-cases
publication_status: draft
authorship: agent
assistant: codex
project: fuzzing-tests-writer
aliases: ["Research lifecycle cases"]
tags: [fuzzing, design/framing]
related: ["[[stopping-algorithm]]", "[[methodology-review]]", "[[fpf-framing]]", "[[eval-family-D-stopping]]"]
---
# Research lifecycle cases

This is a retrospective application of [[stopping-algorithm]], not an executed evaluation or a
claim that the earlier project methodology succeeded. The user's judgement that `go-kdl2` and
`proj` were failed attempts is retained. Source facts below are separated from the proposed
disposition. A process stopping would not have prevented a new session from repeating these chains.

Local documents/history were inspected on 2026-11-11 at go-kdl2
`bf04e59e190bbf926a8aee12f17fb233b2847858` and proj
`32d4fa51ed23e56397fee93171fa8a7cab2faf41`; no experiments were rerun. Each case has a bounded
question, a point where additional work needed justification, and evidence a later session can reuse.
Case 5 is a separate proposed construction, not historical evidence or an executed evaluation.

## Case 1 — go-kdl2 corpus compaction after S3 failed

**Recorded facts.** The [methodology audit, lines 118–130](https://github.com/abrosimov/go-kdl2/blob/bf04e59e190bbf926a8aee12f17fb233b2847858/docs/roadmaps/kdl2-go-full-implementation/research/methodology-weaknesses-gaps-and-improvements.md#L118-L130)
records the S2 result, a canonical-ordering defect in S3 and further materialisation/provenance work
in PRs #93/#94 for approximately 12.8 KB of additional reduction. The audit distinguishes a protocol
passing review from justification to execute it. That correction is visible in
[commit 1cb1290](https://github.com/abrosimov/go-kdl2/commit/1cb129029ccd808a8b24673324bbb2f8950606c4).

**Proposed disposition.** The S3 experiment is invalid for its claimed preservation result. That
does not automatically admit another compaction experiment. For the question whether further corpus
reduction warrants work, close `NO_JUSTIFIED_NEXT_STEP` when no material storage/replay need supports
the added effort. Keep any supported earlier result with its limitations; do not adopt the frontier
architecture or discard useful inputs as a consequence of closing the question.

**Checkpoint.** Preserve original/resulting corpus identities, preservation criteria, candidate
S3 output, the failed check and previous attempts/effort. A fresh agent should see why S3 was not
qualified and why improving the protocol was not itself a reason to continue.

**Reopening basis.** A new concrete storage or replay problem, or an applicable changed requirement,
could make additional reduction useful. An approved protocol, repaired script or new session alone
does not. Reassess the affected need and candidate only; reuse unaffected replay evidence.

## Case 2 — go-kdl2 latency admission after inconclusive measurements

**Recorded facts.** The [audit, lines 105–117](https://github.com/abrosimov/go-kdl2/blob/bf04e59e190bbf926a8aee12f17fb233b2847858/docs/roadmaps/kdl2-go-full-implementation/research/methodology-weaknesses-gaps-and-improvements.md#L105-L117)
records an order effect exceeding the policy boundary in v1 and `n_s* = none` in v3. Allocation
mechanisms had support; latency non-regression was not established at acceptable cost in that
environment. [Lines 201–230](https://github.com/abrosimov/go-kdl2/blob/bf04e59e190bbf926a8aee12f17fb233b2847858/docs/roadmaps/kdl2-go-full-implementation/research/methodology-weaknesses-gaps-and-improvements.md#L201-L230)
describe new uncertainty becoming another protocol. This is adjacent performance research within
the failed overall chain, not evidence of fuzzing effectiveness.

**Proposed disposition.** Close the current latency question `INCONCLUSIVE` under the recorded
measurement conditions if no worthwhile discriminator is available. Preserve the allocation
conclusions separately. Do not infer permission to ship from failure to establish non-regression.
If a concrete suitable environment is expected and the question remains active in the task, a
`PAUSED` disposition can instead name its availability/qualification as the resume condition.

**Checkpoint.** Retain configurations, order effects, measured quantities, raw observations, the
unresolved latency claim and the independently supported allocation result. Record which changes
would invalidate each conclusion.

**Reopening/resume basis.** A demonstrably suitable measurement environment, an applicable method
that can distinguish the alternatives, or a changed requirement can justify targeted work. Merely
renaming a protocol v4 or launching another reviewer does not. Without a concrete pending condition,
do not keep the question paused indefinitely.

## Case 3 — go-kdl2 zero-rate intervals and minimisation

**Recorded facts.** The [phase-3 record, lines 447–502](https://github.com/abrosimov/go-kdl2/blob/bf04e59e190bbf926a8aee12f17fb233b2847858/docs/roadmaps/kdl2-go-full-implementation/research/performance-and-fuzz-phase-3-evidence.md#L447-L502)
attributes all recorded zero-rate ticks to minimisation intervals; saved inputs replayed quickly.
It answers G-03 within those conditions without establishing a product hang. Some discarded mutants
could not be replayed, which limits the conclusion. The record does not prove a universal policy
for minimisation or corpus selection.

**Proposed disposition.** Close that attribution question `ANSWERED` for its recorded scope.
Studying every input shape's minimisation cost is a different possible question, not unfinished
work automatically inherited from G-03. This local answer does not rehabilitate the overall attempt.

**Checkpoint.** Preserve raw timestamps, engine/harness versions, corpus snapshot, retained inputs,
replay observations, excluded/unavailable observations and the exact bounded conclusion. Useful
inputs remain available for replay after research closure.

**Reopening basis.** A reproducible slow product invocation or a relevant engine/target/dataset
change that could defeat the attribution supports a targeted check. An unrelated commit or another
quiet counter with no new distinguishing evidence does not automatically reopen the full study.

## Case 4 — proj scope drift into an unsupported adversary

**Recorded facts.** The [retrospective, lines 58–113](https://github.com/abrosimov/proj/blob/32d4fa51ed23e56397fee93171fa8a7cab2faf41/docs/katoptron/2026/09/proj-review-scope-inflation.md#L58-L113)
records the original concern about damaging user state, briefs assuming an adversary without an
established threat model, and expanded work against absent threats. The document was introduced
in [commit 65a1447](https://github.com/abrosimov/proj/commit/65a1447ff7c29ae9b5da92a0147618f0a1a19849).
This is negative process evidence, not a fuzzing experiment. The project's
[testing document](https://github.com/abrosimov/proj/blob/32d4fa51ed23e56397fee93171fa8a7cab2faf41/docs/architecture/testing.md#L24-L25)
also distinguishes PBT; none of that workflow is imported here.

**Proposed disposition.** Close the unsupported adversary branch `NO_JUSTIFIED_NEXT_STEP` rather
than treating each imagined threat as an unresolved requirement. Continue the original, authorised
state-safety question only for concrete applicable scenarios. Closing the added branch does not
close an unanswered original question.

**Checkpoint.** Retain the original objective, actual usage assumptions, supported scenarios and
rejected assumptions, so the next agent does not reconstruct the same invented scope.

**Reopening basis.** Evidence of changed use, such as processing repositories supplied by other
parties, or a reproducible failure under the existing use can support a new assessment. A changed
threat model changes scope and needs corresponding authority; a new agent's imagination is not
evidence of that change.

## Case 5 — proposed new-corpus exploration across sessions

**Purpose and starting material.** The authorised task is to investigate a parser's handling of
permitted framed inputs. The target contract and an existing qualified harness are available at
commit C1. Corpus D1 contains a fixed set of unfamiliar optional-field combinations. An earlier
question about truncation inputs is closed; D1 does not contradict its evidence. No precise new
hypothesis or expected bug is supplied. C1 and D1 are illustrative identifiers, not real revisions.

**Proposed construction.** This walkthrough applies C.39 to the joins between operations, RMP.1:4.0
and C.40 to question formation, C.43 to the next choice, and GOALS.7/A.15.10 to recoverable work.
The pattern sources and allocation belong to [[fpf-framing]]. The observations below are stipulated
to explain the method; they must be supplied independently when the evaluation is implemented.

| Contribution | Operation and resulting material | Receiving use and limit |
|---|---|---|
| Inspect D1 | Check provenance and permitted use; replay a declared finite selection with the existing harness and inspect acceptance, rejection and reached behaviour | This reconnaissance can discover a distinction without predicting it. Preserve originals, selection, configuration and observations; do not claim to represent unseen inputs |
| Form a new question | Suppose one input reaches an optional-field decoder absent from the earlier corpus, without failing. Retain it and ask which permitted combinations in the declared selection reach that decoder | Link the new question to reconnaissance; retain the old truncation closure. Reached behaviour supports this question, not a defect or a general coverage claim |
| Define the experiment | Use the selected inputs and the harness's qualified path observation to compare those combinations; declare the selection, effort limit and answer condition before running | The retained input and observation method must actually be available to the experiment. Creating a question without executable material would leave this join incomplete |
| Execute and interrupt | Record completed replays and reached-path observations. Execution stops before the remaining selected cases are replayed | Retain inputs, completed case identities, commands/configuration and the pending comparison. An interrupted experiment does not answer the question |
| Resume in a new session | Give the agent only the persisted material and current checkout. It recovers the question, observation method and remaining cases, checks relevant changes, then performs the unfinished replay/comparison | A documentation-only commit does not invalidate the observations. A changed decoder or oracle requires reassessment of dependent results; reading a checkpoint alone is not continuation |
| Return and close | Suppose the selected cases have now been observed and their path distinctions explain which combinations reach the decoder | Close this bounded question ANSWERED, with selection and measurement limits. Preserve useful inputs for replay. Completion of the experiment does not prove the parser correct or finish every possible direction |
| Consider another direction | A later corpus may expose a different permitted construct, or new evidence may challenge this conclusion | Form a separately justified question in the first case; reopen affected reliance in the second. Neither action resets history or automatically authorises further work |

**Contrasting outcome.** If the first pass reveals no useful difference and no worthwhile next
operation, retain that limited observation and close the reconnaissance line. Do not fabricate an
explanation, reject all future corpora or repeatedly enlarge the selection merely to avoid stopping.
If it reveals a useful but unexpected distinction, allow that result to change the next question
within the authorised task. Retention of useful inputs remains independent of finding a crash.

**Independent checks.** Families C, D and H should exercise this connected case and its contrasting
outcome. Inspect seed artefacts, actual replay observations, the resumed operation and the final
answer to the bounded question. The evaluator must distinguish a correct local command from the
result required by the original task, and useful research from a succession of plausible plans.

## Transfer to independent evaluation

Family D uses these failure patterns in small controlled cases, not the complete historical
repositories. Give a later session only the persisted record and the current snapshot; check it
reuses a closed answer, waits on a real pause condition, reopens only affected conclusions and
does not turn an invalid/negative experiment into an automatic retry. Include a legitimate bounded
explanatory experiment and Case 5's initially unsettled direction so restraint does not become a
ban on useful research. These examples inform case construction; final qualification also needs
independent cases outside authoring and adaptation.

The evidence supports constructing these cases. Only later execution can establish that the actual
agent and its support perform the transitions correctly; document consistency is a narrower result.
