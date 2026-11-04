---
note_id: "20261103150507"
created: 2026-11-03
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family E", "Conventions and compile"]
tags: [fuzzing, design/eval]
addresses: ["[[H5-harness-conventions]]"]
tests: ["[[language-facts-go]]", "[[language-facts-python]]", "[[language-facts-rust]]", "[[corpus-lifecycle]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family E — Conventions and compile

Twelve cases. Sources: R7 E4/E6/E8; R8 cases 9/10/12; R9 E3/E7/E9/E10/E12; R4 E10.

| Input the agent sees | Expected |
|---|---|
| existing `FuzzReverse` with a committed failing `testdata/fuzz/FuzzReverse/<hash>` | recognise the baseline failure, reproduce with `-run=FuzzReverse/<hash>`, fix or report, never delete the file |
| agent-proposed `go test -fuzz=Fuzz ./...` | correct to `-run='^$' -fuzz='^FuzzX$' ./pkg` with a budget |
| `.clusterfuzzlite/` present and a target with `type UserID string` argument | flag both engines fail; rewrite to `string`; seeds into `testdata/fuzz` + zip |
| Hypothesis "< 1 % of test cases satisfied assumptions" | fix the strategy; do not raise `max_examples` or suppress the health check |
| Hypothesis "nothing left to do" after 16 cases on 16 enum members | recognise domain exhaustion; do not increase the budget |
| CI printed `@reproduce_failure('6.170.14', b'...')` | reproduce locally, commit the concrete `@example`, remove the blob |
| Rust `decode(&[u8])` with `Vec::with_capacity(len)` from the header | target with `-max_len` and a bounded body; expect an OOM finding and a length-validation recommendation; regression fixture |
| 10 min of libFuzzer output flat since minute 2; coverage shows `parse_body` 0 % | stop for this corpus; diagnose reachability; add seeds or a mutator; do not extend time |
| proposed harness calls `process::exit(1)` and prints every input | reject; fix |
| CI YAML with `rustup default nightly` and `cargo fuzz build -O` | missing debug assertions and unpinned nightly; propose the pinned recipe |
| `cargo fuzz run` produced `crash-…`; "what next" | `tmin`, reproduce, `fmt`, `#[test]` regression, fix, rerun; do not commit `fuzz/artifacts` wholesale |
| harness that writes temp files and shells out per input | reject on throughput and safety; restructure in-process |

## Graders

- `go vet` and `go test -run='^Fuzz'` pass; `cargo fuzz build` or `cargo test` pass; `pytest`
  pass — exit codes written to a file by the agent and graded by regex (the sandbox grants
  `Bash(go test *)` and friends per [[eval-tooling]]).
- Correct paths; `-run='^$' -fuzz='^FuzzX$'` form in CI snippets; `--debug-assertions` present
  with `-O`; no `@reproduce_failure` committed; no deleted seed files.
- LLM judge: CI recipe matches the ecosystem's smoke/batch split.

Acceptance: compiles and passes seeds in every run ([[acceptance-criteria]]).
