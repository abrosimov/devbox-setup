---
note_id: "202611031506003"
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-003"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[stopping-algorithm]]", "[[automation-scripts]]", "[[eval-family-D-stopping]]"]
---
# FTW-D-003: Stopping thresholds are marked sourced or proposed and exposed as script flags

## Decision

Every number in [[stopping-algorithm]] carries ✓ (sourced) or ◇ (proposed default). The ◇ values (plateau window, execution floor, sanity-gate time, discoverability criterion, triage budget, rejection trigger) are command-line flags of `fuzz_campaign.py`, and family D eval cases are written so that a wrong default flips a decision.

## Context

No primary source gives a numeric stopping threshold (R2 §4, R6 §4.2); inventing one as if cited would violate `C.11.DUA` and make the evals unable to tell a bad default from a bad rule.

## Alternatives considered

(a) Hard-code thresholds in the skill prose — untestable, and the model would restate them as facts. (b) Leave the decision to the model per run — reproduces H2.

## Consequences

The script, not the model, parses engine output and emits the decision token; the skill explains the token; tuning happens on non-holdout cases only ([[acceptance-criteria]]).

## Reopen when

an engine starts exposing per-feature incidence counts (making Good–Turing computable natively), or the evals show a ◇ default never changes a decision (then it can be fixed in prose).
