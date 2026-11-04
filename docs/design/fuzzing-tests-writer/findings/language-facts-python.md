---
note_id: "20261103150302"
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
aliases: ["Language facts — Python"]
tags: [fuzzing, design/finding, lang/python, h5, h3, h4]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
grounded_in: ["[[08-lang-python|R8]]"]
realised_by: ["[[skill-python-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
opens: ["[[FTW-OQ-006-hypofuzz-licence]]"]
related: ["[[language-facts-go]]", "[[language-facts-rust]]"]
---
# Language facts — Python

Source: [[08-lang-python|R8]] (Hypothesis 6.170.14, Atheris 3.1.0, HypoFuzz as of 2026-11-03).

| Topic | Fact |
|---|---|
| Three tools, three jobs | **Hypothesis**: property-based inside pytest, typed/structured inputs, shrinking, example database, no coverage feedback, stops at `max_examples` (100). **Atheris**: libFuzzer for Python, coverage-guided, byte-oriented, runs forever, instruments C extensions with ASan. **HypoFuzz**: coverage-guided fuzzing of unmodified Hypothesis tests, failures land in the Hypothesis database so `pytest` replays them; free for non-commercial use only. |
| What fuzzing finds | almost never a "crash": wrong exception types, exponential or infinite loops (CPython #90863), wrong results via differential or round-trip oracles (ujson #440), memory errors only in native extensions (Pillow CVE-2020-35653). |
| Stop reasons (observable) | `--hypothesis-show-statistics` prints "Stopped because settings.max_examples=N" (budget), "nothing left to do" (domain exhausted — do not raise the budget), "< 1 % of test cases satisfied assumptions" (strategy is wrong — fix it); shrinking capped at 500 shrinks / 300 s. Atheris never stops without `-atheris_runs=N` or `-max_total_time`. |
| CI profile | with `CI`/`GITHUB_ACTIONS`/… set, Hypothesis auto-loads `ci`: `derandomize=True, deadline=None, database=None, print_blob=True`; a conftest that loads `default` silently undoes it; pair the deterministic PR gate with a nightly non-derandomised or HypoFuzz run. |
| Reproduction | pin confirmed bugs as `@example(...)`; never commit `@reproduce_failure` (blob is version-specific); `.hypothesis/` stays out of VCS; `GitHubArtifactDatabase` / Redis for cross-run memory. |
| Health checks | `filter_too_much` at 50 rejected draws → rewrite the strategy, never suppress; `function_scoped_fixture` and `differing_executors` are correctness checks and are never suppressed; prefer `.filter` over `assume`, `assume` over early `return`. |
| Structure | `builds`, `from_type`, `@composite`, `recursive`, `from_regex`, `from_lark`; `RuleBasedStateMachine` for state; `target()` only with ≥1 000 examples; Atheris `FuzzedDataProvider` for knobs; `test.hypothesis.fuzz_one_input` lets one `@given` test run under Atheris (OSS-Fuzz ujson does this); corpus bytes are tied to the Hypothesis version. |
| Atheris layout and run | `tests/fuzz/<name>_fuzzer.py` (`*_fuzzer.py` is the OSS-Fuzz discovery glob), `corpus/<name>/`, `<name>.dict`; `with atheris.instrument_imports(): import lib`; `atheris.Setup(sys.argv, TestOneInput)`; `-atheris_runs=N` in CI; expected exceptions caught; crash artefacts become regression seeds. |
| Native extensions | build with `-fsanitize=address,fuzzer-no-link`, `LD_PRELOAD` Atheris' `asan_with_fuzzer.so`, `ASAN_OPTIONS=detect_leaks=0`, `enable_python_coverage=False` when only native coverage matters; never preload ASan for pure-Python targets. |
| Not fuzzing | `pytest-randomly`, `Faker` (no oracle, no shrinking, no feedback); `pythonfuzz` archived; `python-afl` superseded; `schemathesis` = Hypothesis over OpenAPI/GraphQL with built-in checks (use it for HTTP APIs); `crosshair` = symbolic backend for Hypothesis, pure-Python deterministic code only. |
| Existing agent prompts | Hypothesis' `.claude/commands/hypothesis.md` and Anthropic's `agentic-pbt` `hypo.md` agree on the discipline; reuse them ([[oracle-ladder]]). Reported validity of agent-found bugs 56 % valid / 32 % worth reporting — UNVERIFIED (search snippet). |

## Decision rule (R8 §5.1)

≤ ~10 known cases → parametrised test; typed function with a statable relation → Hypothesis;
API with state → `RuleBasedStateMachine`; parser/decoder over bytes or any C-extension boundary →
Atheris (+ASan if native); structured grammar input with Python logic → Hypothesis strategy under
HypoFuzz (or Atheris via `fuzz_one_input`); HTTP API with a schema → schemathesis; glue with no
property of its own → do not fuzz.

Skeletons: R8 §5.2 (Hypothesis) and §5.3 (Atheris); review checklist §5.5; CI recipe §5.6.
