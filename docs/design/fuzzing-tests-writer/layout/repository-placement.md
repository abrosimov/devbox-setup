---
note_id: "20261103150410"
created: 2026-11-03
modified: 2026-11-12
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

The authored definitions use the existing shared content and provider deployment paths. The table
records source files, not an assertion that either provider has loaded them in a deployed session.
See [[authoring-validation]] for observed checks and remaining qualification.

| Artefact | Authored location or deferred decision |
|---|---|
| Claude Code agent — [[agent-procedure]] | `roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md`: YAML/Markdown, `sonnet`, explicit tools including `Skill`, and two preloaded shared skills |
| Codex agent | `roles/devbox/files/dot_codex/agents/fuzzing-tests-writer.toml`: `name`, `description` and `developer_instructions`; no model or permission override |
| Six shared skills | `roles/devbox/files/dot_ai/skills/{fuzzing-applicability,fuzzing-campaign,structured-input-generation,go-fuzzing,python-fuzzing,rust-fuzzing}/SKILL.md`; portable name/description frontmatter |
| Conditional references — [[reference-documents]] | Four Markdown files under the owning skills' `references/` directories |
| Codex registration | All six skills and `fuzzing-tests-writer` registered in `roles/devbox/defaults/main/codex.yml` |
| Research record — [[automation-scripts]] | Target repository's existing note/artefact convention, guided by `fuzzing-campaign/references/research-record.md`; no checkpoint service or new script |
| Command — [[FTW-D-005-techne-fuzz-command]] | Deferred; no `techne-fuzz` command, custom trigger, hook or scheduler |
| Behavioural evaluation fixtures — [[eval-tooling]] | `tests/fuzzing_agent_evals/` remains a proposal; full evaluation is not established by authoring checks |
| Method and validation | `docs/design/fuzzing-tests-writer/`, including [[authoring-budgets]] and [[authoring-validation]] |

Claude preloads `fuzzing-applicability` and `fuzzing-campaign`; the agent loads the selected language
skill and structured-input skill when needed. Codex instructions require reading those shared skill
entrypoints and only the references needed for the operation. The runtime files do not depend on
vault wikilinks or on loading the FPF corpus. The existing deployment routes shared content to
Claude's `~/.claude/agents/` and `~/.claude/skills/`, and registered Codex content to
`~/.codex/agents/` and `~/.agents/skills/`.

Claude leaves `permissionMode` unset; Codex supplies no permission override. Functional descriptions
support ordinary provider discovery. Advanced invocation conditions and routing remain a separate
decision. Current provider evidence and the corrected context-dependent discovery check are in
[[authoring-budgets]]. Neither format implies a new authority to install, publish or deploy.

The persistent research record belongs to the target repository. Sessions recover its question,
method and unfinished operation rather than inventing a fresh identity on each invocation.
No deployment or home configuration change was made; the user will deploy `personal`. Gemini is
outside delivery scope.
