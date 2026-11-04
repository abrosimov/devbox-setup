---
note_id: "20261103150205"
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
aliases: ["Corpus lifecycle"]
tags: [fuzzing, design/finding, h2, h3, h5]
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[03-structure-aware-generation|R3]]", "[[07-lang-go|R7]]", "[[09-lang-rust|R9]]", "[[08-lang-python|R8]]"]
realised_by: ["[[skill-fuzzing-campaign]]", "[[automation-scripts]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-D-stopping]]"]
related: ["[[input-shape-triage]]", "[[stopping-algorithm]]"]
---
# Corpus lifecycle

A checklist (R2 §5.2) for the seed, working and regression corpus before, during and after a run;
the per-ecosystem paths are in the `language-facts-*` notes. The wrappers are `fuzz_corpus.py`
([[automation-scripts]]); the per-ecosystem commit policy is open in
[[FTW-OQ-008-corpus-commit-policy]].

## Before fuzzing

- Collect valid, small, diverse seeds from tests, fixtures, docs, bug reports; smallest input per
  feature; provenance and licence recorded (corpus bytes appear in bug reports — OSS-Fuzz).
- Put seeds where the engine **and** the normal test runner find them: Go `testdata/fuzz/<FuzzName>/`
  or `f.Add`; cargo-fuzz `fuzz/corpus/<target>/` (or a committed `fuzz/seeds/`); libFuzzer/OSS-Fuzz
  `<target>_seed_corpus.zip`; Hypothesis `@example(...)`, never the database.
- Minimise the seed set (`afl-cmin`, `-merge=1`, `cargo fuzz cmin`); add a dictionary for token
  formats; run the discoverability check once; confirm determinism; fix timeouts, OOMs and shallow
  bugs first or "fuzzing will stall quickly".

## During

- Working corpus stays out of the repository: Go `$GOCACHE/fuzz` (unbounded, `go clean -fuzzcache`),
  AFL `out/*/queue`, Hypothesis `.hypothesis/`; cargo-fuzz `fuzz/corpus` is git-ignored by `cargo
  fuzz init` and is committed only after `cmin` or kept in a storage repository as ClusterFuzzLite
  does.
- Parallel instances share one corpus directory; prune daily when batch fuzzing accumulates
  ("mandatory when batch fuzzing" — ClusterFuzzLite).

## After a run

- Minimise crashers (`-minimize_crash=1`, `cargo fuzz tmin`, `afl-tmin`; Go does it automatically
  for 60 s and only for string/byte arguments); check the crash state did not change; reproduce from
  the artefact path.
- Commit the **regression set** in the ecosystem's form: Go writes `testdata/fuzz/FuzzX/<hash>` and
  plain `go test` replays it; Rust copies the minimised artefact into a `#[test]` fixture (or
  bolero's committed `__fuzz__`); Atheris crash files go into the committed seed corpus.
- Merge new-coverage inputs back into the committed seeds, re-`cmin`, generate a coverage report
  and keep the uncovered-function list for the next escalation rung.
- Staleness: renaming a target or `go clean -fuzzcache` loses the generated corpus; a changed input
  format invalidates seeds (re-run the sanity gate); Hypothesis database entries drop on version or
  test change; corpora built through a generator (`fuzz_one_input`, `MakeFuzz`, `arbitrary`; the
  bridges of [[fuzzing-vs-pbt-boundary]]) are tied to the generator's version and are not durable
  assets (R3 §4.5).

Crashers are deduplicated by crash state before they are counted; the figures are in
[[reporting-and-claim-hygiene]].
