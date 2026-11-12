---
note_id: "20261104100004"
created: 2026-11-04
modified: 2026-11-10
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: reference
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["PBT agent prompts", "Hypothesis command and agentic-pbt"]
tags: [fuzzing, design/framing]
grounded_in: ["[[08-lang-python|R8]]"]
related: ["[[fuzzing-vs-pbt-boundary]]", "[[oracle-ladder]]", "[[reporting-and-claim-hygiene]]"]
opens: ["[[FTW-OQ-011-agentic-pbt-validity]]"]
---
# Historical PBT prompt references — excluded from this methodology

This note previously imported rules and unverified statistics from Hypothesis' command prompt and
`agentic-pbt`. That transfer is withdrawn by [[FTW-D-008-pbt-out-of-scope]]. PBT and mutation analysis
are outside the current agent, skills and evaluations; this note schedules no follow-up track.

The historical references remain discoverable in [[08-lang-python|R8]] §3.5 and
[[FTW-OQ-011-agentic-pbt-validity]]. Neither their properties nor validity percentages are evidence
that this fuzzing agent works. Current oracle, triage and reporting rules are justified independently
in [[oracle-ladder]], [[reporting-and-claim-hygiene]] and [[methodology-review]].
