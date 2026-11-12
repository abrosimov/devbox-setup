---
note_id: "20261110160000"
created: 2026-11-10
modified: 2026-11-12
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: methodology-review
publication_status: draft
authorship: agent
assistant: codex
project: fuzzing-tests-writer
aliases: ["Fuzzing methodology review"]
tags: [fuzzing, design/framing]
related: ["[[fpf-framing]]", "[[research-corpus]]", "[[agent-procedure]]", "[[eval-plan]]", "[[next-iteration]]"]
---
# Methodology review — finite work, useful inputs and qualified claims

The revised documents specify a bounded procedure and six skill operation contracts. They are
now implemented by two provider definitions and six shared skills. [[authoring-validation]] records
local checks; they do not establish correct cross-session behaviour or general agent effectiveness.
Advanced invocation conditions remain a separate decision. PBT and mutation analysis are
excluded throughout the current method, including its evaluations.

## Basis and authority

The user's assessment of `go-kdl2` and `proj` is **failed attempts**: exploration did not stop and
resources were wasted. That assessment governs this design. Repository records supply specific
counterexamples and history, not a licence to reinterpret those attempts as success. Scope and
useful-input retention follow the user. The mandatory B/R wall-clock was our mistaken interpretation
of stopping, corrected on 2026-11-11: research spans agent sessions, pauses and subject versions. FPF
organises the lifecycle; it does not manufacture empirical proof of its effectiveness.

| Evidence inspected | What it establishes | What it does not establish |
|---|---|---|
| [go-kdl2 history, 4 October](https://github.com/abrosimov/go-kdl2/commit/fd574ff3e21596259566b52f62f1cd97b726e85a), Finding 05/06 | Its own audit records successive review/amendment cycles and uncertainty becoming more research | That its proposed replacement procedure or frontier architecture succeeded |
| [go-kdl2 history, 5 October](https://github.com/abrosimov/go-kdl2/commit/1cb129029ccd808a8b24673324bbb2f8950606c4), Proposal 6 | A later correction distinguishes budget constraint from fuzzing sufficiency | That merely adding another decision step guarantees termination |
| go-kdl2 `docs/roadmaps/kdl2-go-full-implementation/research/performance-and-fuzz-phase-3-evidence.md`, lines 431–510 in the inspected checkout | Recorded zero-rate intervals coincide with minimisation; saved inputs replay quickly; engine time output can hide elapsed minimisation cost | A product hang, a universal minimisation policy, or evidence that useful inputs should be excluded from replay |
| go-kdl2 `docs/roadmaps/kdl2-go-full-implementation/research/fuzz-frontier-phase-0-inventory.md`, lines 405–416 | The recorded oracle expected a duplicate `required` error; the product's single error was correct; the nearest ordinary regression used a different input | That the fuzzing product found a real defect in this case. This example came from PBT; only its false-oracle lesson transfers, not its workflow |
| proj `docs/katoptron/2026/09/proj-review-scope-inflation.md`, “What I actually did” / “Consequences” | A retrospective records an invented adversary and resulting scope inflation | A measured causal account of all fuzzing failures; this is adjacent process evidence, not a fuzz campaign success |

Local checkouts were inspected at go-kdl2 `f345e460f4cbe71020775802f5c90c9a5082f0f7` and proj
`074bfbea3772845e32dc55d390f510e24c102a09`. Paths above are relative to those repositories; the
review did not run their tests or modify their files. GitHub commits above were read on 2026-11-10.
This is a targeted history check, not an exhaustive audit of every issue, PR or campaign.

## Disposition of the previous rules

| Previous claim or obligation | Basis for correction | Current rule and owning note | Independent check |
|---|---|---|---|
| Plateau/escalation, then a mandatory B/R process deadline, decide when research ends | User's correction: research persists per commit/experiment/dataset across sessions | Stable question/use, checkpoints, justified continuation, pause and closure: [[stopping-algorithm]] | Family D: delayed resumption, closed-result reuse, relevant/irrelevant changes, no uninformative retry |
| A quiet counter means saturation or a broken harness | Same indication fits working search, poor reachability, minimisation or missing telemetry; C.16.IR | Report the observation and unresolved alternatives: [[reporting-and-claim-hygiene]] | Families D/F: no saturation or bug-free conclusion |
| Search-useful corpus need not stay in replay | User explicitly rejected this inference | Preserve useful coverage/structured inputs and regressions: [[corpus-lifecycle]] | Families C/E/G: useful seed survives and replays |
| Recorded project policies are validated designs | Historical adoption is different from successful outcome; RMP.7 | Failed attempts provide defeating cases, not an architecture to clone | Families D/G/H: bounded work, oracle challenge and scope restraint |
| H1–H5 are confirmed causal explanations of earlier failures | General literature cannot prove local causality | Qualified hypotheses and design risks: [[ontology]] | Per-family behavioural tests, without causal ranking claims |
| PBT bridges and mutation analysis improve coverage of the study | Explicit scope exclusion | Removed from current operations, requirements and evals: [[FTW-D-008-pbt-out-of-scope]] | Scope cases and document consistency |
| Static checks, import success or model-written exit codes prove harness validity | They need not demonstrate meaningful execution | Independent build, replay and oracle observations: [[eval-family-E-conventions]] | Runner-owned logs/status and known expected observations |
| One Claude plugin recipe covers evaluation; trigger tests ship now | Both providers required; invocation deferred | Common case meaning, provider adapters later: [[eval-tooling]] | Current official docs plus actual adapter checks at authoring |
| Positive score improvement in every family is mandatory | A baseline may already satisfy a case | Protected constraints and supported comparative claims: [[acceptance-criteria]] | Matched conditions, held-out cases, all attempts reported |

## How much of the Fuzzing Book is used?

**Source coverage is broad; operational transfer was uneven.** The R4–R6 ledgers list 29 subject
chapters: seven in R4, eight in R5 and fourteen in R6. That count includes the now-excluded mutation
analysis chapter and short treatments; it is not a percentage of knowledge mastered. R4 explicitly
records only partial inspection of executed outputs. The notebooks were not executed in this pass.
The old part numbers in filenames are historical: the current contents put lexical fuzzing in II,
syntactic in III, and semantic/domain/managing in IV–VI.

| Book contribution | Before this pass | Transfer now | Limit |
|---|---|---|---|
| Seeds, dictionaries and coverage-guided input mutation (R4 §3.4–3.5; R5 §3.7) | Substantial source synthesis, mixed with generic escalation | Start with useful existing inputs; choose the least additional structure the target needs; preserve replay value | No fixed “seed usefulness” number or obligation to build a grammar |
| Grammar generation, repair and expansion coverage (R5 §3.1–3.7) | Covered, but grammar coverage also proposed as a stopping signal | Bound size/recursion, observe intended paths, distinguish grammar alternatives from code coverage in [[input-shape-triage]] | Covering grammar alternatives does not prove program coverage or absence of bugs |
| Failure reduction (R5 §3.8) | Reduction lacked explicit interruption/reuse semantics | Preserve the original and same symptom, distinguish unresolved replay, save resumable context in [[corpus-lifecycle]] | A saved partial reduction need not be repeated or completed without a useful next contribution |
| Discovery estimates (R6 §3.1, §5.2) | Formulas and proxies influenced saturation/escalation | Retain the lesson that interpretation depends on the measured quantity and assumptions | No residual-risk estimator or saturation gate is implemented or required |
| Reporting and bucketing (R6 §3.2, §5.3) | Crash signatures and report fields already present | Separate process outcome, finding class, evidence and uncertainty | Bucket count is not unique product-bug count |
| Advanced semantic/domain methods (R6 §3.3–3.8) | Mostly catalogue and short summaries | No new capability obligation; use only an already-supported operation justified by the scoped target | No new solver, model, integration-fuzzing or research workstream |

The primary [grammar coverage chapter](https://www.fuzzingbook.org/html/GrammarCoverageFuzzer.html),
[reduction chapter](https://www.fuzzingbook.org/html/Reducer.html) and
[stopping chapter](https://www.fuzzingbook.org/html/WhenToStopFuzzing.html) were revisited on
2026-11-10. They support the distinctions above; they do not prescribe this research lifecycle or its resource policy.
The retained byte-input path also prevents structure-aware generation from hiding malformed-input
behaviour that belongs to the target contract. No Book chapter automatically becomes a skill.

## Six skill responsibilities

| Skill | Concrete contribution |
|---|---|
| [[skill-fuzzing-applicability]] | Scoped suitability assessment, contract/oracle basis and charter |
| [[skill-fuzzing-campaign]] | Persistent research state, justified experiments, interpretation, triage, retention and report |
| [[skill-structured-input-generation]] | Useful seeds and bounded decoding/repair with meaningful path evidence |
| [[skill-go-fuzzing]] | Native Go harness, qualification, seed replay and engine artefact handling |
| [[skill-python-fuzzing]] | Python fuzz harness, instrumentation, rejection handling and replay |
| [[skill-rust-fuzzing]] | Rust fuzz harness, selected build/sanitizer configuration and replay |

These are operation preconditions and outputs, not conditions for invoking skills. SYSE.48 adds
that a useful source trace must be generalised and tested on a new case and a defeating case; it
does not justify packaging every historical procedure as another skill.

## Readiness and remaining boundary

The document-level method has a defined result, source-to-rule trace, operation decomposition and
qualification plan. Authoring now applies it without restarting the broad survey.
[[repository-placement]] records the actual packaging and loading choices; [[authoring-budgets]]
records provider size/loading evidence and measured runtime bodies. [[authoring-validation]] separates
local checks from remaining full lifecycle, Python/Rust runtime and comparative qualification.
Advanced invocation policy is undecided; nothing has been deployed.

The FPF result test is therefore: **method specification** → **authored definitions** → **rules linked
to evidence and observable checks**. It is not specification → successful deployment. Unknowns
that do not change an in-scope operation remain limitations rather than new research tasks.

## Historical validation of the 2026-11-10 revision

On 2026-11-10, all 80 document frontmatters parsed as YAML; all note IDs were unique and existing
IDs were preserved; 865 internal wikilinks resolved after excluding inline/fenced code. Whitespace
checks passed. Cross-document review aligned the initial charter before investigation with its
completion before harness construction, the B/R deadlines, outcome classes and deferred invocation.
The checks did not establish that the B/R framing was correct; it is now withdrawn.
No agent, skill, supervisor or executable evaluation was implemented or run. No commit or deployment
was made. These checks establish document consistency, not operational qualification.

## Correction and retrospective check on 2026-11-11

[[stopping-algorithm]] now governs research identity, ACTIVE/PAUSED/CLOSED state, closure reasons,
checkpoints and impact-based reopening across commits/experiments/datasets. Local process limits
remain execution details. A session restart cannot erase prior evidence or accumulated effort.
Another experiment needs attainable useful gain, including a bounded explanatory result where
appropriate, and proportionate cost. Existing authority is used without a new approval for every step.

[[research-lifecycle-cases]] walks four negative chains: further corpus compaction after an invalid
candidate, inconclusive latency measurement, answered minimisation attribution, and proj's unsupported
adversary branch. It identifies the proposed stopping point, retained evidence and a legitimate
changed basis for returning. Performance/process examples are explicitly labelled; they are not
fuzzing successes and do not import PBT or mutation analysis.

The walkthrough is retrospective reasoning from records, not an observed run of the proposed agent.
The updated evaluation specification tests faithful checkpoint recovery and receiving use in a new
session, closure despite unused execution allowance, pause without automatic retries, and targeted
reopening after a material change. These checks still need implementation and execution later.

Validation on 2026-11-11: 81 YAML frontmatters parsed, 81 unique note IDs with existing IDs retained,
and 881 internal wikilinks resolved after excluding code. Whitespace checks and a scan for the
withdrawn active deadline/outcome contracts passed. The lifecycle correction touched 49 notes,
including the new historical-case walkthrough; research annex bodies remained historical. No
agents, skills, execution support or behavioural tests were implemented or run, and no commit or
publication was made.

## Applied FPF method and size check on 2026-11-11

The previous requirement to name a precise unresolved distinction before every experiment was too
narrow for initial reconnaissance. RMP.1:4.0 and C.40 support starting from concrete material, an
executable operation and a kind of possible contribution, without predicting the discovery. The
charter, agent and skill contracts now distinguish that work from a question-led experiment.

F.0.2.MA assigns source contributions to their owning operations in [[fpf-framing]]. C.39 connects
those operations through actual material in [[research-lifecycle-cases]] Case 5: new corpus,
reconnaissance, question, experiment, interruption, resumed operation and a bounded answer. C.43
connects observations to the next choice. GOALS.7/A.15.10 require recovery and use of the question,
method and unfinished operation. A new question need not reopen an unrelated closed one.

All six skill contracts now include concrete applicable and defeating cases. Families C/D/H and
[[acceptance-criteria]] check legitimate exploration alongside unjustified continuation; E.23 ties
later improvements to behaviour, protected effects and comparable evidence. The new walkthrough
contains stipulated observations, not a successful run or empirical validation.

F.19 keeps operations explicit; A.6.3.CSC preserves the distinctions needed by compact operation
tables and links their fuller sources. [[authoring-budgets]] records the comparison, body sizes and
dated vendor evidence. Its 200-line body target is a local authoring choice, not a provider limit.
The existing local discovery check reports 15,040/16,000 characters: zero errors and one warning.
Its old fixed model differs from current provider guidance and needs reconciliation before adding
the six actual descriptions. Shared validators and unrelated skills were not changed.

This pass applies the methods to design documents and operation contracts. It creates no runtime
definitions, registrations, invocation policy, scripts or behavioural test runs. PBT and mutation
analysis remain excluded; go-kdl2/proj remain negative evidence. Existing uncommitted work is retained.

Validation of this application pass: 82 YAML frontmatters parsed, 82 unique note IDs with existing
IDs preserved, and 937 internal wikilinks resolved after excluding code. Whitespace checks passed.
The pass changed 33 design documents, including the new authoring-budget note; no runtime files
were changed. These checks establish document integrity, not agent effectiveness.
