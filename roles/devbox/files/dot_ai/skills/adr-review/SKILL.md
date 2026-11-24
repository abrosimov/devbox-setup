---
name: adr-review
description: >
  Runs the iterative review of an architecture decision record (ADR) on Confluence: per
  version, human feedback becomes a goal, then exploration where content changes, editing, a
  bounded review–fix loop and acceptance, ending in a paste-ready review comment of one to three
  Confluence comments that the user posts. Keeps a review workspace with self-contained version
  folders, verifiable facts, binding decisions and per-version handoffs, and dispatches role
  agents for goal, exploration, editing, review and acceptance. Use when the user asks to
  review an ADR, start or continue an ADR review, turn feedback on a review draft into the next
  version, or resume an ADR review in a new session.
disable-model-invocation: true
allowed-tools: Bash(printenv ADR_REVIEW_ROOT), Bash(printenv AION_AUTOPOIESEON), Bash(printenv ADR_REVIEW_VAULT)
problem: "ADR reviews run by hand lost facts in compaction, reversed binding decisions, leaked session labels and imported other ADRs' vocabulary across versions and sessions."
related: [fpf-thinking, jira-text, writing-for-the-reader]
---

# ADR review

Runs one version of an ADR review at a time, in the main session, because only the main
session can talk to the user. Role agents do the stages that need a fresh context or
independence; the files in the review workspace carry the work between roles, sessions and
versions.

Usage: `/adr-review [ADR page URL | review folder] [feedback file] [stage=<name>] [out=<dir>]`.

## Problem

Past reviews failed in recurring ways. Each has a mechanism here:

| Failure | Prevented by |
|---|---|
| A stage reverses a binding decision | `decisions.md` outranks every criterion; a conflicting check is void, never enforced |
| Facts lost when the text is shortened | must-keep facts in `facts.md`; the editor's loss record; the fact-retention check |
| Session labels or working names in posted text | text rules; label and slug scans in the checks stage |
| Terms imported from other documents | `vocabulary.md` and its "do not use" table |
| Restating what the ADR already says | text rule: quote the ADR and argue from it; reviewer check |
| Claims not traced, or contested readings stated as fact | pinned references; inferences marked; contested readings become questions |
| Code cited for things not yet built | the goal records the ADR's kind; the code-citation rule in `references/text-rules.md` |
| Walls of text | the length budget: one to three comments, top comment carries every ask |
| Over-scoped proposals | proposals cut to what the committee decides (C.42) |
| Confusion across versions or between ADRs | one folder per version, aliases, a source check before any stage |
| Context lost between sessions | `vNN/HANDOFF.md`, rewritten every session |

## Contents

- [Problem](#problem)
- [Scope](#scope)
- [Start: find the workspace](#start-find-the-workspace)
- [The loop for one version](#the-loop-for-one-version)
- [Briefing a role agent](#briefing-a-role-agent)
- [Binding decisions come first](#binding-decisions-come-first)
- [Review–fix rounds](#reviewfix-rounds)
- [Checks before the user sees a draft](#checks-before-the-user-sees-a-draft)
- [Reporting and posting](#reporting-and-posting)
- [Sessions and resuming](#sessions-and-resuming)
- [References](#references)

## Scope

| In scope | Out of scope |
|---|---|
| The review comment on one ADR, its versions, and the evidence behind it | Editing the ADR, related ADRs, code, tickets or Confluence pages |
| Workspace files under the review folder | Posting anything; creating tickets (draft their text instead) |
| Asking the user what only the user holds | Defending the user's own earlier ADRs; criticising the chosen approach |

## Start: find the workspace

1. **Resolve the review root once**, in this order, and pass absolute paths to every agent:
   1. a folder or path the user gave in the arguments or the conversation; a path to an
      `ADR-0NN Review/` folder sets the root to its parent;
   2. `ADR_REVIEW_ROOT` (`printenv ADR_REVIEW_ROOT`);
   3. `$AION_AUTOPOIESEON/$ADR_REVIEW_VAULT/Projects/Arch commitee`, only when both variables are
      set and non-empty (`ADR_REVIEW_VAULT` is set per machine in the gitignored devbox overlay
      `roles/devbox/local/`, for example `.config/fish/conf.d/adr_review.fish`).

   `MNEMOSYNE_PERISTASEOS` is only a profile signal (expected `work`); it changes nothing here.
   If none of the three is available, ask the user where the vault and the reviews folder are,
   and use that path for the session. Never guess a path or a vault name.
2. **Find the review folder** `ADR-0NN Review/` under the root from the ADR id or page URL. A new
   review gets the layout in `references/workspace-layout.md`.
3. **Dry run.** With `out=<dir>`, read the review folder as given and write every new or changed
   file under `<dir>` instead, at its path relative to the review root
   (`<dir>/ADR-0NN Review/AI/vNN/…`). Reads look in `<dir>` first, then in the review folder, so
   a dry run sees its own earlier output. Use it for evals, for trying a change, and for a
   workspace another session is editing.
4. **Check the ADR source.** Confirm that `AI/sources/` holds the reviewed ADR at the page version
   the review is about, and that the human note's ADR link points at the same page. A different
   page or a newer page version is reported to the user before any stage runs; a newer version
   reopens only the facts and review points that rest on changed text (A.10.1, C.11.DBR). Fetch pages
   in the main session, which has the Atlassian tools; agents work from the saved snapshot.

**New review (v01).** When no `ADR-0NN Review/` folder exists yet, the main session:

1. creates the folder with the layout in `references/workspace-layout.md`, the human note
   `ADR-0NN Review.md` (ADR link, status, current version), the ADR snapshot in `AI/sources/`
   at its page version, and `AI/sources/SOURCES.md` describing it (and `AI/raw/` for cached API
   responses, if any);
2. seeds `AI/decisions.md` from what the user said in the conversation, one row per stated
   constraint, and asks the user for the reader context (who reads the comment, and any product
   or delivery context that changes what an ask can rest on) if the conversation does not give
   it;
3. opens `v01/` with its `HANDOFF.md` and no `00-feedback.md`, then runs the goal stage.

## The loop for one version

A version is one drafted comment set. A new version `vNN` (two digits) starts only when new human
feedback on the previous delivered draft arrives; fixes found during a version are applied to
that version's comment. The current version is the highest `vNN` folder.

| Stage | Role agent | FPF patterns (read the IDs, do not restate them) | Writes |
|---|---|---|---|
| 0. Open the version | main session | A.15.10 | `vNN/00-feedback.md` (verbatim, with its author; none in v01), `vNN/HANDOFF.md` |
| 1. Goal | `adr-goal-setter` | GOALS.1, GOALS.2, GOALS.7, A.1.STM; C.11.DBR, A.10.1, F.2, C.32.ADA | `vNN/10-goal.md`; updates to `decisions.md`, `vocabulary.md`, `points.md` |
| 2. Explore (only when content changes) | `adr-explorer`, one per topic, in parallel | A.10, C.28.CM; C.32.ADA and C.32.ADR for the ADR itself | `vNN/2N-explore-<topic>.md`; the main session then appends the proposed facts to `facts.md` |
| 3. Edit | `adr-editor` | F.19, A.6.3.CSC, NSTD.1–NSTD.3; EXD.3, C.42 | `vNN/40-comment.md`, `vNN/41-changes.md` |
| 4. Review ↔ fix | `adr-reviewer`, then `adr-editor` | E.23, NSTD.6, C.28.CM; F.13, A.10, C.32.ADR | `vNN/5N-review-rN.md`; fixes in `40-comment.md` and `41-changes.md` |
| 5. Accept | `adr-acceptor` | C.39.WI, C.42; C.41.UA, A.7 | `vNN/60-acceptance.md` |
| 6. Checks | main session | C.41.UA | `vNN/70-checks.md` |
| 7. Hand to the user | main session | PSDA.14 for the report | `vNN/HANDOFF.md`; `published/comment-vNN.md` after the user posts |

What each stage receives, must produce and counts as done: `references/stage-contracts.md`.

The role agents are installed with the skill as `adr-goal-setter`, `adr-explorer`, `adr-editor`,
`adr-reviewer` and `adr-acceptor`; when loaded from a plugin (as in an eval run) their names carry
the plugin prefix, for example `adr-review:adr-editor`. If a role agent is not installed, run that stage inline from its
contract and mark the stage file "performed inline by the main session, not independent". The
reviewer stage is never run inline by the session that edited the text; if no reviewer agent is
available, stop after editing and say so.

`stage=<name>` (`open`, `goal`, `explore`, `edit`, `review`, `accept`, `checks`) runs one stage
on the current version and stops; given a feedback file, `goal` first opens the new version with
it. Without `stage=`, continue from the next operation in `vNN/HANDOFF.md`. A run that ends after
one stage still rewrites `vNN/HANDOFF.md`.

## Briefing a role agent

Every brief carries, and only carries:

- **Objective**: the stage's result for this version, in one or two sentences.
- **Read in this order**: absolute paths, starting with `decisions.md` and `vNN/10-goal.md`.
  The acceptor is the exception: `vNN/40-comment.md` and the ADR snapshot first, read cold, then
  the goal, `decisions.md` and the last review.
- **The user's ask and decisions already made**, quoted or linked; nothing the orchestrator
  thinks would be nice.
- **Write only your output files** (named), plus the shared registers the contract allows.
- **Protected passages**: text that must stay byte-identical, quoted exactly.
- **For re-review**: "changed passages only" plus the earlier findings to check.
- **References**: the absolute path of this skill's `references/` folder,
  `${CLAUDE_SKILL_DIR}/references/` (for example `~/.claude/skills/adr-review/references/`),
  and the stage's section name in `stage-contracts.md`. Agents read from that folder whatever their contract names
  (`stage-contracts.md`, `text-rules.md`, `checks.md`, `workspace-layout.md`,
  `handoff-template.md`, `length-budget.md`, `vocabulary-review.md`).
- **FPF texts**: the absolute path of the FPF references folder and the recipe
  `grep -n '^## <ID> ' <file>`, then read to the next `^## `. Resolve the folder once: the
  sibling skill `${CLAUDE_SKILL_DIR}/../fpf-thinking/references/` (both skills are deployed side
  by side to `~/.claude/skills/` and `~/.gemini/config/skills/`), otherwise
  `~/.claude/skills/fpf-thinking/references/`; if neither exists, say so in the brief. Files:
  `FPF-Spec.md` for every pattern with a letter ID; under `DPFs/`,
  `Management DPF Suite/GOAL-CONSTRUCTION-AND-REGULATION-PRINCIPLES-FRAMEWORK.md` (GOALS),
  `Narrativization-and-Narrative-Studies-Principles-Framework.md` (NSTD),
  `DECISION-DESIGN-PRINCIPLES-FRAMEWORK.md` (PSDA), `EXPLANATION-DESIGN-PRINCIPLES-FRAMEWORK.md`
  (EXD). The FPF skills cannot be preloaded into an agent, so the brief carries the path.

Launch independent explorers in one message so they run concurrently. Wait for all of them
before the next stage, and give the user one consolidated answer, never per-agent fragments.

**Specialist consults (read only).** Beside the explorers, the main session may ask one bounded
question of an existing read-only specialist when a review point turns on its field and the
explorer's domain skills do not settle it: `architect` for a system-level trade-off or an
alternative the ADR did not weigh, `domain-expert` for whether a requirement or assumption holds
in the business domain, `database-reviewer` for a schema, migration or query claim. The brief
carries the question, the ADR snapshot path and the relevant facts, and says the specialist
writes nothing. The main session saves the answer as `vNN/2N-explore-consult-<specialist>.md`
(alias `ADR-0NN vNN explore consult-<specialist>`); an explorer or the reviewer verifies each
claim in it before it becomes a fact. Engineer agents are not used: they carry write and
approval protocols this read-only work does not need.

## Binding decisions come first

`AI/decisions.md` holds the user's decisions for this review, each with its date and source.
They outrank every stage criterion, including the reviewer's and acceptor's checks and the
internal length signals.

- A goal check that conflicts with a decision is invalid; the goal setter must not write one. If
  a stage reports one anyway, the main session marks the check void in `vNN/HANDOFF.md`, removes
  it from later briefs, and names it in the report; it is not fixed by changing the comment.
- A finding that would require breaking a decision is recorded as "conflicts with decision
  <name>" and goes to the user only if it brings evidence the user has not seen; it is never
  must-fix.
- A new decision from the user's feedback is added to `decisions.md` by the goal setter with its
  source, before any other stage of that version runs.

## Review–fix rounds

A round is one review, the fixes, and a re-review of the changed passages against the same
checks. A list of addressed items is not a finished round.

- **Early version**: up to 5 rounds. **Late version**: at most 2.
- Early and late are defined once, in `references/stage-contracts.md`, "Goal" (the class item).
  The goal setter records the class in `10-goal.md`; the user can override it.
- **Acceptance with listed fixes**: the editor applies the acceptor's fixes, then the reviewer
  re-reviews the changed passages only. That pass counts as a round within the bound; if the
  bound is already reached, report the fixes as open instead.
- Stop earlier when no must-fix remains and no proposal is worth its cost (E.23:4.3), after a
  round that closes no finding, or when a fix undoes an earlier one. Stop at the bound and report
  the open findings with their evidence and a recommendation; never narrow the goal's checks to
  declare success.
- A finding that returns after being fixed has a cause the fixes did not reach. Look at the goal,
  the editor's reading of it, or a check that contradicts a decision, and fix that cause.
- In a late version the reviewer reviews the changed passages and their effect on neighbouring
  text only; a new finding outside them needs the reason the earlier review could not have seen
  it.

## Checks before the user sees a draft

Run in the main session and record each answer as yes, no, unknown or not checked (C.41.UA) in
`vNN/70-checks.md`; a check that was not run is never reported as passed (A.7). The list and its
commands: `references/checks.md`. In short:

- text rules: session labels, imported terms, semicolon chains, reviewer "we", unpinned code
  links, security details meant for Jira (`references/text-rules.md`);
- every must-keep fact used by a live review point is still in the comment, with its link;
- every Markdown file of the version has its alias;
- the length budget's reader task holds (`references/length-budget.md`);
- the `jira-text` checker, when that skill is installed; otherwise record "not checked: `jira-text`
  not available" and do the manual subset in `references/checks.md`.

## Reporting and posting

- Talk to the user in the conversation's language; write every file in British English.
- One report per version, after the last agent has returned: outcome first, then the acceptance
  verdict, the open findings with recommendations, "Decisions I made", and "What I need from you"
  only when something is blocked on the user.
- Never report word or character counts to the user. Speak of comments, parts and what a reader
  can do.
- **Nothing is posted by this skill.** Prepare the paste-ready text (and the Confluence HTML
  through the `jira-text` converter when available), name where each part goes, and wait. The
  user posts. After the user says it is posted, write `published/comment-vNN.md` with the posted
  text, the date and the comment links the user gives, and update the human note's AI section.
- Draft ticket text for security-sensitive details in the version folder; creating the ticket is
  the user's action.

## Sessions and resuming

One version may take several sessions. At the end of every session, rewrite `vNN/HANDOFF.md` in
the form of `references/handoff-template.md` and append one session line. On resuming, read
`vNN/HANDOFF.md`, then re-check only the conditions it names as able to change (ADR page version,
new feedback, files edited since). Continue from its next operation; do not redo established
stages. A planned or listed step is not a performed one: inspect its output file before relying
on it.

## References

| File | Read when |
|---|---|
| `references/workspace-layout.md` | Opening a review or a version; any question of where a file goes, its alias, or review points versus evidence |
| `references/stage-contracts.md` | Briefing an agent or running a stage inline |
| `references/handoff-template.md` | Writing or reading `vNN/HANDOFF.md` and stage handoffs |
| `references/text-rules.md` | Editing, reviewing or checking posted text |
| `references/vocabulary-review.md` | Goal stage on a new ADR page version; editing; review |
| `references/length-budget.md` | Goal, editing, review and checks |
| `references/checks.md` | Stage 6 |

`${CLAUDE_SKILL_DIR}` is this skill's directory; give agents the absolute path of a reference
file, not its relative name.
