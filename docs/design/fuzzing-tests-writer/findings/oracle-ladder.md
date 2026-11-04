---
note_id: "20261103150202"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Oracle ladder"]
tags: [fuzzing, design/finding, h4]
addresses: ["[[H4-crash-only-oracle]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-B-oracle]]"]
related: ["[[applicability-gate]]", "[[reporting-and-claim-hygiene]]", "[[pbt-agent-prompts]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Oracle ladder

Pick the strongest oracle the target admits and name it in the harness header (R1 §3.10, §5.2;
R4 §5.4; R6 §5.4). The rung is a charter field ([[fuzzing-charter]]), and a "does not panic"
harness where a stronger rung is available fails review ([[eval-family-B-oracle]]). Hughes' ranking
of property kinds (model-based and metamorphic strongest) is partially verified (R1 §3.4).

| Rung | Oracle | Detects | Needs from the target | Fits |
|---|---|---|---|---|
| 1 | Model-based (state machine) | divergence from a simple model across call sequences | model + transition enum + preconditions | mutating APIs, protocols, caches |
| 2 | Differential | wrong results against a reference | second implementation; normalised output; spec without undefined behaviour | crypto, math, parsers with a reference |
| 3 | Round trip | lossy or asymmetric encode/decode, normalisation bugs | both directions; equality notion | codecs, marshal/unmarshal, parse/print |
| 4 | Metamorphic relation | wrong results without a reference | domain knowledge for the relation | numeric, search, sorting, compression |
| 5 | Invariant / postcondition | violated data-structure or output invariants | cheap checker | containers, parsers (valid UTF-8 out) |
| 6 | Resource limits | infinite loops, super-linear algorithms, unbounded allocation | per-input timeout, RSS/allocation cap | parsers, regex, decompressors |
| 7 | Crash / panic / exception | index out of range, nil/None, unwrap, assert, overflow (Rust debug), UTF-8 boundary | nothing | every target; the only oracle of a first byte-level target |

A harness that stands only on rungs 6–7 is accepted only for untrusted byte decoders where denial of
service is the risk (Go's security policy counts panics, stack exhaustion and unbounded reads as
security issues — R1 S15).

Rungs 1–5 state the relations a property-based test would state; here they are written **inside the
fuzz target** and checked on engine-generated inputs, as the Go tutorial, the Go blog and the
rust-url and ujson findings do (R7 §3.6, R9 §3.7, R8 §3.2). The triage and claim discipline this
agent borrows from the PBT agent prompts is in [[pbt-agent-prompts]].

## Ecosystem facts that change what the bottom rungs see

- Go records a worker killed by the OOM killer as *no crash*; only the 1 s per-input timeout
  surfaces allocation bugs; the engine has no sanitizer, leak check or allocation cap (R7 §3.1, §3.4).
- cargo-fuzz keeps debug assertions and overflow checks on by default; OSS-Fuzz's `-O` recipe turns
  them off unless `--debug-assertions` is added (R9 §3.1 C5, D4).
- Atheris reports any uncaught exception; expected exception types must be caught, and a broad
  `except Exception` is only acceptable in a documented differential harness (R8 §3.2).
- Rust ASan fires only on access: harnesses over FFI must touch every returned reference (R9 C17).
