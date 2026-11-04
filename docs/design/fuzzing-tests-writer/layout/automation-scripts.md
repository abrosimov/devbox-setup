---
note_id: "20261103150409"
created: 2026-11-03
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: scripts
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Automation scripts", "fuzz_campaign.py", "fuzz_corpus.py"]
tags: [fuzzing, design/component]
addresses: ["[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]", "[[H6-crash-counting-reports]]"]
realises: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-D-stopping]]"]
decided_by: ["[[FTW-D-003-thresholds-as-flags]]"]
target_path: "roles/devbox/files/dot_claude/bin/"
related: ["[[skill-fuzzing-campaign]]", "[[eval-tooling]]"]
---
# Automation scripts

Two stdlib-only Python scripts in the existing `dot_claude/bin/` uv project, with unit tests in the
same suite so `make test-claude-hooks` covers them. Both are engine-agnostic at the interface; the
language skills only fill in flags.

## `fuzz_campaign.py`

- `run --engine {go,libfuzzer,atheris,hypothesis} --budget {interactive,smoke,batch,deep}
  --target … -- <engine args>`: refuses to start without a cap; injects `-fuzztime` /
  `-max_total_time` / `-atheris_runs` / `max_examples` from the class; streams the engine output;
  samples counters every 60 s (Go via `-json` `output` events, libFuzzer via `pulse`/`NEW`/`REDUCE`
  lines and `-print_final_stats=1`, Hypothesis via `--hypothesis-show-statistics`); applies the
  sanity gate and the plateau test of [[stopping-algorithm]] with the ◇ defaults as flags; writes
  `campaign.json` (decision token, counters per window, `p̂_W`, artefacts) and renders the report
  template of [[reporting-and-claim-hygiene]] to Markdown.
- `discoverability`: seeded versus empty-corpus run at equal budget.
- `triage`: minimise, reproduce three times, bucket by crash state, convert to the ecosystem's
  regression fixture.

## `fuzz_corpus.py`

Per-engine wrappers for `cmin`/`merge` and `tmin`; raw-seed import (`file2fuzz` for Go, directory
copy for cargo-fuzz and Atheris); seed statistics (count, bytes, largest); grammar-coverage adequacy
count when a grammar file is given.

## Optional later

Mutation-score self-assessment (10–30 statement-deletion mutants against the harness oracle,
R4 §5.6) once the first two scripts are stable; no evidence shows an agent needs it to pass the evals.

## Repository integration

`make validate-claude` accepts the new agent/skill cross-references; `make validate-skills` sees
`evals/` in each skill; `codex.yml` shared-skill list gains the six names;
`tests/deploy/test_codex_assets.py` checks the 29→30 agent count.
