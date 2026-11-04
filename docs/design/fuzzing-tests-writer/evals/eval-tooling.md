---
note_id: "20261103150510"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: tooling
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval tooling"]
tags: [fuzzing, design/eval]
grounded_in: ["[[10-eval-tooling-notes|R10]]"]
decided_by: ["[[FTW-D-004-evals-as-plugin]]"]
opens: ["[[FTW-OQ-009-plugin-eval-prerequisites]]"]
related: ["[[eval-plan]]", "[[automation-scripts]]"]
target_path: "tests/fuzzing_agent_evals/"
---
# Eval tooling

Four layers, from cheapest to most complete (R10).

1. **Skill triggering** — each skill ships `evals/trigger_evals.json` (~20 queries with near-miss
   negatives) and `evals/evals.json`; `make validate-skills` checks structure, `make eval-skills
   SKILL=…` runs Anthropic's `run_eval.py`, `make improve-skills` tunes the description (60/40
   train/test split, three runs per query). Existing machinery; no new code.
2. **Behavioural evals** — `claude plugin eval` targets a *plugin*, so a plugin directory
   `tests/fuzzing_agent_evals/plugin/` copies or links the agent and the six skills. Cases are
   `evals/<case>/prompt.md` (frontmatter `runs`, `max_turns`, `timeout_seconds`, `allowed_tools`,
   `tags`), `graders/*.md` (`regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`,
   with targets `last_message`, `trace`, `files`, `{source: file, path}`), and `case.yaml`
   (`schema_version "1.1"`, `context.scaffold_script` copying the fixture repository into the
   workspace). Local: `--scaffold --allow-tools "Bash(go test *),Bash(go vet *),Bash(cargo *),
   Bash(python *),Bash(pytest *)"`. CI: `--trust-plugin --json results.json --threshold 0.8
   --model <pinned> --judge-model <pinned> --no-publish --max-cost-usd <ceiling>`; exit 0 pass,
   1 below threshold, 2 partial. The delegation grader (`tool_used: Agent` with a `subagent_type`
   match) checks that an orchestrating session hands off fuzz requests to the agent and does not for
   plain unit-test requests. Granted Bash runs under the OS sandbox (Linux needs bubblewrap and
   socat); network is limited, hence vendored fixtures.
3. **Headless driver** — `claude -p --bare --agents <file> --add-dir <skills> --allowedTools …
   --output-format json --max-turns N --max-budget-usd M`, run from inside each fixture, for the
   B1 baseline arm and ad-hoc runs on recorded logs; writes the same per-case JSON so the two tools'
   results compare. `--bare` ignores `~/.claude/agents` and `~/.claude/skills` unless passed
   explicitly and needs `ANTHROPIC_API_KEY`.
4. **Campaign-script unit tests** — recorded engine logs double as fixtures for `fuzz_campaign.py`'s
   parser and decision logic under the existing `bin/` pytest suite, so the deterministic half of
   [[eval-family-D-stopping]] runs without a model.

## Hold-out and determinism

Hold-out by `--tag holdout` (the only mechanism available; not a documented feature). Pin `--model`
and `--judge-model` in CI so a model rollout is not read as a regression; keep
`aggregate-result.json` per run with model and date. Use `--ablation none` to halve cost when the
with/without delta is not needed.

`/skill-doctor` reports usage and context cost and `claude plugin validate` checks structure;
neither grades behaviour.
