---
note_id: "20261103150505"
created: 2026-11-03
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
aliases: ["Eval family C", "Structure and seeds"]
tags: [fuzzing, design/eval]
addresses: ["[[H3-random-seeds-for-structured-input]]"]
tests: ["[[input-shape-triage]]", "[[fuzzing-vs-pbt-boundary]]", "[[skill-structured-input-generation]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Eval family C — Structure and seeds

Evaluate whether input construction reaches the intended behaviour and useful inputs survive
for replay across sessions. Initial reconnaissance may discover the distinction worth investigating;
it needs available material, a feasible operation and proportionate effort, not a predicted discovery.
No automatic escalation ladder is tested.

| Case | Expected observable result |
|---|---|
| Simple text parser and existing fixtures | Reuse meaningful seeds and token dictionary where useful; do not require a grammar |
| Strict parser with a supplied grammar | Construct bounded inputs; exercise relevant alternatives and validate parser reachability separately |
| Length/CRC framed input | Use valid fixtures or constructive repair for deep paths while retaining an invalid/raw-byte path; do not silently change the product's checks |
| Mostly rejected mutations at a magic header | Interpret the observed barrier, justify a proportionate in-scope seed/dictionary experiment if it can resolve that obstruction; do not infer a broken harness from rejection rate alone |
| Compressed binary data | Reuse real compressed seeds; do not manufacture an irrelevant textual grammar |
| Large existing corpus with useful coverage inputs | Preserve provenance and known useful behaviour during deduplication; corpus size alone does not justify deletion |
| Newly useful input with no failure | Preserve it for replay using repository conventions; a crash is not a prerequisite for retention |
| New corpus contains unfamiliar permitted constructs but no precise hypothesis | Perform a bounded inspection/replay pass using a qualified target; retain observed behaviour and use it to formulate a question, return a sufficient result or stop with a stated limitation |
| Inputs differ in bytes but exhibit the same observed behaviour | Do not claim new behavioural coverage from encoding diversity alone; retain useful cases and state what the observation can distinguish |
| Reconnaissance exposes a useful unexpected path without a crash | Preserve the input and reproduction conditions, and consider the evidenced next question within existing scope; do not reject the result because it was not predicted |
| Grammar-generated input reduces to a different symptom | Keep the original; classify the candidate as unresolved or a different failure rather than successful minimisation |
| Execution is interrupted while constructing or minimising inputs | Preserve original inputs, partial evidence and checkpoint; distinguish interruption from research closure and justify any resumption |

## Evidence

Inspect actual seed files and their provenance, execute replay independently, and compare the
relevant behaviour before and after corpus reduction. Do not require an arbitrary minimum seed
count. Grammar-alternative coverage, code coverage and accepted-input counts are distinct
observations. Byte minimisation is not proof of structural or global minimality.
Use the proposed connected walkthrough in [[research-lifecycle-cases]] to check that the retained
input actually supplies the next experiment and remains replayable after the question closes.

Apply the Fuzzing Book's constructive generation and same-symptom reduction ideas through
[[input-shape-triage]] and [[corpus-lifecycle]]. PBT bridges and PBT generator authoring are excluded.
