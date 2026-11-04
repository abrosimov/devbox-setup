---
note_id: "20261103150205"
created: 2026-11-03
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

Mechanical, so a checklist (R2 §5.2); the per-ecosystem paths are in the `language-facts-*` notes.

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
  bolero's committed `__fuzz__`); Atheris crash files go into the committed seed corpus. (For
  reference only, PBT track: proptest commits `proptest-regressions/` seeds, Hypothesis pins
  `@example` — [[fuzzing-vs-pbt-boundary]].)
- Merge new-coverage inputs back into the committed seeds, re-`cmin`, generate a coverage report
  and keep the uncovered-function list for the next escalation rung.
- Staleness: renaming a target or `go clean -fuzzcache` loses the generated corpus; a changed input
  format invalidates seeds (re-run the sanity gate); Hypothesis database entries drop on version or
  test change; corpora built through a generator (`fuzz_one_input`, `MakeFuzz`, `arbitrary`) are
  tied to the generator's version and are not durable assets (R3 §4.5).

## Crash deduplication

Crash state (sanitizer/panic type + top frames) is the practical key; Klees et al. show stack
hashes over-count (~46 per bug) and collide (~16 %), abstract level; timeouts and OOMs cannot be
deduplicated at all — one each per target. Ground truth is "one fix" (R2 §3.3 C8).

## Design consequence

Checklist and per-engine commands in [[skill-fuzzing-campaign]]; wrappers in `fuzz_corpus.py`
([[automation-scripts]]); commit policy per ecosystem is graded in [[eval-family-E-conventions]]
and recorded in [[FTW-OQ-008-corpus-commit-policy]].
