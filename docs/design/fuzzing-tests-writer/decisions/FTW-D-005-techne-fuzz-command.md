---
note_id: "202611031506005"
modified: 2026-11-10
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-005"]
tags: [fuzzing, design/decision]
status: deferred
supersedes: []
superseded_by: []
related: ["[[agent-procedure]]", "[[repository-placement]]"]
---
# FTW-D-005: Invocation and command selection are deferred

*Amended in draft on 2026-11-10 by the methodology revision ([[methodology-review]]).*

The user explicitly deferred conditions for calling the agent and skills. The former `/techne-fuzz`
command decision is therefore withdrawn from this iteration. No command, automatic delegation rule,
description-trigger policy, routing change or trigger evaluation is selected here.

The method still specifies the information an operation requires after invocation, and how it ends.
Those are execution preconditions, not invocation conditions.

**Basis:** user direction; [[system-characterisation]] and [[next-iteration]]. Naming and routing
alternatives can be assessed when that separate decision is made. No model choice follows from this
note. Its retained filename and ID preserve old links without leaving the old command normative.
