---
note_id: "20261103150503"
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
aliases: ["Eval family A", "Gate"]
tags: [fuzzing, design/eval]
addresses: ["[[H1-no-applicability-gate]]"]
tests: ["[[applicability-gate]]", "[[skill-fuzzing-applicability]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family A — Gate

Twelve cases, half of which expect "do not fuzz". Sources: R1 §6 cases 1/3/5/7/12/14; R7 E2/E3/E9;
R8 cases 6/7; R9 E1/E2.

| Input the agent sees | Expected |
|---|---|
| Go `LoadConfig(path)` reading YAML and calling `yaml.Unmarshal` | do not fuzz (filesystem + upstream-fuzzed parser); unit tests for own validation |
| Go `ParseFrame([]byte)` custom binary protocol | fuzz: native target, seeds from captured frames, round trip, `testdata/fuzz/FuzzParseFrame/` |
| Rust `parse(&str) -> Result<Ast>` + `Display` | fuzz with cargo-fuzz, dictionary of keywords, round-trip oracle, debug assertions kept |
| Rust `mean(&[f64])` | proptest with metamorphic relations; not a fuzz target |
| Python Lambda handler calling boto3/DynamoDB | do not fuzz; extract the pure transformation |
| Python `class LRUCache` | model-based `RuleBasedStateMachine` |
| Go `MustCompilePattern` / `CompilePattern` | fuzz `CompilePattern` only |
| Go `Add(a, b Money)` with documented laws | rapid property test; no fuzz target |
| Go `IsWeekend(t time.Time)` | table test over weekdays and zone edges |
| Go "fuzz our HTTP handler end-to-end" | decline; propose the request-parsing function in isolation |
| Django view with `get_object_or_404` | do not fuzz; parametrised 200/404 test; schemathesis if a schema exists |
| Rust `#[derive(Serialize, Deserialize)]` config with no custom impls | do not write a cargo-fuzz target |

## Graders

- `file_exists` negative: no `Fuzz*` function, `fuzz_target!`, or `*_fuzzer.py` created in
  do-not-fuzz cases.
- Regex on the last message for the quoted gate row and the decision token.
- LLM judge: the decision names the matching row and reason and proposes the right alternative.

Acceptance: no false "fuzz" on a do-not-fuzz case in any run ([[acceptance-criteria]]).
