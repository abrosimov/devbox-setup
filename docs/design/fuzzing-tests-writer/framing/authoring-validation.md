---
note_id: "20261112120000"
created: 2026-11-12
modified: 2026-11-12
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: authoring-validation
publication_status: draft
authorship: agent
assistant: codex
project: fuzzing-tests-writer
aliases: ["Fuzzing authoring validation"]
tags: [fuzzing, design/framing]
related: ["[[agent-procedure]]", "[[authoring-budgets]]", "[[repository-placement]]", "[[next-iteration]]"]
---
# Authored assets and qualification evidence

Two provider definitions and six shared skills now implement the accepted methodology. This note
records local qualification on 2026-11-12. The user will deploy to personal; no deployment, live-home
configuration update, commit or publication was performed in this authoring pass.

## Installed shape

Paths below are relative to the repository root:

- Claude Code: `roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md`.
- Codex: `roles/devbox/files/dot_codex/agents/fuzzing-tests-writer.toml`.
- Shared skills under `roles/devbox/files/dot_ai/skills/`: `fuzzing-applicability`,
  `fuzzing-campaign`, `structured-input-generation`, `go-fuzzing`, `python-fuzzing`, `rust-fuzzing`.
- Codex registration: `roles/devbox/defaults/main/codex.yml`. Claude's existing shared-asset
  deployment picks up the new files without an additional task.

The Claude definition follows the repository's writer-role `sonnet` choice and preloads only
applicability and campaign. Its other skills and their references load when needed. The Codex
definition inherits its parent model, permissions and tools, and explicitly reads the relevant
skills. Neither definition overrides approval policy. Ordinary names and functional descriptions
support provider discovery; advanced invocation conditions, routing, commands and scheduling remain
deferred. PBT and mutation analysis are excluded.

Provider contracts were refreshed against [Claude subagents](https://code.claude.com/docs/en/sub-agents),
[Claude skills](https://code.claude.com/docs/en/skills),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) and
[Codex skills](https://learn.chatgpt.com/docs/build-skills). In particular, full preloaded skill
bodies differ from discovery descriptions, and native Codex role TOML differs from Claude YAML/Markdown.
See [[authoring-budgets]] for the size policy and discovery-budget correction.

## Structural and documentation checks

- All six skill entrypoints passed the skill creator's structural validator.
- The repository configuration validator checked 30 agents, 51 skills and 22 commands: zero errors.
  Two warnings remain: context-dependent discovery headroom (`BUDGET_UNKNOWN`, local listing
  estimate 15,840 characters) and the pre-existing unreferenced `response-templates` trigger warning.
  Neither is evidence that every description fits the eventual runtime model.
- The design corpus check parsed 83 YAML frontmatters, preserved existing IDs, found 83 unique IDs
  and resolved 973 wiki links. `git diff --check` passed.
- Agent bodies are 62 lines for Claude and 50 for Codex; skill bodies are 62–95 lines. Four
  directly linked supporting references hold conditional detail. These are source measurements,
  not tokenisation or an effectiveness result.
- Focused validator and Codex asset tests passed: 101 tests (91 validator tests and 10 asset tests).
  An earlier full deployment run passed 367 tests and failed two expected-agent-set assertions
  while that list was still being updated. Both assertions passed in the final 10-test asset run;
  the remaining 359 deployment tests had already passed and were not rerun.
- Ruff lint and format checks passed for the three changed Python files.

Actual discovery/loading of the new assets by standalone Claude Code and Codex CLI sessions was
not established. Native file contracts and repository registration are checked; source presence
must not be reported as observed provider loading. The user's personal deployment and a subsequent
fresh provider session remain separate evidence.

## Native Go procedure trial

A temporary Go 1.24.0 fixture at `/private/tmp/fuzz-language-smoke.7u15mS` uses a byte-to-hex-to-byte
round-trip assertion. It is a tool/procedure fixture, not a real-project applicability or bug-yield
benchmark. Commands used `GOTOOLCHAIN=local`, `GOPROXY=off` and fixture-local build/module caches.

- Initial ordinary replay passed both built-in seeds.
- A native search with `-fuzztime=2s -fuzzminimizetime=1s -parallel=1` exited zero, reporting
  88,639 executions, seven new interesting inputs and nine total inputs. These search counters
  were observed by the authoring worker; the later research record attributes them rather than
  pretending to hold the raw search log.
- An independent fresh-context agent read the authored Codex definition and relevant skills. It
  copied all seven generated records unchanged from the search cache into `testdata/fuzz/FuzzDecode`,
  preserved the originals and verified byte equality.
- `go test . -run '^FuzzDecode$' -count=1 -v` then explicitly ran all nine cases successfully.
  Package-reported replay time was 0.343 seconds; the log is `replay.log` in the fixture.
- The agent checked the installed hex API contract and wrote `FUZZING_RESEARCH.md`, closing the
  corpus-retention/replay question as `CLOSED — ANSWERED`, with input hashes and observation limits.
- A second fresh-context agent recovered that record, verified unchanged harness, toolchain,
  corpus and original/copy identities, and inspected the previous replay evidence. It preserved
  the supported closure without starting another replay or search. Only its resumption note changed.

The two fresh contexts received the actual role and skills, not the parent conversation or the
expected disposition. They exercise corpus retention and closed-question recovery in this host's
agent runtime; they do not establish Claude-specific model behaviour or a comparative improvement.
Temporary evidence remains usable only while the fixture directory exists. Its hashes and commands
are recorded there; no durable external archive or publication is implied.

## Qualification limits

No Atheris execution or cargo-fuzz execution was performed: Atheris was absent from the repository
environment and cargo-fuzz/a compatible installed nightly were unavailable. The Python and Rust
instructions were checked against current primary sources and local structural checks; their actual
engine execution remains unqualified on this machine. No dependencies or toolchains were installed.

No held-out comparative evaluation, long-lived PAUSED-operation recovery, real-project defect yield,
new-corpus branching evaluation or full provider/model behavioural matrix has been completed. Those
limits do not prevent deploying the authored definitions for initial use; they prevent claiming that
the earlier failed projects' research behaviour has already been solved empirically.

The source worktree remains uncommitted. The user's existing deployment entrypoint is `make personal`;
running it and inspecting the installed configuration belongs to the user's deployment step.
