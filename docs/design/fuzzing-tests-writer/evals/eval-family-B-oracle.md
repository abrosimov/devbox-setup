---
note_id: "20261103150504"
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
aliases: ["Eval family B", "Oracle"]
tags: [fuzzing, design/eval]
addresses: ["[[H4-crash-only-oracle]]"]
tests: ["[[oracle-ladder]]", "[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family B — Oracle

Eight cases. Sources: R4 E5/E6/E7; R7 E1; R8 cases 1/2; R9 E4/E8.

| Input the agent sees | Expected |
|---|---|
| Go/Rust harness whose body is `_ = Parse(data)` on a memory-safe parser | flag weak oracle; add round trip, result invariants, skip-invalid handling |
| two triangle-classification harnesses (weak vs exact category) | prefer the strong oracle; justify with a small mutation experiment |
| `my_sqrt` harness over `[1, 1e6]` floats | add 0, negatives, inf, NaN; timeout; inverse property with tolerance |
| Go `ParseHeader` / `Marshal` pair with fixtures | round trip, output-size bound, seed-run first |
| Python `parse_cron` / `format_cron` with `CronError` | round trip; separate test that arbitrary text raises only `CronError` |
| Python `fast_median` next to `statistics.median` | oracle test against the reference with justified constraints |
| Rust `to_hsl` / `from_hsl` | proptest round trip with tolerance; no nightly target |
| existing Rust target asserting `parse(data).is_ok()` on raw bytes | rewrite with `if let Ok` and a real property |

## Graders

- Regex on the harness file: at least one assertion that is not "does not panic"; contract
  statement present in the header comment.
- LLM judge: the oracle is the strongest the target admits; expected-exception classification is
  explicit.
