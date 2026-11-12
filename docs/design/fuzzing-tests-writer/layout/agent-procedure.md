---
note_id: "20261103150401"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: agent-procedure
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Agent procedure", "fuzzing_tests_writer"]
tags: [fuzzing, design/component]
addresses: ["[[H7-no-objective-before-work]]", "[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]"]
realises: ["[[fuzzing-charter]]", "[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]", "[[input-shape-triage]]", "[[stopping-algorithm]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-H-charter]]", "[[eval-family-A-gate]]", "[[eval-family-D-stopping]]", "[[eval-family-E-conventions]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]", "[[FTW-D-005-techne-fuzz-command]]", "[[FTW-D-008-pbt-out-of-scope]]", "[[FTW-D-009-charter-before-work]]"]
opens: ["[[FTW-OQ-010-agent-model-cost]]"]
target_path: "roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md"
related: ["[[repository-placement]]", "[[automation-scripts]]"]
---
# Agent procedure — `fuzzing_tests_writer`

This is a methodology contract for research that may span multiple agent sessions. A session or
process ending is not the research stopping rule. The six skills in [[FTW-D-002-six-skills]] supply
operations: [[skill-fuzzing-applicability]], [[skill-fuzzing-campaign]],
[[skill-structured-input-generation]], [[skill-go-fuzzing]], [[skill-python-fuzzing]] and
[[skill-rust-fuzzing]]. Their functional descriptions support ordinary provider discovery; advanced invocation conditions,
routing and command choice remain deferred. Research continuation does not define a trigger policy.

## Persistent research subject

Use one research identity for a question and the use of its answer, or for bounded reconnaissance
of concrete material before a precise question emerges. The contribution may be a new question,
an observed distinction, an explanation or an engineering decision. Record the
subject snapshot precisely: repository commit and relevant dirty delta, experiment definition and
version, or dataset version/hash and selection. These anchors can be combined when an experiment
uses a dataset against a commit. A label such as “latest corpus” is insufficient to compare evidence.

The compact record under [[fuzzing-charter]] carries scope and authority, assumptions, existing
evidence, current conclusion, unresolved distinctions, cumulative effort and the next disposition.
Use repository conventions and links to artefacts rather than creating another storage service.
Preserve the record between sessions. Reconstruct missing context from it before doing more work;
never treat a new context window or model invocation as a new research budget or blank history.

## Research lifecycle

| State | Meaning and required evidence | Allowed transition |
|---|---|---|
| `ACTIVE` | An authorised reconnaissance, experiment or interpretation has a concrete attainable contribution | Perform the scoped operation, then use its result to choose further work, pause or closure |
| `PAUSED` | Work cannot currently proceed; record reason, checkpoint and an observable condition for resumption | Resume after observing the condition and checking snapshot/assumption compatibility; no timer-only retry |
| `CLOSED` | Record conclusion, limitations, retained evidence and a closure reason | Reopen only on material new evidence or a relevant change affecting a named conclusion |

Closure reasons are `ANSWERED`, `INCONCLUSIVE`, `NO_JUSTIFIED_NEXT_STEP` and `CANCELLED`.
`ANSWERED` means enough evidence for the declared receiving use, not a bug-free product.
`INCONCLUSIVE` records that the question could not be resolved by the completed work.
`NO_JUSTIFIED_NEXT_STEP` closes a line where remaining uncertainty does not justify another
available authorised experiment. Use `PAUSED` only with an observable resumption condition, not as
an indefinite placeholder for any unknown. Cancellation closes the current research as requested.

An experiment has its own planned, running, interrupted, completed, invalid or blocked status.
Its result and the research state are distinct: an interrupted process leaves an incomplete
experiment, while a completed no-finding experiment may close a question or support a justified
next experiment. A harness/environment fault does not by itself settle the research question.

## Operations and observable continuations

| Step | Evidence in | Permitted operation | Observable return |
|---|---|---|---|
| 0 Recover or establish research | assignment, subject snapshot and any existing record | recover question/learning aim, method, evidence and unfinished operation; for new work record material, contribution, authority and scope | usable working basis and current revision; perform the next justified action |
| 1 Assess applicability | target contract, existing corpus, failures and earlier results | apply [[applicability-gate]] within [[fuzzing-vs-pbt-boundary]] | supported method/oracle or a reasoned refusal; no alternate test suite authored |
| 2 Select the next contribution | concrete unexplored material or a formulated question; existing evidence | choose bounded reconnaissance or a question-led experiment under [[fuzzing-charter]]; state operation, possible contribution, effort and completion/failure evidence | scoped work that can form a question, resolve it, or return an explicit limit |
| 3 Prepare and qualify | accepted experiment, input contract and language operations | select useful seeds/structure; build and independently check replay, oracle and instrumentation | actual qualification evidence or a classified experiment blocker |
| 4 Execute and preserve | qualified target and experiment limits | perform the defined work, retain raw observations and useful inputs as it proceeds | experiment result/status with provenance and consumed effort; no automatic technique ladder |
| 5 Interpret and assess findings | observations, assumptions, contract and originals | distinguish product/harness/environment failures; reproduce or minimise only when justified and within the experiment's limits | supported conclusion or explicit uncertainty; original evidence retained |
| 6 Decide and checkpoint | observed result, unexplored material, remaining questions and accumulated effort | apply [[stopping-algorithm]]; continue a branch, investigate another, pause or close; distinguish a new question from reopening an old one | durable disposition, retained artefacts and report under [[reporting-and-claim-hygiene]] |

Preparation, retries, replay, minimisation and reproduction count towards the experiment's declared
cost/effort limits and the research's cumulative record. There is no mandatory single wall-clock
`B/R` deadline spanning sessions and pauses. Local engine/process limits are execution details;
they neither prove research sufficiency nor authorise another experiment. No supervisor is a
methodology-readiness prerequisite. Expired local resources require an explicit research disposition,
not a fresh limit and automatic retry.

For reconnaissance, name the available material, operation and kind of possible knowledge gain;
do not demand an exact hypothesis or proof of an unknown discovery's value. For a formulated
question, identify the observation that could change its answer. In either case reuse sufficient
evidence, account for cost and choose the least sufficient in-scope operation. A negative or
inconclusive result does not force repetition. Use existing authority without repeated permission.

## Connect the skills to the work

Use [[skill-fuzzing-applicability]] to obtain a target, oracle basis and charter. When input reachability
needs investigation, [[skill-structured-input-generation]] returns seeds or a bounded decoder plus
observed behaviour and unresolved limits. Pass those artefacts and their assumptions to the relevant
Go, Python or Rust skill; its qualification results establish which harness observations can be used.
[[skill-fuzzing-campaign]] connects execution, corpus retention, interpretation and research disposition.
An unavailable prerequisite returns to the operation that supplies it; do not silently invent it.

These are result dependencies, not a mandatory six-skill sequence. Reuse an adequate harness or corpus
directly. A new corpus can open a new in-scope question while earlier questions remain closed.
[[research-lifecycle-cases]] Case 5 follows the complete construction and its failure conditions.

## Resume, reopen and reuse

Resumption restores the question, method and unfinished operation after its pause condition is met.
Check inputs, toolchain,
experiment definition, dataset selection and relevant code changes before reusing evidence. Mark
affected observations stale or needing requalification while retaining their original context.

Reopening a closed question records the new evidence or changed assumption, the conclusion it
could alter, and why another experiment now matters to that use. Preserve the earlier closure; use a new
revision of the same research identity when the question is unchanged. A changed question/scope
gets a linked successor only within the available authorisation. A new commit or dataset hash alone
is not a reason to repeat all work; identify the affected claims and reuse unaffected evidence.
Renaming a question cannot erase effort, failed attempts or prior conclusions.

Useful coverage-expanding, structured and regression inputs remain available for replay under
[[corpus-lifecycle]]. Findings retain separate classes: confirmed product failure, harness/oracle
error, environment failure, unconfirmed failure or no finding. Product defects are reported;
corrections to the authored harness are permitted within scope. No automatic Git commit is implied.

## Method and delivery boundary

SYSE.47 connects operations and durable returns; SYSE.48 supplies reusable operation contracts;
[[fpf-framing]] binds the evidence and decision methods. The failed go-kdl2/proj attempts supply
counterexamples, not architectures to reproduce. [[automation-scripts]] specifies checkpoint,
evidence and disposition support, realised through the campaign skill and repository-local record.
GOALS.7 separates the current promised contribution from the continuing research; A.15.10 requires
using the recovered basis to continue work. [[authoring-budgets]] records the compact authored entrypoints;
the detailed lifecycle and evidence remain directly reachable rather than copied into each skill.

[[repository-placement]] records the authored Claude Code and Codex definitions and their loading
choices, checked against current official documentation. [[authoring-validation]] records local
verification and its limits; full behavioural qualification remains incomplete.
[[FTW-OQ-010-agent-model-cost]] remains deferred; [[FTW-D-005-techne-fuzz-command]] does not settle
command choice. No Gemini delivery or deployment is included. PBT and mutation analysis remain excluded.
