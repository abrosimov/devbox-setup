---
note_id: "20261103150204"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Stopping algorithm"]
tags: [fuzzing, design/finding, h2]
addresses: ["[[H2-no-stopping-rule]]"]
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
tested_by: ["[[eval-family-D-stopping]]"]
decided_by: ["[[FTW-D-003-thresholds-as-flags]]"]
related: ["[[corpus-lifecycle]]", "[[reporting-and-claim-hygiene]]"]
---
# Research exploration and lifecycle — develop, continue, pause and close

The governed object is scoped research attached to a commit, experiment or dataset snapshot:
reconnaissance can form a question, and question-led work investigates its answer.
It can span many agent invocations and elapsed days. An agent session and a fuzz-engine process
are execution episodes, not the identity or lifetime of the research.

*Amended on 2026-11-11:* the former mandatory single wall-clock B/R deadline and supervisor
readiness gate conflated research closure with process termination. They are withdrawn. Local
execution limits remain ordinary experiment constraints; they do not decide whether the research
question is answered. [[FTW-D-003-thresholds-as-flags]] records the correction.

## Identify the research and preserve its basis

Record a stable research identity, question, receiving use and authorised scope. The use may be
an engineering decision or a bounded knowledge result, such as discriminating two explanations;
an immediate product change is not required. State what evidence would be sufficient for that use.
For initial reconnaissance, record the available material, the bounded area to examine and the kind
of knowledge sought; the exact question or hypothesis may emerge from that work. The reconnaissance
result can be a usable question, an observed distinction, a sufficient answer or a stated limit.

Bind observations to the relevant snapshot: repository commit plus any relevant uncommitted delta;
experiment definition and configuration version; dataset identity, content/version and selection.
Use the dimensions the claim depends on, not a mandatory inventory of unrelated metadata. A branch
name or a mutable dataset path alone does not identify what was tested.

A compact durable record holds current findings and their evidence links, assumptions, unresolved
distinctions, experiment attempts and effort already spent, retained inputs, and the current
lifecycle state with its reason. Follow repository conventions. The record must be enough for a
fresh session to continue without rediscovering completed work. Do not commission a new registry.

## States and transitions

| State | Meaning | Permitted next step |
|---|---|---|
| `ACTIVE` | A scoped question has justified work that can currently be performed | Conduct the admitted experiment; record its result and reassess continuation |
| `PAUSED` | Progress waits for a named, observable condition | Save a checkpoint and stop pursuing the question; resume only after the condition is observed and the basis is rechecked |
| `CLOSED` | No further investigation is justified for the current basis and receiving use | Preserve the conclusion, limitations and closure reason; reopen only on a material change described below |

Closure reasons are `ANSWERED` (sufficient result obtained), `INCONCLUSIVE` (available evidence
cannot resolve the question and no worthwhile next experiment is available),
`NO_JUSTIFIED_NEXT_STEP` (further work lacks sufficient relevance, value or authority), and
`CANCELLED` (the user ends this research). State the actual reason; closure is not a bug-free claim.
`INCONCLUSIVE` describes an unresolved result; `NO_JUSTIFIED_NEXT_STEP` also covers a question whose
receiving use has disappeared. Do not relabel one as success.

A pause records the missing condition, why it matters, the checkpoint and how to recognise a
change. Examples are an unavailable environment needed for a discriminating measurement or an
explicitly requested later continuation. An unknown with no plausible resolution condition is not
a reason to leave an endless pending investigation. There is no polling schedule or automatic
retry implied by `PAUSED`.

## Admission of another experiment

After every experiment, including an invalid or interrupted attempt, ask whether another is justified.
Record the answer compactly with the result; a separate design document per step is unnecessary.

1. Recover prior results, failed attempts and useful inputs. Identify whether the next contribution
   explores available material to form a question or investigates an already formulated question.
2. For reconnaissance, name the material, executable operation and kind of observable contribution:
   for example, distinguish input families or discover which behaviour a corpus reaches. The exact
   discovery and its eventual usefulness need not be known beforehand. For a formulated question,
   state the possible observations and how they would change its explanation or answer.
3. Choose the least sufficient available method. Explain what differs from an already unsuccessful
   attempt; a retry can be justified by a corrected condition, not merely by a fresh session.
4. Check scope, authority and proportionate effort. State practical cost/resource limits and the
   experiment's end condition, including preparation, analysis, minimisation and reproduction where
   required. Preserve accumulated effort across attempts; a new label never erases it.
5. Continue within existing authority when these conditions hold. Otherwise close with limitations,
   or pause only for a meaningful resume condition. Do not ask for approval of every routine step.

A valid negative result is a result. An invalid experiment needs its defect recorded; repairing it
is a candidate next action, not an automatic obligation. A new technique is not a reason by itself
for a new experiment. Uncertainty discovered while investigating does not become mandatory debt.

## New corpora and directions

Inspect new material for behaviour-changing differences, using bounded reconnaissance when those
differences are not yet known. A new corpus may supply seeds for an existing experiment, challenge a
conclusion, or expose a different in-scope question. Preserve the observed distinction, actual inputs
and conditions of reuse. A byte-level difference alone establishes none of these contributions.

Choose the next operation from what was observed: develop a promising branch, inspect another input
family, repair inadequate observation, retain material for later use, or close this line. Compare its
attainable contribution with the work and resources required. A promising intermediate input can
receive a bounded investigation without a promise that its descendants will reveal a defect.
An unexplored possibility does not require exhausting every branch.

A new question can proceed while an earlier question stays closed. Link its origin and shared
evidence, preserve cumulative effort, and check existing scope and authority. Reopen the old question
only when new evidence changes its basis. Neither closure nor a dataset hash prohibits legitimate
new exploration or authorises an automatic restart. Useful inputs remain available for replay.

## Pause, resume and changed subjects

Before returning from a session, save the last completed operation, unfinished attempt, original
and reduced inputs, replay context, evidence pointers and research disposition. If execution was
interrupted, record what is known and unknown; never imply the interrupted experiment completed.
Experiments may be planned, running, interrupted, completed, invalid or blocked. These statuses and
product/harness/environment finding classes are separate from the three research states.

On resume, read the checkpoint, observe the named resume condition, compare the current subject
with the recorded snapshot and check the planned step's assumptions. Recover the question, method,
last completed action and unfinished operation, then perform its justified next step or report the
specific missing prerequisite. Reuse unaffected work. An
unchanged question and basis do not warrant repeating the investigation. A budget or tool timeout
may leave an experiment interrupted; it does not determine research closure without this assessment.

For a closed question, a new commit, experiment version or dataset hash is only a candidate change.
Identify which evidence or assumption it affects and why the conclusion could differ. An unrelated
commit, reordered equivalent data or another model session is not enough. A relevant decoder fix,
a changed contract, a newly available discriminating dataset or evidence contradicting an assumption
can justify a targeted reopening. Record the old closure and the changed basis, not a silent reset.

Keep the research identity with a new basis revision when the question/use remains the same. A
materially different question or scope has a linked successor and its own authority check. Creating
that successor cannot bypass scope or erase cumulative cost. Invocation/routing policy remains
separate: these are conditions for valid continuation after assignment, not automatic call triggers.

## Evidence limits and checks

Engine counters describe their actual observations. No saturation outcome, mandatory escalation
ladder or generic residual-risk estimator is adopted. Useful inputs remain available for reuse and
replay under [[corpus-lifecycle]], even when a question closes.

[[research-lifecycle-cases]] applies this method retrospectively to failed project attempts, with
facts separated from proposed closure points. [[eval-family-D-stopping]] specifies independent
multi-session checks. [[automation-scripts]] defines checkpoint/evidence support for later authoring;
writing these notes does not establish that an agent will obey the lifecycle.
