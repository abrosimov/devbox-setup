---
note_id: "202611031506004"
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
aliases: ["FTW-D-004"]
tags: [fuzzing, design/decision]
status: deferred
supersedes: []
superseded_by: []
related: ["[[eval-tooling]]", "[[eval-plan]]", "[[eval-fixtures]]"]
---
# FTW-D-004: Provider-independent behavioural checks; concrete harness deferred

*Amended in draft on 2026-11-10 by the methodology revision ([[methodology-review]]).*

Specify common cases, independent grading and comparable budgets in [[eval-plan]], [[eval-fixtures]]
and [[acceptance-criteria]]. Choose concrete Claude Code and Codex execution adapters only after
checking each provider's current official documentation during authoring.

This withdraws the earlier decision to make `claude plugin eval` the sole implementation and to add
trigger evals now. Claude plugin evaluation remains a possible facility, subject to actual isolation,
permissions and baseline behaviour. It does not establish equivalent Codex behaviour.

**Basis:** SYSE.46; user requires both providers and defers invocation. [[eval-tooling]] separates
runtime evidence from model-produced claims. A model-written exit-code file is not independent proof.

**Alternatives:** tying the method to one vendor prevents a fair cross-provider check; using only
configuration parsers proves loading at most. Later adapters must preserve case meaning and expose
independent logs and effects. Invocation evaluation waits for its separate policy.
