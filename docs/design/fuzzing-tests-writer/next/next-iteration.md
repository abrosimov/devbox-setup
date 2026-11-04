---
note_id: "20261103150800"
created: 2026-11-03
language: en
type: design
subtype: plan
note_role: artifact
artifact_kind: plan
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Next iteration"]
tags: [fuzzing, design/plan]
related: ["[[fuzzing-tests-writer]]", "[[repository-placement]]", "[[acceptance-criteria]]"]
---
# Next iteration

Ordered so that each step has a gate before the next starts.

1. **Methodology skills first**: [[skill-fuzzing-applicability]], [[skill-fuzzing-campaign]],
   [[skill-structured-input-generation]] from the finding notes and the annexes, each with
   `evals/trigger_evals.json` and `evals/evals.json`; `make validate-skills` and `make eval-skills
   SKILL=…` per skill. Follow `skill-builder` and its cached Anthropic authoring notes; every rule
   ends in a Sources list naming an annex section.
2. **Language skills**: [[skill-go-fuzzing]] (1.27.3), [[skill-python-fuzzing]],
   [[skill-rust-fuzzing]]; verify every command line in a scratch module with the local toolchains
   (Go and cargo are available in the dev container; Atheris and Hypothesis need a venv).
3. **Scripts**: `fuzz_campaign.py` and `fuzz_corpus.py` ([[automation-scripts]]) with the
   recorded-log fixtures and unit tests; `uv lock` for `bin/` only if a dependency is added (none
   planned).
4. **Agent**: `fuzzing_tests_writer.md` per `agent-builder` (mandatory sections, hand-off protocol,
   complexity check) from [[agent-procedure]], the Codex TOML, `techne-fuzz.md`;
   `make validate-claude`; register in `codex.yml`; update the agent-count test and the
   README/CLAUDE.md tables.
5. **Evals**: [[eval-fixtures]], plugin wrapper, graders, headless driver ([[eval-tooling]]); first
   full run against B0 and B1; tune the ◇ defaults on the non-holdout set; record results per
   [[acceptance-criteria]].
6. **Vendor guidance pass**: reconcile the prompt and skills with the current Anthropic sub-agent and
   skill authoring docs, OpenAI's Codex custom-agent format and Google's Antigravity rules format,
   through the existing adapters; the shared core stays provider-neutral.
7. **Deploy and live test**: `make <profile> EXTRA_VARS='--tags ai,claude,codex,agy'`, then
   `make test-live ENGINES=claude,codex`.

## Scope boundaries for the iteration

- The property-based-testing track (Hypothesis, proptest, rapid incl. state machines) is a separate
  piece of work with its own agent and skills; this iteration builds no PBT artefact and the gate
  hands such cases off ([[FTW-D-008-pbt-out-of-scope]]; [[pbt-agent-prompts]] is its starting point).
- Every campaign the agent runs starts from a charter ([[fuzzing-charter]]); the skill, the
  procedure and eval family H enforce it.
- Go toolchain for authoring and verification: `GOTOOLCHAIN=go1.27.3` with
  `GOPROXY=https://proxy.golang.org,direct` (the toolchain is fetched as the module
  `golang.org/toolchain@v0.0.1-go1.27.3.linux-amd64`; `dl.google.com` is not needed).

## Refresh triggers (G.2 §11 SoTA-Echoing)

The annexes are frozen as of 2026-11-03. Refresh when any of: Go custom-mutator proposal #48815
lands; Rust sanitizers stabilise (rust-lang/rust#123617); Hypothesis ships an Atheris backend;
the unreachable paper hosts become readable ([[FTW-OQ-001-unverified-paper-bodies]]); Go 1.28
release notes mention fuzzing.

## Open questions to close along the way

`open_questions/` FTW-OQ-001 … 010; each names the component it blocks.
