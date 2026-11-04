---
note_id: "20261103150410"
created: 2026-11-03
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: placement
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Repository placement"]
tags: [fuzzing, design/component]
related: ["[[system-characterisation]]", "[[next-iteration]]"]
---
# Repository placement

| Artefact | Path |
|---|---|
| Agent (Claude/Gemini source) — [[agent-procedure]] | `roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md` |
| Agent (Codex adapter) | `roles/devbox/files/dot_codex/agents/fuzzing-tests-writer.toml` |
| Command ([[FTW-D-005-techne-fuzz-command]]) | `roles/devbox/files/dot_ai/commands/techne-fuzz.md` |
| Skills | `roles/devbox/files/dot_ai/skills/{fuzzing-applicability,fuzzing-campaign,structured-input-generation,go-fuzzing,python-fuzzing,rust-fuzzing}/` |
| Reference documents ([[reference-documents]]) | `<skill>/references/` |
| Scripts ([[automation-scripts]]) | `roles/devbox/files/dot_claude/bin/fuzz_campaign.py`, `fuzz_corpus.py` (+ tests) |
| Eval fixtures and plugin wrapper ([[eval-tooling]]) | `tests/fuzzing_agent_evals/` |
| Codex shared-skill registration | `roles/devbox/defaults/main/codex.yml` |
| This vault | `docs/design/fuzzing-tests-writer/` |

Deploy path after authoring: `make <profile> EXTRA_VARS='--tags ai,claude,codex,agy'`, then
`make test-live ENGINES=claude,codex`.
