---
name: python-fuzzing
description: Build, qualify, run and replay Atheris fuzz targets, checking instrumentation and exception meaning while retaining useful inputs.
---

# Python fuzzing

Produce an Atheris harness, observed qualification results and replayable inputs for the assigned
Python target. Use the existing research scope and effort limits. Bounded reconnaissance can
discover a question from unfamiliar inputs without predicting a bug. PBT, Hypothesis/HypoFuzz
bridges and mutation analysis are outside this workflow.

## Establish the local basis

- Inspect repository instructions, packaging/lockfiles, existing fuzz entrypoints, corpus layout
  and the target contract. Use the repository's Python environment and launcher.
- Record interpreter and Atheris versions, dependency/build configuration, target commit/dirty
  changes and input selection. Check compatibility rather than substituting a different interpreter.
- Missing Atheris, native instrumentation or a required dependency is an environment gap. Install
  or rebuild only with existing authorisation; do not silently change the lockfile or system Python.
- Recover prior observations and the unfinished operation before starting more work. State the
  concrete material and possible learning contribution, or the question-led observation sought.

## Construct and qualify

Keep a deterministic callable accepting bytes. Instrument relevant Python imports with
`atheris.instrument_imports()` before importing them, or use the supported explicit instrumentation
API where imports already occurred. An `atheris.instrument_func` callback can provide callback
coverage, but it does not prove coverage of the intended product code. Put `atheris.Setup` and
`atheris.Fuzz` behind the executable entrypoint so importing a replay helper cannot start fuzzing.

Catch only exceptions the contract identifies as expected rejection, and only around the call that
may legitimately reject. Allow unexpected exceptions to remain observable. Do not suppress an oracle
failure with a broad `except Exception`, return-success wrapper or blanket exception conversion.
For round trips or comparisons, define the expected relation independently of the implementation.

Use known valid and expected-invalid inputs to demonstrate the product call and check. A module
import is not qualification. Inspect reached product behaviour with the project's existing coverage
tools when needed; distinguish callback coverage from product coverage. Native extensions require
their own compatible instrumentation/build evidence; pure-Python coverage does not supply it.

For structured choices, `FuzzedDataProvider` or a bounded explicit byte decoder can be used. Bound
sizes, recursion and operation counts, retain raw bytes plus decoder version, and preserve a route
for intentionally malformed input. Do not bypass production validation to improve reachability.

## Execute and replay

These examples assume `.venv/bin/python`, an executable `tests/fuzz/fuzz_decode.py`, and existing
corpus/artefact directories. Substitute repository paths and justified limits; create only the
authorised local output directories before running. Check the installed engine's `-help=1` output.

```text
.venv/bin/python tests/fuzz/fuzz_decode.py -help=1
.venv/bin/python tests/fuzz/fuzz_decode.py tests/fuzz/corpus/decode/valid-seed
.venv/bin/python tests/fuzz/fuzz_decode.py tests/fuzz/corpus/decode -max_total_time=30 -artifact_prefix=tests/fuzz/artifacts/decode/
```

A file argument selects libFuzzer replay; a directory supplies a search corpus. Inspect actual
execution and output rather than treating the path's existence as replay evidence. To replay a
corpus without search, pass its selected files or use the repository's ordinary callable runner;
do not assume pytest discovers an arbitrary corpus directory. Verify accepted, rejected and known
failing cases under the same decoder and oracle as search.

`-max_total_time` limits a search operation; `-timeout` is a per-input engine check. Select any
input-size/memory/time bounds from this experiment's contract. If using `coverage.py`, Atheris's
`-atheris_runs=N` supports graceful reporting; libFuzzer `-runs` may exit without that report.
Python and native failures can leave different diagnostics, so retain logs even when coverage
output is absent. A command limit or native exit does not by itself identify a product defect.

## Preserve and continue

- Keep useful coverage/structured seeds and regression inputs in durable replay storage. Record
  provenance, intended behaviour, command and observed replay status; a non-crashing seed can be
  valuable. Protect originals from automatic corpus replacement or unverified deduplication.
- Preserve original failures before reducing. If reduction is justified, test the same relevant
  exception or native symptom, not merely any non-zero exit. Keep the last verified candidate and
  classify missing, unstable or environment-dependent evidence as unresolved.
- Repair an authored harness/oracle defect within scope and revisit its affected conclusions.
  Report product defects without silently expanding the task to product repair.
- Save the question/learning aim, method, completed and unfinished operations, inputs, environment
  and effort on interruption. On return, recheck affected assumptions and perform the next justified
  operation; reading a checkpoint alone is not continuation. New material can form another in-scope
  question without reopening unrelated completed work.

Return commands/exits, environment and instrumentation evidence, harness changes, corpus paths,
verified replay instructions and finding classification. Distinguish product, harness/oracle,
environment and unconfirmed failures. Explain what was learned and what remains; process exit and
quiet counters do not establish research completion or saturation. Do not commit or publish inputs
without authority.

## Primary references

Checked 2026-11-12; consult the installed version's behaviour before using additional flags:

- [Atheris](https://github.com/google/atheris) — instrumentation, callback setup and Python coverage.
- [Native extensions](https://github.com/google/atheris/blob/master/native_extension_fuzzing.md) —
  conditional native build/instrumentation guidance; read when native code is in scope.
- [libFuzzer options](https://llvm.org/docs/LibFuzzer.html#options) — files versus corpora and limits.
