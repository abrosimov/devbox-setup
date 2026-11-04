---
note_id: "20261103150504"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family B", "Oracle"]
tags: [fuzzing, design/eval]
addresses: ["[[H4-crash-only-oracle]]"]
tests: ["[[oracle-ladder]]", "[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Eval family B — Oracle inside the fuzz target

Eight cases, all with a `fuzz` gate outcome; the question is which rung of the [[oracle-ladder]]
the harness stands on. Sources: R4 E5/E6/E7; R7 E1; R8 micro-example 1; R9 E8, M1; R1 case 15.

| Input the agent sees | Expected |
|---|---|
| Go/Rust harness whose body is `_ = Parse(data)` on a memory-safe parser with a `Format` counterpart | flag weak oracle; add round trip (`Format(Parse(x))` re-parses equal), result invariants, skip-invalid handling |
| two draft harnesses for a triangle classifier fed from a text line: one asserts "not Equilateral when sides differ", one asserts the exact category | prefer the strong oracle; justify with a small mutation experiment |
| `my_sqrt` fuzz target over floats decoded from bytes in `[1, 1e6]` only | add 0, negatives, inf, NaN to seeds; per-input timeout; inverse-property check with tolerance |
| Go `ParseHeader` / `Marshal` pair with fixtures | round trip, output-size bound, seed run first |
| Python `ujson`-style decoder with a stdlib reference available | differential harness (`json` vs `ujson`), skip when either raises, re-serialise both, documented broad `except` |
| Rust `Url::parse` / `to_string` pair | round-trip check inside `fuzz_target!` (the rust-url #729 pattern), `Corpus::Reject` on parse failure |
| existing Rust target asserting `parse(data).is_ok()` on raw bytes | rewrite with `if let Ok` and a real property; state that the old target only finds invalid input |
| Go decoder of a length-prefixed archive format where only DoS matters | crash + timeout + allocation-bound oracle, justified by Go's security-policy classes |

## Graders

- Regex on the harness file: at least one assertion that is not "does not panic"; contract
  statement present in the header comment; no PBT framework imported.
- LLM judge: the oracle is the strongest the target admits; expected-exception or
  expected-error classification is explicit.
