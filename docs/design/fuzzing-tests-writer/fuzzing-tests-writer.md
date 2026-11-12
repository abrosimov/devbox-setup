---
note_id: "20261103150000"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: hub
note_role: artifact
artifact_kind: map-of-content
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Fuzzing Tests Writer", "FTW hub"]
tags: [fuzzing, design/hub]
status: authored-local-qualification
related: ["[[ontology]]", "[[fpf-framing]]", "[[next-iteration]]"]
---
# Fuzzing Tests Writer — design hub

This study specifies a fuzzing research capability for Claude Code and Codex in Go, Python and Rust.
The 2026-11-11 correction defines research per commit, experiment or dataset across multiple agent
sessions, with pauses, resumption and evidence-based closure. Failed `go-kdl2` and `proj` attempts
supply negative cases. The method now has authored provider definitions and six shared skills; their existence does not
establish that the agent works across sessions.
The applied FPF method also supports bounded reconnaissance of new corpora before a precise question
exists, then connects the resulting material to experiments and actual continuation after a pause.

## Reading route

Start with [[fpf-framing]] for method construction, [[stopping-algorithm]] for exploration and the
lifecycle, and [[research-lifecycle-cases]] for negative cases and the proposed new-corpus walkthrough.
[[methodology-review]] records the changed rules, evidence and limits; [[authoring-validation]]
separates authoring checks from remaining behavioural qualification. Use
[[agent-procedure]] for the procedure and [[eval-plan]] for its independent checks.
[[fpf-framing]] records why the selected FPF methods apply.

| Area | Entry | Result |
|---|---|---|
| Boundary and evidence | [[system-characterisation]] · [[research-corpus]] · [[ontology]] | Scope, provenance and qualified failure hypotheses H1–H7 |
| Method | [[fuzzing-charter]] · [[applicability-gate]] · [[oracle-ladder]] · [[input-shape-triage]] | Objective, suitability, justified oracle and input construction |
| Finishing and retention | [[stopping-algorithm]] · [[corpus-lifecycle]] · [[reporting-and-claim-hygiene]] | Persistent conclusions, justified transitions and useful replay inputs |
| Skills | [[skill-fuzzing-applicability]] · [[skill-fuzzing-campaign]] · [[skill-structured-input-generation]] · [[skill-go-fuzzing]] · [[skill-python-fuzzing]] · [[skill-rust-fuzzing]] | Six operation contracts and their authored skill entrypoints |
| Support | [[automation-scripts]] · [[reference-documents]] · [[repository-placement]] | Authored placement, conditional references and record support |
| Evaluation | [[eval-plan]] · [[eval-fixtures]] · [[acceptance-criteria]] | Behavioural cases and independent evidence |
| Next work | [[next-iteration]] · [[authoring-budgets]] | Size/loading evidence, qualification limits and separate invocation policy |
| Historical material | [[research-index]] | Frozen annexes R1–R10; not an executable policy |

## Governing rules

- Research retains its question, receiving use, versioned subject, evidence and effort across sessions.
  ACTIVE, PAUSED and CLOSED have different meanings; checkpoints explain how to resume or reopen.
- Reconnaissance needs concrete material, a feasible operation and a possible learning contribution;
  an exact hypothesis or proof of future usefulness is unnecessary. Question-led experiments name
  the distinction they can resolve. Both use proportionate effort and existing authority.
  A new session, commit, dataset hash, technique or remaining unknown is not sufficient by itself.
- A changed basis prompts a targeted check of affected conclusions, preserving prior closure and
  unaffected evidence. Local execution limits do not decide research completion.
- A new in-scope question can arise while an earlier question remains closed. Link its source
  material and prior effort; neither new labels nor new corpora erase history.
- Preserve useful coverage-expanding, structurally useful and regression inputs for reuse and replay.
  Deduplication must preserve their demonstrated value; retention is not permission to commit.
- Separate research state, experiment status and finding classification. No observed bug is not proof of no bugs;
  zero feature growth is not a saturation certificate.
- `go-kdl2` and `proj` supply negative evidence and counterexamples, not successful architectures.
- PBT and mutation analysis are excluded from deliverables, requirements and evaluations.
- Functional descriptions use ordinary provider discovery. Custom invocation conditions, routing,
  commands, hooks and scheduling remain deferred; no such automation was added.
- Provider definitions were authored against current official documentation; [[repository-placement]]
  records their different loading and permission choices. Shared methodology does not imply
  identical runtime behaviour.

## Decisions and readiness

FTW-D-001/002/006/009 retain applicability, six skills, local references and the charter.
[[FTW-D-003-thresholds-as-flags]] now fixes the persistent research lifecycle; [[FTW-D-008-pbt-out-of-scope]]
removes bridges and mutation analysis. [[FTW-D-004-evals-as-plugin]] and
[[FTW-D-005-techne-fuzz-command]] defer provider tooling and invocation respectively.
[[FTW-D-007-go-target-version]] retains the research target while separating source evidence from
future runtime verification. Open questions retain their IDs and identify whether they block later
authoring or are excluded; they are not a research backlog to exhaust.

Authoring is complete for both provider definitions and the six shared skills. See
[[authoring-validation]] for the exact local checks and their limits. Full cross-session lifecycle
qualification and Python/Rust runtime checks remain unperformed. Advanced invocation policy remains
a separate decision. Nothing has been deployed; the user will deploy `personal`.
