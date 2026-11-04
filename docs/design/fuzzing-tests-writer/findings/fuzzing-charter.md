---
note_id: "20261104100002"
created: 2026-11-04
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Fuzzing charter", "Objective and verifiable result"]
tags: [fuzzing, design/finding, h7, h1, h2]
addresses: ["[[H7-no-objective-before-work]]", "[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[agent-procedure]]"]
tested_by: ["[[eval-family-H-charter]]"]
decided_by: ["[[FTW-D-009-charter-before-work]]"]
related: ["[[applicability-gate]]", "[[stopping-algorithm]]", "[[reporting-and-claim-hygiene]]"]
---
# Fuzzing charter — objective and verifiable result before any work

The agent fixes, in writing, what the fuzzing is for and what result can be checked, **before** it
writes a harness or runs an engine. The charter is the contract the campaign report is compared
against; a campaign without a charter is not started.

## Charter fields

| Field | Content | Source of the rule |
|---|---|---|
| Entry point(s) | package/module, function, input kind (bytes, text, typed, sequence) | R1 §5.1 precondition 7 (one format or API family per target) |
| Objective | which bug classes are being hunted and why they are plausible here: panics/OOB in a format reader, unbounded allocation from length fields, infinite loops, round-trip inconsistency, UB across `unsafe`/FFI | R7 §3.6, R9 §3.7, R8 §3.2 (bug-class evidence) |
| Oracle and contract | the rung of the [[oracle-ladder]] used; "never panics, returns error on invalid input" or "may panic on precondition X" | R1 §5.1 preconditions 4–5 |
| Out of scope | what is deliberately not covered: entry points sent to the PBT track ([[fuzzing-vs-pbt-boundary]]), I/O layers, already-fuzzed dependencies | [[applicability-gate]] |
| Verifiable result | the observable artefacts that count as done: harness file(s) at the ecosystem path; seed corpus committed and passing as unit tests; a campaign of budget class *X* with its `campaign.json` and decision token; buckets with reproducers or an explicit "no findings at budget *X*, residual risk not quantified"; coverage of the named functions reached | R2 §5.1, §5.3; R6 §5.3 |
| Budget class and stop rule | `interactive` / `smoke` / `batch` / `deep`, the cap passed to the engine, and the escalation rungs allowed | [[stopping-algorithm]] |
| Success and failure criteria | what makes the campaign a success (bugs found *or* saturation reached with coverage evidence) and what makes it a failure of the work (blocked harness, discoverability failure, oracle too weak) | R2 §5.1 steps 2–3 |

## Rules

1. The charter is written after the gate ([[applicability-gate]]) says the entry point is a fuzzing
   task, and before any harness file exists; in the trace, the charter precedes the first `Write` of
   a harness ([[eval-family-H-charter]]).
2. The charter is short (≤ 25 lines) and lives next to the work: a section at the top of the
   campaign report draft, or a `FUZZING.md` next to the harness when the repository has none.
3. Changing the charter mid-campaign is allowed only through the escalation ladder
   ([[stopping-algorithm]] step 8); the change is recorded, and a harness change starts a new
   (target, corpus) ledger entry with its own charter line.
4. The final report ([[reporting-and-claim-hygiene]]) opens by restating the charter and closes by
   stating, item by item, whether the verifiable result was met.
5. A charter whose objective cannot name a plausible bug class, or whose oracle is "does not crash"
   on a memory-safe typed API, is returned to the gate: the entry point is not a fuzzing task.

## Template

```text
Charter — <package>::<entry point>   (date, commit)
Objective: hunt <bug classes> because <evidence: input kind, past issues, unsafe/FFI, length fields>
Oracle: <ladder rung>; contract: <never panics / may panic on X>
Out of scope: <PBT-track entry points; I/O layer; upstream-fuzzed deps>
Verifiable result: harness at <path>; seeds at <path> passing `<test cmd>`; campaign <class> with
  campaign.json + decision token; buckets with reproducers or "no findings at <class>"; coverage of
  <functions> reached
Budget: <class>, cap <flag>; escalation allowed: <rungs>
Success: <…>   Failure of the work: <blocked harness | discoverability < 50 % | oracle returned to gate>
```
