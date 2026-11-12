---
note_id: "20261103150510"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: tooling
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval tooling"]
tags: [fuzzing, design/eval]
grounded_in: ["[[10-eval-tooling-notes|R10]]"]
decided_by: ["[[FTW-D-004-evals-as-plugin]]"]
opens: ["[[FTW-OQ-009-plugin-eval-prerequisites]]"]
related: ["[[eval-plan]]", "[[automation-scripts]]"]
target_path: "tests/fuzzing_agent_evals/"
---
# Eval tooling

## Contract before provider implementation

This specifies evidence a future evaluator must produce. It does not author a runner, plugin, agent,
skill or CI job. Actual Claude Code and Codex packaging, permissions, saved-session facilities and
output schemas require current official documentation at authoring time
([[FTW-D-004-evals-as-plugin]]). Invocation/discovery/routing and trigger evaluation stay separate.

## Evaluation layers

1. **Document and package structure:** check metadata, links and actual provider schemas once files
   exist. Structural validity does not establish behaviour.
2. **Recorded-evidence cases:** supply controlled history, logs and contracts to test decisions and
   interpretation. Such cases do not establish actual builds, replay or persistence.
3. **Executable fixture cases:** observe generated files, independently build and replay the target,
   and capture real outcomes under ordinary local execution limits.
4. **Multi-session lifecycle cases:** initialise one research record, interrupt or finish a session,
   start another with the declared persisted context, and supply controlled commit/dataset or
   dependency changes. Inspect whether the agent resumes, closes or reopens for the right reason,
   preserves evidence and effort, and avoids uninformative repeated work.

A custom process supervisor is not the subject or required prerequisite of research-lifecycle
qualification. Runtime safeguards and workspace controls must be appropriate to executed fixtures;
they do not substitute for deciding whether another experiment is justified. A tool allowlist alone
does not demonstrate filesystem or network restrictions.

## Evidence ownership and persistence

Outside the evaluated agent's writable grading area, retain independent copies of initial subject
snapshots, supplied event history, checkpoint versions, experiment proposals/results, commands,
exits/signals, raw output, resource observations and workspace diffs. The agent's research record is
an output to verify, not a trusted source of its own execution or cost. Missing data remains unknown.

The evaluator distinguishes ACTIVE, PAUSED and CLOSED and records the basis of each transition.
A CLOSED record names ANSWERED, INCONCLUSIVE, NO_JUSTIFIED_NEXT_STEP or CANCELLED. Its conclusion,
limitations and evidence remain visible when later reopened. A PAUSED record names an observable
resume condition and saved checkpoint. Experiment status and process status are separate fields.

Test recovery without private chat history. Reuse repository-native materials; a new storage service
or provider-specific memory facility is not implied. The harness must not silently reset files or
costs between sessions of one trial. Independent trials remain isolated and start from the declared
baseline. A fresh identifier must not conceal a continuation of previously charged work.

For changed commits or datasets, the evaluator knows which facts or assumptions changed and which
remain applicable. It checks that the agent assesses the relevant delta rather than using hash
inequality as a blanket invalidation rule. If order matters to the experiment, reordering is relevant;
if it does not, the result can be reused with that qualification recorded.

Independent execution uses actual language build/load and target paths. `go vet`, import success,
unrelated tests and agent-authored status files cannot replace this evidence. Known failing seeds
remain identified rather than deleted to obtain a green result. Holdout expectations and verifiers
remain outside agent write access. Grading does not retrospectively perform missing research work.

## Provider qualification

Run equivalent cases for Claude Code and Codex using explicit adapter mappings. Record differences
in skill availability, persisted context, permissions and observation interfaces that affect
comparability. Parsing configuration is not a live model evaluation; a single session cannot qualify
multi-session behaviour. Model choices, concrete adapters, repetitions and expenditure are deferred
to authorised authoring and qualification. See [[eval-plan]] and [[acceptance-criteria]].
