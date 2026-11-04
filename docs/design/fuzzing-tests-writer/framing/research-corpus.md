---
note_id: "20261103150103"
created: 2026-11-03
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: corpus-description
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Research corpus"]
tags: [fuzzing, design/framing]
related: ["[[research-index]]", "[[fpf-framing]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[02-stopping-and-corpus-lifecycle|R2]]", "[[03-structure-aware-generation|R3]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[05-fuzzingbook-part2-syntactic|R5]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]", "[[10-eval-tooling-notes|R10]]"]
---
# Research corpus

Ten annexes (≈3 100 lines) written by parallel research agents against one brief
([[00-research-brief]]); index at [[research-index]].

| Annex | Topic | Primary sources (GitHub source of the rendered site unless noted) |
|---|---|---|
| [[01-methods-and-applicability\|R1]] | Method families; applicability gate; oracle catalogue; evaluation hygiene; cost | google/fuzzing docs, libFuzzer flags, Go fuzz docs and design draft, rust-fuzz book and trophy case, Atheris, Hypothesis, OSS-Fuzz, AFL++, Fuzzing Book; Klees 2018, Schloegel 2024 guidelines, Böhme (abstract level) |
| [[02-stopping-and-corpus-lifecycle\|R2]] | Saturation theory; engine observables; corpus lifecycle; CI budgets; stopping algorithm | Fuzzing Book "When To Stop Fuzzing", libFuzzer source, AFL++ docs, AFLFast, Go `internal/fuzz`, cargo-fuzz source, Hypothesis source, ClusterFuzzLite, OSS-Fuzz |
| [[03-structure-aware-generation\|R3]] | Why bytes fail; grammars, typed generators, custom mutators, repair; seeds; shrinking | libFuzzer structure-aware doc, libprotobuf-mutator, AFL++ custom mutators, `arbitrary`, Hypothesis, rapid, go-fuzz-headers, Fuzzing Book, Zest/AFLSmart (abstract) |
| [[04-fuzzingbook-part1-lexical\|R4]] | Fuzzing Book Part I | uds-se/fuzzingbook notebooks and rendered HTML |
| [[05-fuzzingbook-part2-syntactic\|R5]] | Fuzzing Book Part II | same |
| [[06-fuzzingbook-parts3-5\|R6]] | Fuzzing Book Parts III–V | same, plus Go fuzz docs, AFL++ docs, ClusterFuzz glossary |
| [[07-lang-go\|R7]] | Go native fuzzing, rapid, go-fuzz-headers, OSS-Fuzz shim, bug classes; §8 re-verifies against go1.27.3 sources | golang/website, golang/go at tags, go-118-fuzz-build, rapid, OSS-Fuzz, golang/go issues |
| [[08-lang-python\|R8]] | Hypothesis, Atheris, HypoFuzz, schemathesis, crosshair; existing agent prompts | Hypothesis source and docs, Atheris, hypofuzz, OSS-Fuzz Python projects, CPython/Pillow/ujson issues |
| [[09-lang-rust\|R9]] | cargo-fuzz, libfuzzer-sys, `arbitrary`, bolero, proptest, afl.rs, honggfuzz, trophy case, RustSec | rust-fuzz repos, proptest, bolero, OSS-Fuzz, advisory-db, rustc docs |
| [[10-eval-tooling-notes\|R10]] | `claude plugin eval`, skill-creator scripts, headless mode | code.claude.com docs, anthropics/skills |

## Independence (RMP.7)

The Google lineage (google/fuzzing, OSS-Fuzz, ClusterFuzz, libFuzzer) is one tradition and restates
itself across R1–R3; AFL++/AFLFast is a second; the Fuzzing Book is a didactic synthesis that cites
both and adds the statistical line (Böhme); the language ecosystems are three independent empirical
records (Go issue tracker, Rust trophy case and RustSec, Python OSS-Fuzz projects); the
property-based-testing tradition is separate and partly in tension with greybox on whether coverage
feedback matters for typed inputs (R1 §4.2, R9 §4 D6).

## Access caveats

`fuzzingbook.org`, `go.dev`, `llvm.org`, `docs.rs`, `hypothesis.readthedocs.io`,
`rust-fuzz.github.io`, `google.github.io`, `arxiv.org` were not reachable from the research session.
Tool documentation was read from the GitHub repositories that render those sites. Paper bodies that
exist only on those hosts are cited at abstract level and marked UNVERIFIED in the ledgers; see
[[FTW-OQ-001-unverified-paper-bodies]] and [[FTW-OQ-002-libfuzzer-legend]].
