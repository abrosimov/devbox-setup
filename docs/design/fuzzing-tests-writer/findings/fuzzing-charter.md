---
note_id: "20261104100002"
created: 2026-11-04
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
aliases: ["Fuzzing charter", "Objective and verifiable result"]
tags: [fuzzing, design/finding, h7, h1, h2]
addresses: ["[[H7-no-objective-before-work]]", "[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[agent-procedure]]"]
tested_by: ["[[eval-family-H-charter]]"]
decided_by: ["[[FTW-D-009-charter-before-work]]"]
related: ["[[applicability-gate]]", "[[stopping-algorithm]]", "[[reporting-and-claim-hygiene]]"]
---
# Fuzzing charter — persistent question and checkable result

The charter belongs to the research, not to an individual agent session. It identifies the question
or reconnaissance aim, subject snapshot, sufficient current contribution and authorised effects. It survives pauses,
agent restarts and experiments. Record the known boundary before investigation; refine unknown
entry-point/oracle details with evidence before writing a harness.
Initial reconnaissance may start with concrete material and a bounded learning aim; it does not
require a precise hypothesis or proof that an unknown result will be useful. Record the question
that emerges without pretending it was specified before the observations.

## Required content

| Field | Content |
|---|---|
| Identity and use | Stable research identity; formulated question or reconnaissance material/area and kind of knowledge sought; intended use where known |
| Subject and version | Relevant commit and dirty delta, experiment definition/configuration, or dataset version/content and selection; state which observations depend on which snapshot |
| Scope and authority | Candidate area or entry points, permitted effects, exclusions and any existing resource constraints |
| Sufficient result | For reconnaissance: inspect the declared material through the chosen operation and return distinctions, a question or an explicit limit. For a formulated question: observations sufficient for its use. Neither requires finding a bug |
| Oracle and assumptions | Contract-backed check, expected rejection and independent basis; record unresolved details honestly |
| Existing evidence | Prior attempts and conclusions, useful inputs and replay context; remaining consequential uncertainty |
| Next work, if justified | Reconnaissance or question-led experiment; material, operation, attainable contribution, practical cost/effort bound and completion/failure evidence; reuse existing evidence |
| Lifecycle | ACTIVE, PAUSED or CLOSED, reason, checkpoint and resume/reopening basis under [[stopping-algorithm]] |

## Rules

1. Do not begin with unbounded repository exploration. A broad assignment can first define a bounded
   candidate area and a useful applicability result; no invented target or adversary is required.
2. Changes to an oracle or method are recorded with their evidence and implications for previous
   results. They do not silently expand scope or reset effort already spent.
3. Each next experiment needs a justified contribution. A source catalogue or technique ladder is
   not a work queue. Research may finish with a supported answer or explicit unresolved limitations.
   Reconnaissance justifies a kind of possible contribution; it need not predict the discovery.
4. Pauses save enough state for a later run. A changed commit/dataset prompts an impact check, not a
   full restart or automatic reopening.
5. Preserve useful inputs for replay. Local retention does not authorise commits/publication.
   Product fixes remain separate; correcting the authored harness can be in scope.
6. A session report states both what this episode did and the resulting research state. It does not
   infer research completion from process exit or a technical limit.

## Compact record

```text
Research: <stable identity; question/use or reconnaissance area and learning aim>
Basis: <relevant commit/delta, experiment definition or dataset snapshot>
Scope: <authorised area/effects; exclusions>
Current contribution: <material/operation/end result for reconnaissance, or sufficient answer>
Evidence so far: <links; assumptions; retained inputs; effort/attempts>
Unresolved: <question or unexplored material within scope, or none>
Next work: <mode; material; operation; possible contribution; limit; end evidence, or none>
State: <ACTIVE | PAUSED | CLOSED; reason>
Checkpoint: <question and method; completed/unfinished operation; resume/reopening basis>
```

Use an existing note or repository record where possible; this is a content contract, not a new
storage format. Invocation conditions are deferred. [[eval-family-H-charter]] checks identity,
ordering, scope continuity and reuse across sessions.
