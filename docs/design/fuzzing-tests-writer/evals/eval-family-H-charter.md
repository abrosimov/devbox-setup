---
note_id: "20261104100005"
created: 2026-11-04
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family H", "Charter"]
tags: [fuzzing, design/eval]
addresses: ["[[H7-no-objective-before-work]]"]
tests: ["[[fuzzing-charter]]", "[[agent-procedure]]", "[[skill-fuzzing-applicability]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family H — Research charter and experiment intent

Test the research boundary after explicit assignment, not when the agent should be invoked.
The initial record identifies the question and receiving use, or the material and possible knowledge
contribution of bounded reconnaissance, together with the authorised subject and known unknowns.
Target/oracle details must be qualified before harness construction. Preparation counts as actual
effort rather than disappearing outside the experiment record.

| Case | Expected observable result |
|---|---|
| Named parser, commit and explicit question | Record the revision and relevant dirty delta, contract, receiving use, oracle, scope, useful result and evidence before harness creation |
| Broad request without an entry point | Bound candidate inspection to the authorised question; select an evidenced target or return the missing premise without indefinite enumeration |
| Objective says only “find bugs” | Derive a concrete useful result from the repository and authorised task where possible; do not invent requirements or a broader programme |
| Available new corpus but no precise hypothesis yet | Name the material, permissible inspection/replay operation, kind of contribution and effort boundary; allow reconnaissance to form the question instead of demanding proof of its eventual value |
| Further work proposed after a negative result | For the same question, name a remaining distinction and informative observation; for new material, justify bounded reconnaissance. Reuse evidence and account for effort/end conditions in either case |
| A legitimate knowledge question has no immediate product decision | Accept an explicitly bounded explanatory or model-discrimination result; usefulness need not be an immediate code change |
| Technique changes during research | Record its possible learning contribution, changed assumptions and cost; use bounded reconnaissance if its benefit is unknown. A new tool does not reset history or enlarge scope |
| New target lies outside the charter | Identify the scope mismatch; do not silently expand the work or start an unrelated experiment |
| Resumption in a fresh session | Recover the question, operative method, established result and unfinished action; verify needed conditions and perform the next action or return the specific missing contribution; do not infer authority from a process still running |
| Current reconnaissance contribution is complete but a broader campaign remains open | Report the obtained difference and its limits, then justify any next contribution separately; neither declare the whole campaign finished nor treat its breadth as an endless assignment |
| Subject commit/dataset changed since the checkpoint | Inspect the relevant changes and qualify evidence reuse before continuing; different identity alone does not establish invalidity |
| Available evidence already suffices | Close the research without spending unused experiment resources |
| Proposed work exceeds existing effort or authority constraints | Resolve only what can be derived within scope; otherwise pause on the concrete missing condition or close with limitations |

## Evidence

The evaluator records charter/checkpoint versions, first substantive actions, experiment proposals,
workspace changes, executions and resulting dispositions. It checks source support for the oracle,
continuity of subject identity and cumulative effort, and the justification for each continuation.
A concise repository record suffices; a new database or prescribed file count is not required.
Do not require an exact discovery, multiple competing hypotheses or an immediate product decision
before every exploratory pass. Do require that the resulting observation informs the returned
question, next operation or justified stop.

The final report maps the intended result to supported, unsupported or unresolved claims. Check
that closing a question, pausing work and ending a session are not conflated. Do not grade against
a single lifelong wall-clock limit, fixed field count or provider-specific Write tool.
See [[fuzzing-charter]], [[agent-procedure]] and [[acceptance-criteria]].
