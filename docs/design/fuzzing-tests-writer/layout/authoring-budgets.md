---
note_id: "20261111153000"
created: 2026-11-11
modified: 2026-11-12
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: authoring-budget
publication_status: draft
authorship: agent
assistant: codex
project: fuzzing-tests-writer
aliases: ["Authoring budgets"]
tags: [fuzzing, design/component]
related: ["[[agent-procedure]]", "[[reference-documents]]", "[[repository-placement]]", "[[next-iteration]]"]
---
# Authoring budgets and semantic preservation

## Contents

- [Provider evidence](#provider-evidence)
- [Repository rules](#repository-rules-and-measured-headroom)
- [Working size target](#working-size-target)
- [Semantic preservation](#f19-and-a63csc-in-this-authoring-pass)
- [Current measurements](#current-authored-measurements)

Provider evidence was checked on **2026-11-11** and authoring sources rechecked on **2026-11-12**.
Separate discovery metadata, loaded instructions and conditional references. Runtime definitions
now exist; their measured size below does not establish actual model context consumption.

## Provider evidence

| Surface | Current evidence | Meaning for this design |
|---|---|---|
| Portable skills | [Agent Skills specification](https://agentskills.io/specification): name 1–64 characters, description 1–1024 characters; recommends a body below 500 lines / 5,000 tokens | Name/description constraints differ from recommended body size; a short body still needs usable actions |
| Claude skill authoring | [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): keep SKILL.md below 500 lines, link references directly, add contents for references over 100 lines | Keep conditional detail beside its operation; do not turn the historical annexes into loaded instructions |
| Claude discovery | [Skills](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short): listing budget defaults to 1% of context; descriptions can be dropped while names remain; per-entry description plus when_to_use defaults to 1,536 characters | Discovery has its own budget; short descriptions must remain discriminating. Functional descriptions use ordinary discovery; advanced invocation policy is deferred |
| Claude compaction | [Skill content lifecycle](https://code.claude.com/docs/en/skills#skill-content-lifecycle): restores up to 5,000 tokens per recently invoked skill, within a shared 25,000-token allowance | Put essential conditions early and retain durable research evidence outside transient skill context |
| Claude subagents | [Subagents](https://code.claude.com/docs/en/sub-agents): combined custom-agent descriptions above 15,000 tokens warn but still load; skills listed for preloading inject full bodies | Do not assume six small files are cheap when all six are preloaded; choose loading separately from content ownership |
| Codex discovery | [Build skills](https://learn.chatgpt.com/docs/build-skills): default initial listing budget 2% of context, fallback 8,000 characters; descriptions can shorten and skills can be omitted; skills.max_context_tokens supports up to 10,000 tokens | Measure discovery separately from the selected body and references; do not copy Claude's budget or settings |
| Agent body | [Claude subagents](https://code.claude.com/docs/en/sub-agents), [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) | No numerical body line ceiling was established in these pages; the repository's 900-line warning is not a vendor limit |

Claude's YAML/Markdown agent and Codex's TOML agent are different provider surfaces. Shared skill
content uses SKILL.md and local references. [[repository-placement]] records the provider-specific
loading and inheritance choices; [[authoring-validation]] separates format checks from observed
runtime behaviour. Advanced invocation policy and automatic scheduling remain deferred.

## Repository rules and measured headroom

Repository paths below are relative to its root:

- `roles/devbox/files/dot_ai/agents/agent_builder.md`, Quality Validation: under 900 lines is a
  warning convention, with an exception for code-writing agents.
- `roles/devbox/files/dot_ai/agents/skill_builder.md`, Structural/Content Validation: under 500
  lines, direct references, description under 1,024 characters, and contents above 100 lines.
- `roles/devbox/files/dot_claude/bin/validate_config.py`, `check_skill_budget`: estimates listing
  characters after the configured per-entry cap (default 1,536). Without an explicit fixed budget,
  headroom is `BUDGET_UNKNOWN`, because the default allocation is 1% of the runtime model context.
  Invalid settings fail validation; potential truncation or omission is reported as a warning.
  The former fixed 16,000-character/95% error rule has been removed.
- `roles/devbox/files/dot_claude/bin/rules_budget.py`: the 150–200 instruction range is a lexical
  diagnostic heuristic, not a provider limit or an evaluation of agent behaviour.

The cached `skill-builder/references/anthropic-skill-authoring.md` still describes Claude's older
2%/16,000-character model. Current online guidance takes precedence. That unrelated cached guide
was not rewritten by this authoring change. The validator no longer imposes its obsolete hard limit
or requires shrinking unrelated descriptions to make room for the six skills.

Reproduce the scoped check with the repository environment:

```text
.venv/bin/python roles/devbox/files/dot_claude/bin/validate_config.py --root roles/devbox/files/dot_claude --ai-root roles/devbox/files/dot_ai --codex-root roles/devbox/files/dot_codex --check budget
```

`--budget` prints a detailed report but always returns zero; use `--check budget` for its gate result.
The local listing estimate with the six new skills is 15,840 characters. This is an estimate of
metadata, not token consumption or proof of sufficient runtime headroom. Check the configured
Claude session with `/doctor` when assessing actual discovery. [[authoring-validation]] records
complete validation results, including unrelated warnings.

## Working size target

For authored entrypoints, aim for **at most 200 body lines** per agent or SKILL.md; inspect an overrun
before splitting. This is a local working target, not a provider restriction or a new lint rule.
Keep descriptions to one short functional sentence for ordinary provider discovery. The 500/900-line
warnings are upper review boundaries, not targets to fill.

Measure the entrypoint's lines, words and bytes, metadata characters, selected references and the
actual simultaneously loaded combination separately. Use the provider/model tokenizer before
claiming token counts. Moving text to a reference saves context only when it is read conditionally.

## F.19 and A.6.3.CSC in this authoring pass

F.19 keeps the actor, material, operation, result and next use explicit while removing repeated
history and framework narration. A.6.3.CSC compares each shorter operational account with its linked
fuller method for the particular use it must support:

| Short account and source | Retained distinctions | Omitted detail and return |
|---|---|---|
| Agent operation table ← [[fuzzing-charter]], [[stopping-algorithm]] | Reconnaissance versus question-led work; current contribution versus continuing research; authorised scope; pause/closure; new question versus reopening | Detailed state/reopening criteria remain in those notes; return before a transition whose grounds the short account does not settle |
| Campaign operations ← [[stopping-algorithm]], [[corpus-lifecycle]] | Actual resumed operation, accumulated effort, useful inputs and replay, observed result versus next choice | Historical derivations and full retention/reduction conditions remain in the source; read them when reducing, replacing or requalifying inputs |
| Structure/language operations ← [[input-shape-triage]], language facts and [[oracle-ladder]] | Bounds, expected rejection, oracle qualification, original evidence and compatible replay | Engine flags, worked examples and source caveats remain conditional references; consult before relying on version-specific behaviour |

The shortened text carries no stronger effectiveness, coverage, authority or provider claim than
its sources. Changes in reconnaissance policy are substantive amendments supported by [[fpf-framing]],
not omissions excused as compression. No essential execution condition is removed merely to meet
the working size target. References must be directly available in the authored package; vault links
here are design provenance, not assumed runtime paths.

## Current authored measurements

Measured on 2026-11-12. Markdown bodies exclude YAML frontmatter and surrounding blank lines;
the Codex body is `developer_instructions`. Counts are not tokenizer measurements.

| Runtime body | Lines | Whitespace-separated words | UTF-8 bytes | Description characters |
|---|---:|---:|---:|---:|
| Claude agent | 62 | 581 | 4262 | 115 |
| Codex agent | 50 | 545 | 4019 | 115 |
| fuzzing-applicability | 65 | 619 | 4311 | 76 |
| fuzzing-campaign | 89 | 852 | 6117 | 102 |
| structured-input-generation | 62 | 629 | 4575 | 94 |
| go-fuzzing | 87 | 797 | 5871 | 135 |
| python-fuzzing | 93 | 786 | 6289 | 130 |
| rust-fuzzing | 95 | 804 | 6253 | 139 |

All entrypoints fit the local 200-line working target. Claude preloads only applicability and
campaign; the selected language skill and structure skill are read as needed. Codex reads the same
shared entrypoints and relevant references on demand. Four supporting references are linked directly;
none requires the design vault at runtime. Actual simultaneously loaded context remains dependent
on provider behaviour, model and operation; these counts alone do not establish its budget.
