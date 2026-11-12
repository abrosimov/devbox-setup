---
note_id: "20261104100009"
created: 2026-11-04
modified: 2026-11-11
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-009"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[fuzzing-charter]]", "[[agent-procedure]]", "[[eval-family-H-charter]]"]
---
# FTW-D-009: Persistent research charter before harness construction

*Amended in draft on 2026-11-11 to distinguish research from agent sessions.*

Record the known research question/use, or reconnaissance material and learning aim, together with
the subject basis and scope before investigation. A precise hypothesis can emerge from reconnaissance.
Resolve the target/oracle details needed for a meaningful harness before writing it. The charter
can initially name a bounded candidate area; it must not hide unbounded exploration or invent facts.
[[fuzzing-charter]] supplies the compact record.

On subsequent invocations recover that record, completed work and current disposition. Refine only
what new evidence affects. A new session is not a new charter or an excuse to repeat the research.
State the next experiment's expected contribution, practical limits and completion evidence when
it is justified; no universal wall-clock allowance spans the research's pauses.

**Basis:** user correction; SYSE.47 procedure and persistent evidence under [[stopping-algorithm]].
The result is checked against the question and its receiving use, not merely against a process exit.
Family H checks the initial ordering and cross-session continuity. The charter records the task;
it is not an additional research programme or a trigger policy.
