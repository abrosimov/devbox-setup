---
note_id: "20261103150409"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: scripts
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Automation scripts", "fuzz_campaign.py", "fuzz_corpus.py"]
tags: [fuzzing, design/component]
addresses: ["[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]", "[[H6-crash-counting-reports]]"]
realises: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-D-stopping]]"]
decided_by: ["[[FTW-D-003-thresholds-as-flags]]"]
target_path: "roles/devbox/files/dot_claude/bin/"
related: ["[[skill-fuzzing-campaign]]", "[[eval-tooling]]"]
---
# Automation support — research checkpoints, evidence and dispositions

This note specifies support operations. The authored campaign skill implements their instructions
through ordinary repository tools and `references/research-record.md`; no new script or service was
added. The earlier `fuzz_campaign.py` and `fuzz_corpus.py` names identify responsibilities only.
[[FTW-D-003-thresholds-as-flags]] and [[stopping-algorithm]] govern research continuation and closure,
not a process-supervisor requirement. Process limits remain ordinary experiment execution controls.

## Minimal persistent record

Inputs are the authorised scope, research identity, question/use or reconnaissance material and aim, subject
snapshot, experiment definition, existing evidence and repository conventions. Preserve:

- Research identity/revision; repository commit and relevant dirty delta, experiment version,
  dataset version/hash and selection as applicable; assumptions and provenance.
- Current `ACTIVE`, `PAUSED` or `CLOSED` state and dated reason. A pause includes its checkpoint
  and observable resume condition; closure includes the conclusion, limitations and reason.
- Experiment/attempt identities and mode: reconnaissance carries material, operation and possible
  knowledge contribution; a question-led experiment carries its distinguishing observations. Both
  retain method, effort/resource limits, observed status/result and actual effort.
- Evidence pointers, useful corpus/reproducer paths, supported conclusions and unresolved issues;
  classification and compatibility are kept distinct from the underlying raw artefacts.
- Resumption/reopening evidence, affected claims and retained earlier dispositions. No new session,
  attempt or label overwrites the cumulative effort and failed-attempt record.

Use a concise existing repository record and artefact links. No database, background service,
new universal file format or process watchdog is required by this method. If an implementation
cannot durably preserve essential evidence, return that specific limitation before relying on
cross-session continuation; do not invent continuity from an absent checkpoint.

## Support operations

| Operation | Required input | Return and failure meaning |
|---|---|---|
| Load checkpoint | identity and available record | question/aim, method, completed and unfinished operation, evidence and disposition; missing/corrupt context is explicit |
| Bind subject | commit/dirty delta, experiment definition or dataset identity/selection | reproducible snapshot and comparison scope; ambiguous input version blocks the affected inference |
| Record experiment | justification, method, limits and attempt observations | planned/running/interrupted/completed/invalid/blocked status with evidence and cost; a process exit is not a research conclusion |
| Check compatibility | old and new snapshots, assumptions, toolchain and oracle | affected claims and reusable evidence; a version change alone cannot invalidate or repeat everything |
| Record disposition | evidence-backed decision under [[stopping-algorithm]] | active next experiment, pause with condition/checkpoint, or closure with reason and limitations |
| Resume/reopen | observed resume condition or material new evidence | linked revision retaining previous conclusion and effort; unsupported continuation is rejected with its missing basis |
| Link a new question | reconnaissance result, actual inputs and existing scope | question with its own contribution and links to prior evidence/effort; earlier questions need not reopen |
| Preserve corpus | useful inputs, provenance, encoding and repository conventions | retained replay paths and observed/unknown replay status; no silent deletion or automatic commit |

Updates must preserve prior evidence and disposition history. Recovery must expose uncertain
writes or missing artefacts rather than recreating a successful result. The same experiment
replayed after interruption gets another attempt record; it is not counted as an independent new
experiment merely because the agent session changed.

## Corpus and finding operations

Retain useful coverage-expanding inputs, valid-structure seeds and regression examples for reuse
and replay. Deduplication/reduction can replace an input only with evidence preserving its known
useful behaviour or the same failure symptom. Keep the original when equivalence is unconfirmed.
Preserving an input is distinct from checking it against a changed code or dataset snapshot.

Preparation, qualification, reproduction and reduction consume the experiment's stated resources
and remain in cumulative research accounting. A local timeout records an interrupted operation;
it does not prove a product hang or close the research. Unconfirmed candidates can be preserved
at a pause or closure without forcing further experiments. Report product defects and correct only
authored harness errors within scope. PBT and mutation-analysis operations are excluded.

## Remaining independent validation

[[eval-tooling]] must observe the meaning and effects of these operations independently of their
success messages. Cases include recovery after interruption, restoring useful inputs, unchanged
and changed snapshots, a false oracle, a paused condition still unmet, a closed question without
new evidence, and justified targeted reopening. Check that the receiving agent uses the recovered
record rather than starting over and that a renamed session does not lose prior effort.

Runtime command caps may be tested where an implementation uses them, but process termination
is not the criterion for research closure. [[authoring-validation]] records the actual local checks;
full lifecycle qualification remains incomplete. [[repository-placement]] records the authored paths
and provider facilities. No custom trigger policy or scheduler was added.
