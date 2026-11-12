---
note_id: "20261103150003"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H2", "No stopping rule, no corpus switch"]
tags: [fuzzing, design/hypothesis, h2]
verdict: "user-reported failure; persistent lifecycle specified"
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]"]
addressed_by: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
tested_by: ["[[eval-family-D-stopping]]"]
related: ["[[ontology]]"]
---
# H2 — Research continues without a justified next result

**Status:** user-reported failure; cross-session remedy specified, not runtime-validated.

The user identifies endless exploration in failed `go-kdl2` and `proj` attempts. Individual runs
could stop while the same investigation restarted as another experiment, review or protocol.
The 2026-11-10 wall-clock/supervisor remedy addressed the wrong lifecycle and is withdrawn.

[[stopping-algorithm]] governs a persistent question and its commit/experiment/dataset basis.
A sufficient answer closes the question. An inconclusive result can close with limitations; a
pause needs a meaningful resume condition. Another experiment needs an attainable contribution
and proportionate effort. Reconnaissance can form a new question from concrete material; it need
not prove the discovery useful in advance. New sessions preserve conclusions, inputs and cost history.

[[research-lifecycle-cases]] separates historical evidence from proposed stopping points. Family D
checks continuity across sessions and selective reopening after relevant changes. Neither quiet
counters nor elapsed time prove saturation; neither new counters nor another technique force
continuation. The method still requires behavioural qualification after authoring.
