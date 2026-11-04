---
note_id: "20261103150302"
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
aliases: ["Language facts — Python"]
tags: [fuzzing, design/finding, lang/python, h5, h3, h4]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
grounded_in: ["[[08-lang-python|R8]]"]
realised_by: ["[[skill-python-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
opens: ["[[FTW-OQ-006-hypofuzz-licence]]"]
related: ["[[language-facts-go]]", "[[language-facts-rust]]", "[[fuzzing-vs-pbt-boundary]]", "[[pbt-agent-prompts]]"]
---
# Language facts — Python

Source: [[08-lang-python|R8]] (Atheris 3.1.0, Hypothesis 6.170.14, HypoFuzz, as of 2026-11-03).
Fuzzing-side facts first; the Hypothesis rows are boundary facts only ([[fuzzing-vs-pbt-boundary]]).

## Fuzzing side (this agent)

| Topic | Fact |
|---|---|
| Engine | **Atheris** = libFuzzer for Python: coverage-guided by bytecode instrumentation, byte-oriented, runs forever, instruments C extensions with ASan; Linux/macOS, Python 3.11–3.14. `atheris.Setup(sys.argv, TestOneInput)`; `TestOneInput(data: bytes)`; `atheris.Fuzz()` does not return. |
| Instrumentation | `with atheris.instrument_imports(): import lib` (must wrap the import), `@atheris.instrument_func`, `atheris.instrument_all()` (slow, experimental); instrumenting nothing yields "No interesting inputs were found" — a sanity-gate signal. |
| Failure model | any uncaught Python exception is a finding; expected exception types are caught in the harness (`except DecodeError: return`); timeouts and RSS limits are libFuzzer's. What fuzzing finds: wrong exception types, exponential/infinite loops (CPython parser #90863), wrong results via differential oracles (ujson #440), native memory errors (Pillow CVE-2020-35653). |
| Structure | `FuzzedDataProvider`: `ConsumeBytes`, `ConsumeUnicode[NoSurrogates]`, `ConsumeInt[InRange]`, `ConsumeIntList`, `ConsumeFloat` (NaN/Inf), `ConsumeBool`, `PickValueInList`; consumption after exhaustion yields zeros/empties; custom mutators (`custom_mutator=`, `atheris.Mutate`) for compressed input; libprotobuf-mutator contrib. |
| Stop and budget | never stops by itself; CI passes `-atheris_runs=N` (not `-runs`) or `-max_total_time`; coverage reports only on graceful exit. |
| Layout | `tests/fuzz/<name>_fuzzer.py` (OSS-Fuzz discovery glob `*_fuzzer.py`), `corpus/<name>/`, `<name>.dict`; crash artefacts (`crash-<sha1>`) become regression seeds in the corpus. |
| Native extensions | build with `-fsanitize=address,fuzzer-no-link`; `LD_PRELOAD` Atheris' `asan_with_fuzzer.so`; `ASAN_OPTIONS=detect_leaks=0`; `enable_python_coverage=False` when only native coverage matters; never preload for pure-Python targets. |
| Oracles in the target | round trip (`loads(dumps(x)) == x`), differential (`json` vs `ujson`, idna vs libidn2 — the OSS-Fuzz ujson project), timeouts as findings, resource limits. |
| HypoFuzz | a coverage-guided **fuzzer** (branch coverage via `sys.monitoring`) over an **existing** Hypothesis suite; runs until interrupted; failures land in the Hypothesis database so `pytest` replays them; run ≥ 1 h, restart workers every 12–24 h; licence free for non-commercial use only ([[FTW-OQ-006-hypofuzz-licence]]). In scope as an engine when the tests already exist; this agent does not write the tests. |
| `fuzz_one_input` bridge | `test.hypothesis.fuzz_one_input(bytes)` drives one existing `@given` test from libFuzzer bytes (OSS-Fuzz ujson `hypothesis_structured_fuzzer.py`); `deadline`/`derandomize`/`max_examples` do not apply; corpus bytes are tied to the Hypothesis version; shrinking and dedup happen later in `pytest`. Hybrid: allowed only for an existing test. |
| OSS-Fuzz | `language: python3`, `base-builder-python` (Atheris preinstalled), `compile_python_fuzzer $SRC/**/*_fuzzer.py`, `<target>_seed_corpus.zip`, `<target>.dict`, `.options`; sanitizers `address`/`undefined` for native code; reproduce with `-timeout=65 -rss_limit_mb=2560`. |
| Not fuzzing | `pytest-randomly`, `Faker` (no oracle, no shrinking, no feedback); `pythonfuzz` archived; `python-afl` superseded by Atheris; `crosshair` is symbolic (PBT backend). |

## Boundary facts (PBT track; recorded so the gate can hand off correctly)

| Topic | Fact |
|---|---|
| Hypothesis | property-based testing inside pytest: typed strategies, shrinking, example database, no coverage feedback, stops at `max_examples` (100) or domain exhaustion; `RuleBasedStateMachine` for stateful models; `target()` for guided search; Ghostwriter scaffolds. All of this is the PBT agent's material. |
| Repro conventions there | `@example` pins, `@reproduce_failure` blob is version-specific, `.hypothesis/` out of VCS, `ci` profile auto-loaded. Only relevant to this agent when a hybrid bridge is used. |
| schemathesis | Hypothesis over OpenAPI/GraphQL with built-in checks — API-testing/PBT track. |
| Existing prompts | Hypothesis' `.claude/commands/hypothesis.md` and Anthropic's `agentic-pbt` — [[pbt-agent-prompts]]. |

## Decision rule (R8 §5.1, restated for this agent's scope)

parser/decoder/decompressor over `bytes`/`str`, or any C-extension boundary → Atheris (+ASan if
native); existing Hypothesis suite with spare CPU → HypoFuzz (licence permitting); existing `@given`
test on an untrusted hot path → Atheris via `fuzz_one_input`; typed function with a statable
relation, stateful API, HTTP API with a schema → `out-of-scope: pbt-track`; glue with no property
of its own, `json.loads` wrapper → do not fuzz.

Skeleton R8 §5.3 (Atheris); review checklist R8 §5.5 (fuzz items); CI recipe R8 §5.6 (fuzz rows).
