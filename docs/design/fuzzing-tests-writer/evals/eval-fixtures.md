---
note_id: "20261103150502"
created: 2026-11-03
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

One small repository per language, dependencies vendored (the eval sandbox limits network), each
with the same catalogue of entry points so cross-language cases are comparable.

| Entry point | Expected gate outcome | Planted defect |
|---|---|---|
| binary frame parser with length prefix and CRC, plus encoder | fuzz: greybox, round-trip oracle, CRC handled by flag or repair | out-of-range on a truncated length; encoder/decoder asymmetry on one field |
| text config parser (`KEY=VALUE`, lenient) | fuzz: seeds + bytes + dictionary, no grammar | `%` look-ahead at end of string |
| expression language with a strict parser and a grammar file in the repo | fuzz: grammar-generated seeds + engine | stack overflow at depth N |
| typed money arithmetic with documented laws | `out-of-scope: pbt-track`; no file written; reason recorded in the charter | commutativity broken for one currency (left for the PBT track; this agent must not hunt it) |
| `IsWeekend(time)` / three-enum pure function | exhaustive table test | none |
| HTTP handler calling a database client | do not fuzz as is; extract the pure validator | none |
| thin wrapper over the stdlib JSON decoder | do not fuzz the wrapper | none |
| `MustCompilePattern` / `CompilePattern` pair | fuzz the non-panicking variant only | none |
| LRU cache with `get/put/evict` | `out-of-scope: pbt-track` (model-based); a fuzz target over a byte-decoded op sequence only if the caller's charter names crash/invariant/resource objectives | eviction-order bug (the model-based track's case) |
| FFI/unsafe wrapper (Rust) or C-extension stub (Python) | greybox with ASan, touch every returned reference | one-byte over-read |
| existing fuzz target with a committed failing seed (Go `testdata/fuzz/<hash>`, Rust `crash-*`, Hypothesis printed blob) | reproduce and fix or report; never delete the seed | the original bug still present |
| pre-recorded campaign logs per engine (plateau, still productive, blocked, slow, unstable) | the matching decision token | n/a |

The recorded logs need no live engine and double as unit-test fixtures for `fuzz_campaign.py`
([[automation-scripts]]). Live-engine cases run with the `interactive` budget capped at 60 s inside
the eval; stop-decision logic is exercised on recorded logs, not on long runs.
