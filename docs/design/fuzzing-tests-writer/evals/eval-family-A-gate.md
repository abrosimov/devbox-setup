---
note_id: "20261103150503"
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
aliases: ["Eval family A", "Gate"]
tags: [fuzzing, design/eval]
addresses: ["[[H1-no-applicability-gate]]"]
tests: ["[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]", "[[skill-fuzzing-applicability]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Eval family A — Gate

Twelve cases covering all four gate outcomes; release criterion in [[acceptance-criteria]].
Sources: R1 §6 cases 1/3/5/7/12/14; R7 E2/E3/E9; R8 cases 6/7; R9 E1/E2.

| Input the agent sees | Expected |
|---|---|
| Go `LoadConfig(path)` reading YAML and calling `yaml.Unmarshal` | `do-not-fuzz` (filesystem + upstream-fuzzed parser); recommend unit tests for own validation |
| Go `ParseFrame([]byte)` custom binary protocol | `fuzz`: native target, seeds from captured frames, round trip, `testdata/fuzz/FuzzParseFrame/` |
| Rust `parse(&str) -> Result<Ast>` + `Display` | `fuzz`: cargo-fuzz, dictionary of keywords, round-trip oracle inside the target, debug assertions kept |
| Rust `mean(&[f64])` | `out-of-scope: pbt-track` (metamorphic relations, no reference, no byte input); nothing written |
| Python Lambda handler calling boto3/DynamoDB | `do-not-fuzz`; name the pure transformation that could be gated separately |
| Python `class LRUCache` | `out-of-scope: pbt-track` (model-based); nothing written |
| Go `MustCompilePattern` / `CompilePattern` | `fuzz` `CompilePattern` only; `Must*` excluded by contract |
| Go `Add(a, b Money)` with documented laws | `out-of-scope: pbt-track`; no rapid test written; reason recorded |
| Go `IsWeekend(t time.Time)` | `out-of-scope: unit-tests` (enumerable domain) |
| Go "fuzz our HTTP handler end-to-end" | `do-not-fuzz` as is; propose the request-parsing function in isolation |
| Django view with `get_object_or_404` | `do-not-fuzz`; parametrised 200/404 is the unit-test track; schema testing is the PBT/API track |
| Rust `#[derive(Serialize, Deserialize)]` config with no custom impls | `do-not-fuzz`; derive code is serde's, already fuzzed upstream |

## Graders

- `file_exists` negative: no `Fuzz*` function, `fuzz_target!`, or `*_fuzzer.py` created in
  non-fuzz cases; **no `@given`, `proptest!` or `rapid.Check` written in any case**.
- Regex on the last message for the decision token and the quoted gate row.
- LLM judge: the decision names the matching row and reason; `pbt-track` hand-offs state what the
  PBT agent would test, without writing it.
