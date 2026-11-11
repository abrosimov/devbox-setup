---
note_id: "202611031506001"
created: 2026-11-03
modified: 2026-11-11
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-001"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[applicability-gate]]", "[[agent-procedure]]", "[[eval-family-A-gate]]"]
---
# FTW-D-001: Applicability before harness construction

*Amended in draft on 2026-11-11 for persistent research ([[methodology-review]]).*

Keep applicability as a reusable operation in [[skill-fuzzing-applicability]], applied before a
harness is written. Check the named entry point, available contract, observable oracle, reproducible
execution and proportionate experiment effort. Return a justified fuzzing plan or a reason to decline;
unsupported work is not silently converted into PBT or unit-test authoring.

Recover any existing research record before assessment; revisit only affected assumptions. The
charter is settled before harness construction ([[FTW-D-009-charter-before-work]]). This is procedure order after invocation, not a
rule for triggering or routing to the agent.

**Basis:** user scope; [[applicability-gate]]; [[H1-no-applicability-gate]]. General source guidance
supports suitability checks but does not prove H1 was the dominant cause of these failed attempts.

**Alternatives:** a gate only in the agent prompt would not be reusable; a campaign before checking
suitability spends resources without a stated purpose. Family A checks substantive decisions,
not merely a matching token. Revisit the operation only when supported cases defeat its rules.
