# Research annexes for the fuzzing tests writer design

Source-linked research pack (FPF `G.2` SoTA portfolio) behind
[`../../fuzzing-tests-writer-agent.md`](../../fuzzing-tests-writer-agent.md). Each file follows the
format in `00-research-brief.md`: summary, scope, corpus ledger (source + edition + locator +
status), claim sheets per tradition, disagreements, implications for the agent/skills keyed to
hypotheses H1–H5, candidate eval cases, micro-examples.

| File | Topic |
|---|---|
| `00-research-brief.md` | Brief given to the research agents (method, output format, H1–H5) |
| `01-methods-and-applicability.md` | Method families; when fuzzing is and is not applicable; oracles; evaluation hygiene |
| `02-stopping-and-corpus-lifecycle.md` | Saturation theory, engine observables, stopping algorithm, corpus lifecycle, report template |
| `03-structure-aware-generation.md` | Grammars, typed generators, custom mutators, repair, seeds, shrinking |
| `04-fuzzingbook-part1-lexical.md` | The Fuzzing Book, Part I |
| `05-fuzzingbook-part2-syntactic.md` | The Fuzzing Book, Part II |
| `06-fuzzingbook-parts3-5.md` | The Fuzzing Book, Parts III–V (incl. "When To Stop Fuzzing") |
| `07-lang-go.md` | Go native fuzzing and ecosystem; §8 verifies the facts against the go1.27.3 sources |
| `08-lang-python.md` | Hypothesis, Atheris, HypoFuzz and the rest of the Python ecosystem |
| `09-lang-rust.md` | cargo-fuzz, `arbitrary`, proptest, bolero and the Rust ecosystem |
| `10-eval-tooling-notes.md` | `claude plugin eval`, skill-creator scripts, headless mode |

Access note: `fuzzingbook.org`, `go.dev`, `llvm.org`, `docs.rs`, `hypothesis.readthedocs.io`,
`rust-fuzz.github.io`, `google.github.io` and `arxiv.org` were not reachable from the research
session (2026-11-03). Tool documentation was read from the GitHub repositories that render those
sites; paper bodies hosted only there are marked UNVERIFIED or abstract-level in the ledgers and
must be re-checked before a skill quotes them.
