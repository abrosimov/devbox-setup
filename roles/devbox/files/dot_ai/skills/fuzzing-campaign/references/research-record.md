# Research record and return after a pause

Use an existing repository note or artefact convention. One concise Markdown record with links to
actual inputs and logs is enough; the fields below specify meaning, not a mandatory storage format.
Maintain the record when work produces evidence, changes the next operation or crosses a session
boundary. An ordinary brief pause need not create another report.

```text
Research: stable identity; question and use, or reconnaissance area and learning aim
Basis: relevant commit and dirty delta; experiment configuration; dataset/version/selection
Scope: permitted area and effects; exclusions; existing resource constraints
Current contribution: mode, material, operation, possible knowledge gain or sufficient answer
Oracle/observation: contract basis, expected rejection, instrumentation and unresolved assumptions
Evidence: linked inputs/logs; completed observations; prior conclusions and failed attempts
Effort: actual preparation, execution, replay, analysis and triage across attempts
Next work: operation, justification, practical limits and completion/failure evidence, or none
State: ACTIVE | PAUSED | CLOSED; reason and relevant date
Checkpoint: method, last completed action, unfinished operation and actual artefact locations
Return: observable resume condition, or changed premise needed to reconsider a closed answer
```

For an experiment attempt retain its identifier, command, environment/tool versions, actual status
and result. Record the selection used to make a claim; a mutable path such as `latest-corpus` does
not identify tested content. Include only dimensions that affect the observation or its reuse.
Preserve prior conclusions and their original scope when updating the current basis.

## Closure reasons

- `ANSWERED`: sufficient evidence for the declared question/use or reconnaissance contribution.
- `INCONCLUSIVE`: the evidence cannot resolve the question and no worthwhile available next
  experiment would resolve it under current conditions. Preserve the unresolved alternatives.
- `NO_JUSTIFIED_NEXT_STEP`: further work lacks relevant attainable value, available authority or
  a continuing use. Uncertainty remains visible; this is not a claim of success.
- `CANCELLED`: the user has ended the research.

Use `PAUSED` for a concrete observable condition that could enable useful continuation, such as
availability of a required dataset or an explicitly requested later return. A vague hope that
something may become useful is not a resumption condition. No automatic scheduling follows.

## Resume one actual operation

Recover the question/aim, method and unfinished action, then compare the conditions that action
relies on. For an interrupted reduction these include the original, last verified candidate,
symptom predicate, checked reductions and pending candidate. Confirm the pause condition and
perform the pending justified check; do not silently restart from the original input.

A documentation-only commit may leave the relevant behaviour unchanged. A decoder or oracle
change may invalidate dependent candidate judgements. Preserve the old observations with their
versions, inspect the affected dependency and requalify only what the next action relies on.
If essential material is missing, report which operation it prevents and what would restore it;
do not reconstruct a successful past run from an absent log.

## New question versus reopened answer

A new corpus may expose an optional-field path while an earlier truncation question remains
answered. Record a linked new question within existing scope; keep the truncation closure. If
the corpus instead contradicts the old truncation assumption, record that changed basis and reopen
the affected question. A new identity never erases shared history, effort or failed attempts.
