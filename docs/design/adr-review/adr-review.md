---
aliases: ["adr-review design"]
tags: [design]
status: v0
---
# `adr-review` skill — design summary (v0)

The public summary of the design behind `roles/devbox/files/dot_ai/skills/adr-review/` and its
five role agents (`dot_ai/agents/adr_*.md`). The full design record (goal, exploration, option
sets, comparisons, self-check, fix rounds) and the evals built from past reviews stay in the
private work vault, because they quote internal architecture documents, tickets and code.

## What it is

A user-invoked skill that runs the iterative review of an architecture decision record in the
main session: per version, human feedback becomes a goal, then exploration where content
changes, editing, a bounded review–fix loop and acceptance, ending in one to three Confluence
comments that the user posts. Role agents do the stages that need a fresh context or
independence; files in a review workspace carry the work between roles, sessions and versions.

## Decisions (each a supported direction; the private record holds the comparison)

| Choice | Decision | Reason |
|---|---|---|
| Packaging | Skill in the main session plus five role agents; a missing agent degrades to an inline stage marked "not independent" | Only the main session can talk to the user; the reviewer must not be the editor |
| Explorer | Dedicated read-only `adr-explorer` that reads named domain skills; bounded read-only consults with `architect`, `domain-expert`, `database-reviewer` | Engineer agents carry write and approval protocols a read-only task does not need |
| Evidence and review points | Kept apart and linked by slug: exploration reports per version, `facts.md` (pinned references, must-keep flag), `points.md` | One revalidation point per fact, and rows for the must-keep check; drift itself is prevented by pinned references and revalidation |
| Versions and sessions | Self-contained `vNN/` folders, a new version only on new human feedback, `vNN/HANDOFF.md` rewritten each session | Stale pointers and undecided version numbers in manual reviews |
| Aliases | Every workspace Markdown file has an Obsidian alias with the ADR id and a version | File names repeat across version folders |
| Length budget | One to three comments; the top comment alone carries every ask with its deadline; counts never reported | A numeric cap once reversed a "no length limit" decision |
| Binding decisions | `decisions.md` outranks every stage criterion; a conflicting check is void | A review stage once enforced a check the user had ruled out |
| Code citations | Code is cited only when the ADR (or the part) covers implemented behaviour | An ADR is an architecture document |
| Review root | Explicit path → `ADR_REVIEW_ROOT` → `$AION_AUTOPOIESEON/$ADR_REVIEW_VAULT/Projects/Arch commitee` → ask the user | The vault location differs per machine; `ADR_REVIEW_VAULT` is set per machine in the gitignored overlay `roles/devbox/local/` |
| Loop control | Up to 5 review–fix rounds early, at most 2 late; "late" defined in the Goal contract | Context loss and scope growth in long late loops |

## Evals

Repository convention: content evals in `evals/evals.json` (skill-creator format, validated by
`make validate-skills`); no `trigger_evals.json`, because the skill is user-invoked only
(`disable-model-invocation: true`) and never triggers on its own, so `make eval-skills` has
nothing to run for it. The four content evals use invented material under `evals/files/`.

The `claude plugin eval` suite designed alongside the skill (deterministic graders, regression
and held-out folders) is not ported: a plugin root must contain both the skill and its agents,
which this repository keeps apart in `dot_ai/skills/` and `dot_ai/agents/`, and most of its cases
are built from internal material. It stays runnable from the private staging folder, which has
its own plugin manifest. Eval harness choice for this repository remains open, as for
`docs/design/fuzzing-tests-writer/decisions/FTW-D-004-evals-as-plugin.md`.

## Not yet done

No eval run, no pilot on a live ADR, no Codex agents (planned for the hardening stage).
