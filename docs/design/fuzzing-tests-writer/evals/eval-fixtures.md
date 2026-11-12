---
note_id: "20261103150502"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: fixtures
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval fixtures"]
tags: [fuzzing, design/eval, lang/go, lang/python, lang/rust]
related: ["[[eval-plan]]", "[[eval-tooling]]"]
target_path: "tests/fuzzing_agent_evals/fixtures/<lang>/"
---
# Eval fixtures

These are requirements for future fixtures, not implemented cases. Use small Go, Python and Rust
fixtures where language changes an operation. Each has a pinned subject, stated contract, expected
observations and independent verifier. A research fixture can include several sessions, commits,
experiment versions and dataset revisions. Its event sequence and available evidence are declared
before qualification. Preparation effort is recorded; no silent dependency download is assumed.

| Fixture or variation | Required distinction |
|---|---|
| Length-prefixed binary parser with CRC and encoder | Truncation, semantic round trip, repaired inputs and invalid raw-byte paths |
| Small text config parser with existing seeds | A useful corpus can suffice without grammar engineering |
| Strict expression parser with supplied grammar | Bounded generation; grammar-alternative coverage differs from code coverage |
| Finite enumeration already exhaustively tested | No useful fuzzing contribution; no unnecessary harness |
| Decoder wrapper with optional owned validation | Owned behaviour and contract determine applicability |
| Database-calling handler and separable decoder | Unavailable environment is not a product defect; any extraction remains authorised |
| Documented rejection or panic preconditions | Expected behaviour versus actual contract violation |
| Native/FFI decoder where supported | Instrumentation is active and the observed diagnostic is independently reproduced |
| Known failing seed or deliberately wrong harness assertion | Existing product finding versus false oracle; preserve original evidence |
| Denied required workspace operation | Environment failure without permission bypass |
| Useful input with no failure | Retention and replay do not require bug discovery |
| Unfamiliar corpus with optional-field combinations and an older closed truncation question | Reconnaissance can form a new in-scope question and retain useful inputs without reopening the unrelated answer; include a no-useful-difference variation |
| Saved checkpoint and a fresh session without previous chat | Question/aim, method, evidence, effort and unfinished operation are recovered and used to perform the next justified action |
| Temporarily unavailable dataset, then availability event | A meaningful pause remains inactive until its condition is observed; resumption checks the supplied dataset |
| Answered or inconclusive question with unused resources | Closure does not depend on consuming an allowance |
| Unrelated commit, reordered data, then a materially relevant change | Distinguish irrelevant identity changes from changed assumptions and affected claims |
| Repeated invalid experiment with unchanged cause | No uninformative retry or history reset under a new research identifier |
| Interrupted minimisation with saved original input | Execution interruption is separate from research state and retains a useful checkpoint |
| Misleading or flat engine logs | Observations do not independently imply saturation, safety or a defective harness |

A known defect has a deterministic correctness basis and expected symptom. Fixtures may contain
known bugs; mutation analysis, PBT fixtures and PBT workflows remain excluded. Abstracted incidents
from `go-kdl2` or `proj` retain source provenance and identify changes made for the fixture. Those
failed attempts do not supply a successful architecture to reproduce.

Reset each independent trial to its declared starting state. Within a multi-session trial, preserve
research artefacts across sessions and expose only the specified new evidence/change; resetting on
every session would erase the behaviour under test. Keep expected answers and verifier code outside
agent write access. Recorded traces test interpretation; actual build/replay and checkpoint-reuse
claims require executable cases. Run limits constrain execution separately from research closure.
