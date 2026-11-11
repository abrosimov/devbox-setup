---
note_id: "20261103150999"
modified: 2026-11-10
created: 2026-11-03
language: en
type: research
subtype: index
note_role: artifact
artifact_kind: map-of-content
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Research index", "Annexes"]
tags: [fuzzing, design/research, design/hub]
related: ["[[fuzzing-tests-writer]]", "[[research-corpus]]"]
---
# Research index

> Historical research from 2026-11-03; the body below is retained as provenance. Its proposals
> are not current requirements. The 2026-11-10 disposition is [[methodology-review]]: PBT and
> mutation analysis are excluded; saturation/escalation rules and provider recipes must not be
> imported into authoring. Current operations are specified in [[agent-procedure]].

Source-linked research pack (FPF `G.2` SoTA portfolio) behind
[[fuzzing-tests-writer]] (see [[research-corpus]] for the independence note). Each file follows the
format in `00-research-brief.md`: summary, scope, corpus ledger (source + edition + locator +
status), claim sheets per tradition, disagreements, implications for the agent/skills keyed to
hypotheses H1–H5, candidate eval cases, micro-examples.

| File | Topic |
|---|---|
| [[00-research-brief]] | Brief given to the research agents (method, output format, H1–H5) |
| [[01-methods-and-applicability]] | Method families; when fuzzing is and is not applicable; oracles; evaluation hygiene |
| [[02-stopping-and-corpus-lifecycle]] | Saturation theory, engine observables, stopping algorithm, corpus lifecycle, report template |
| [[03-structure-aware-generation]] | Grammars, typed generators, custom mutators, repair, seeds, shrinking |
| [[04-fuzzingbook-part1-lexical]] | The Fuzzing Book, lexical material (historical part label) |
| [[05-fuzzingbook-part2-syntactic]] | The Fuzzing Book, syntactic material (historical part label) |
| [[06-fuzzingbook-parts3-5]] | The Fuzzing Book, semantic/domain/managing material (historical part labels) |
| [[07-lang-go]] | Go native fuzzing and ecosystem; §8 verifies the facts against the go1.27.3 sources |
| [[08-lang-python]] | Hypothesis, Atheris, HypoFuzz and the rest of the Python ecosystem |
| [[09-lang-rust]] | cargo-fuzz, `arbitrary`, proptest, bolero and the Rust ecosystem |
| [[10-eval-tooling-notes]] | `claude plugin eval`, skill-creator scripts, headless mode |

Access note: `fuzzingbook.org`, `go.dev`, `llvm.org`, `docs.rs`, `hypothesis.readthedocs.io`,
`rust-fuzz.github.io`, `google.github.io` and `arxiv.org` were not reachable from the research
session (2026-11-03). Tool documentation was read from the GitHub repositories that render those
sites; paper bodies hosted only there are marked UNVERIFIED or abstract-level in the ledgers and
must be re-checked before a skill quotes them.
