---
name: fuzzing-campaign
description: Conduct and resume fuzzing research, retain useful corpora and justify the next experiment or closure.
---

# Fuzzing campaign

Carry a scoped investigation from available material to a supported answer or explicit limit.
Research can span commits, experiments, datasets and agent sessions. Its identity, evidence and
effort survive those sessions. PBT, mutation analysis and product repair are outside this workflow.

## Recover before continuing

Read the existing research record, relevant repository instructions and retained artefacts. Recover
the question or reconnaissance aim, method, last completed action and unfinished operation. Check
the actual commit plus relevant dirty changes, dataset/selection, harness, oracle and configuration.
Reuse unaffected results; inspect uncertain prior effects before repeating an operation.

For a new record or an incomplete handover, use [Research record](references/research-record.md).
Keep it in an existing repository note/artefact location. Do not build a checkpoint service.
On return, perform the next justified operation or identify its missing prerequisite; reading a
checkpoint by itself is not continuation. A new session cannot erase earlier failed attempts or cost.

## Choose the current contribution

Distinguish two useful modes; neither requires discovering a bug:

- **Reconnaissance:** name concrete material, a feasible inspection/replay/variation operation,
  possible kind of knowledge gain and a practical effort bound. Explore an unfamiliar corpus or
  promising intermediate input without demanding an exact hypothesis or proof of eventual value.
  Return observed differences, a question, a sufficient answer or a stated limit.
- **Question-led experiment:** state the question and use of its answer, the observation that could
  change that answer, the least sufficient available method, and completion/failure evidence.
  Consult prior work before retrying; identify what has changed in an unsuccessful attempt.

Use existing authority without asking for each routine step. Preparation, execution, copying,
replay, analysis, reproduction and minimisation count towards this experiment's practical limits
and the research's cumulative effort. There is no single mandatory wall-clock budget spanning
research pauses. A run limit constrains execution; it does not establish research sufficiency.

## Execute and return observations

1. Qualify the selected harness and oracle on independently expected cases before relying on a
   search run. Use the repository's engine commands and supported configuration; do not invent
   flag meanings or replace unavailable instrumentation with an assumed success.
2. Perform the declared operation and retain original inputs, relevant logs, commands, versions,
   completed/unfinished work and actual resource use. Record failures and interrupted attempts.
3. Preserve useful coverage-expanding, structured, boundary and regression inputs for replay.
   Read [Corpus and finding handling](references/corpus-and-findings.md) when importing a corpus,
   moving cache inputs, deduplicating, reproducing or reducing a failure.
4. Separate the observation from its explanation. Counters have engine/version-specific meaning.
   Flat coverage or execution rate can reflect search, rejection, minimisation or observation gaps;
   it does not alone prove saturation, safety, a broken harness or a need for another technique.
5. Classify candidates using the contract: confirmed product failure, harness/oracle error,
   environment failure, unconfirmed failure or no finding. Preserve uncertainty and original
   evidence. Correct authored harness defects within scope; report product defects.

## Decide from the result

Relate what was actually obtained to the question or learning aim. Select a useful continuation:
develop this branch, inspect another input family, repair an observation gap, retain material for
later use, or finish. Compare the attainable contribution with its full burden. A negative or invalid
result does not automatically oblige a retry; an unexplored possibility need not be exhausted.

| Research state | Required basis and next action |
|---|---|
| `ACTIVE` | A specific scoped operation has an attainable contribution and can be performed; carry it out |
| `PAUSED` | Record the missing observable condition and checkpoint; resume only when that condition is met and relevant assumptions still hold |
| `CLOSED` | Preserve the supported conclusion, limits and closure reason; pursue no more work on this question without a changed basis |

Use closure reasons `ANSWERED`, `INCONCLUSIVE`, `NO_JUSTIFIED_NEXT_STEP` or `CANCELLED` as defined
in the record reference. Keep research state separate from experiment status (planned, running,
interrupted, completed, invalid or blocked) and finding class. Ending a process does not answer a
question; closing a question does not claim the product bug-free. Pause has no implied polling loop.

## New corpora and changed questions

Inspect an incoming corpus through a bounded compatible replay or construction. Different bytes
alone do not establish different behaviour. Retain useful intermediate and non-crashing inputs and
their conditions of reuse; a closed generating question does not remove their replay value.

A new in-scope question may proceed while an old question stays closed. Link its source material,
shared evidence and effort. Reopen the old question only if new evidence or a changed assumption
could alter a named conclusion. Keep its former closure and revise the affected basis; unrelated
commits, reordered datasets or a new model session do not restart everything. Renaming a failed
attempt does not make it new research.

## Handover

Save the current record before ending a work episode. Report what this episode established, what
remains unresolved, useful input paths and observed replay status, current research disposition
and the justified next operation or resumption condition. Link raw evidence and state actual effort.
Do not report a planned action as completed, a retained input as committed, or a fixture replay as
proof of general effectiveness. Preserve existing user-owned material and approval boundaries.
