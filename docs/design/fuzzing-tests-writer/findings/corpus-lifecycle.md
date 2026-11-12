---
note_id: "20261103150205"
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
aliases: ["Corpus lifecycle"]
tags: [fuzzing, design/finding, h2, h3, h5]
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[03-structure-aware-generation|R3]]", "[[07-lang-go|R7]]", "[[09-lang-rust|R9]]", "[[08-lang-python|R8]]"]
realised_by: ["[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-D-stopping]]"]
related: ["[[input-shape-triage]]", "[[stopping-algorithm]]"]
---
# Corpus lifecycle

Preserve inputs that are useful for later search or replay: coverage-expanding inputs, valid
structured examples, boundary cases and failure reproducers. A useful search input is a valid
reason to retain a replay asset. The failed `go-kdl2` frontier/replay policy is not the model for
this agent. Storage follows the target repository's existing conventions; this method does not
commission a new registry, remote store or automatic Git publication.

## Before, during and after research episodes

- Inventory existing seed, generated and failure corpora without deleting user-owned material.
  Record their paths, format, provenance and relevant harness/decoder versions.
- Select small representative valid examples and intentional invalid cases. Replay them through
  the actual harness and record expected acceptance, rejection or known failure.
- Preserve useful new inputs while they are available. An ephemeral engine cache alone is not a
  durable replay record; copy selected inputs to the repository's established corpus location or
  another already-authorised durable location.
- Separate failing inputs from ordinary passing replay where the runner requires it, retaining
  an explicit reproduction command. Do not delete a known failure to make a run appear green.
- Account for collection, copying, replay and reduction in the experiment effort and persistent
  research history. A paused or closed question keeps its useful replay assets.
- On a later commit or dataset, check the target/decoder assumptions that make an input meaningful;
  preserve previous observations with their versions. Changed scope does not justify deleting
  inputs or repeating every old experiment.
- Do not add scheduled pruning, cross-worker storage or a new infrastructure lifecycle.

## New corpora and directions

Treat an incoming corpus as material to examine. Preserve its origin, selection and version, then
inspect/replay a bounded representative sample through a compatible harness. Compare meaningful
behaviour with existing inputs: acceptance, reached paths, structural cases or a failure symptom.
Different bytes or a new dataset hash alone do not establish new behaviour.

The first pass may discover which question is worth asking. It needs a feasible observation and a
possible knowledge contribution, not proof of the corpus's eventual value. Return the observations
and useful inputs to [[skill-fuzzing-campaign]], which chooses another examination, a new in-scope
question, reuse or closure. A different question does not require reopening an answered one;
new evidence changes an old conclusion only where its assumptions are affected.

Keep useful intermediate and non-crashing inputs available for replay. Record why a seed is useful
or which limited examination remains promising; do not describe an unperformed replay as verified.
Retention does not mandate further experiments. Corpus reduction must preserve the behaviour and
future use for which an input was kept, including structured examples that share current coverage.

## Reduction and preservation

Deduplicate identical inputs cheaply. More aggressive corpus reduction is optional and bounded:
record the criterion and retain the behaviour that made an input useful. Coverage equivalence
alone may lose a valuable structured example or a failure symptom. Keep the original until the
replacement has been checked; if time is insufficient, preserve it unchanged and report that.

For failure reduction, the predicate means **the same relevant failure**, not merely any non-zero
exit. Classify candidate replay as `PASS` (that failure absent), `FAIL` (same failure present), or
`UNRESOLVED` (environmental failure, ambiguity or an interrupted check). An unresolved check is
not evidence that reduction succeeded. The [Fuzzing Book reduction chapter](https://www.fuzzingbook.org/html/Reducer.html)
supports reducing failure-inducing inputs while testing the failure condition; the precise
symptom predicate is a local harness obligation.

On interruption, retain the original, last verified candidate, symptom predicate, checked
reductions and unfinished check. On return, recover that operation and inspect changed target,
decoder or oracle assumptions before continuing it. A new session does not require reducing again
from the original. A changed predicate can invalidate candidate judgements without invalidating the
historical observations or authorising deletion of their inputs.

## Replay handover

| Asset | Required record |
|---|---|
| Useful passing or intentionally rejected seed | Durable path, target, expected behaviour and verified replay command |
| Confirmed failing input | Original and reduced paths where available, symptom, environment and independent replay evidence |
| Unconfirmed failure | Preserved bytes and raw log; the missing confirmation explicitly stated |
| Byte-decoded structured input | Raw engine input plus decoder/version information; a readable decoded example where feasible |

Go, Python and Rust use different corpus formats and runners; see the `language-facts-*` notes.
Verify the actual repository runner, rather than assuming that a corpus directory is replayed by
ordinary tests. Report local files saved, unchanged and unverified. A Git commit or publication
requires separate authority; `corpus retained` must never be reported as `corpus committed`.
