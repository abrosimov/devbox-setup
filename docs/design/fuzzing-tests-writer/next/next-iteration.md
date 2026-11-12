---
note_id: "20261103150800"
created: 2026-11-03
modified: 2026-11-12
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

The methodology has been authored as two provider agent definitions and six shared skills. The
2026-11-11 lifecycle correction, bounded new-corpus reconnaissance and FPF operation contracts
remain the method basis. [[authoring-validation]] records the exact checks performed; authoring
and static validation do not establish general effectiveness or cross-session correctness.
No stage creates PBT or mutation-analysis work.

| Stage | Current result | Evidence and remaining boundary |
|---|---|---|
| Methodology | Specified | F.0.2.MA allocation, C.39 Case 5, SYSE.47/48 contracts and F.19/CSC preservation checks |
| Provider authoring | Authored | [[repository-placement]] lists both agent formats, six portable skills, four local references and Codex registration; [[authoring-budgets]] records size/loading rules |
| Focused local qualification | Recorded separately | [[authoring-validation]] distinguishes parsing, deployment/loader checks and isolated language observations from untested behaviour |
| Invocation — separate user decision | Advanced policy deferred | Ordinary provider discovery uses functional descriptions; no custom command, trigger, hook, routing rule or scheduler |
| Behavioural qualification | Incomplete | Full cross-session recovery, pause/closure/reopening and held-out comparison still require independent records under [[acceptance-criteria]]; Python/Rust runtime checks remain unperformed |
| Personal deployment | User-owned, not performed | The user will deploy `personal`; source registration is not evidence of an installed or working provider session |

## Provider basis and qualification

Authoring used current official [Claude Code subagent](https://code.claude.com/docs/en/sub-agents)
and [skill](https://code.claude.com/docs/en/skills) guidance, and the Codex
[agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents) and
[skill](https://learn.chatgpt.com/docs/build-skills) documentation. Keep the dated rules and their
limits in [[authoring-budgets]], rather than translating Claude frontmatter into Codex fields by
analogy. Runtime loading, permission inheritance and provider-specific continuation need evidence
separate from source format checks.

The local discovery validator now reports context-dependent headroom as unknown when no fixed
budget is supplied; it no longer treats 16,000 characters as a universal fatal limit. This does
not prove every skill description will appear in every model context. Compact bodies and direct
conditional references keep essential operations available without loading the research vault.

## Finite progression

For a qualification experiment, recover its question, method, evidence and unfinished operation;
perform the smallest operation that can resolve the current claim at proportionate cost. A new
corpus can form a question without predicting its usefulness. Closure, pause and selective reopening
follow [[stopping-algorithm]]; a mandatory cross-session wall-clock or supervisor gate remains
withdrawn. A configuration-loading check cannot substitute for observed research behaviour.

No commit, deployment, home change or external publication is part of the current authoring result.
Further qualification should address named claims, not restart the broad survey or exhaust every
historical unknown.

## Open questions

The `open_questions/` notes retain FTW-OQ-001–011. Each records whether it blocks an actual claim,
is conditional, is nonblocking, or is excluded. Do not reopen excluded questions or harvest more
papers merely because a historical research note contains an unknown.
