---
note_id: "20261104100008"
created: 2026-11-04
modified: 2026-11-10
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-008"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[fuzzing-vs-pbt-boundary]]", "[[applicability-gate]]", "[[pbt-agent-prompts]]", "[[FTW-D-002-six-skills]]"]
---
# FTW-D-008: PBT and mutation analysis are excluded

*Amended in draft on 2026-11-10 by the methodology revision ([[methodology-review]]).*

This capability authors fuzz targets, useful seed corpora, bounded campaigns and reports. It does
not create or run PBT workflows, strategies, state machines or PBT bridges. Mutation analysis is
also excluded from requirements, fixtures, acceptance gates and a proposed future workstream.
This explicitly withdraws the earlier exception for existing PBT artefacts and hybrid bridges.

**Basis:** user's explicit scope correction; [[fuzzing-vs-pbt-boundary]]. Historical research that
mentions these techniques remains historical, not a source of current obligations.

A contract-backed assertion inside a fuzz target is permitted. Ordinary mutation of input bytes by
a fuzzing engine is permitted; this is not mutation analysis of product code. The distinction is
operational, not a ban on invariants or the word “mutation”. Unsupported requests return their
scope reason without invoking or designing a separate PBT agent.

**Consequences:** [[pbt-agent-prompts]] is excluded provenance only. FTW-OQ-006 and FTW-OQ-011 are
closed for this scope. Scope changes require the user; no capability-development pattern reopens them.
