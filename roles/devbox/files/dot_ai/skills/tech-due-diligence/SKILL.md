---
name: tech-due-diligence
description: >
  Writes an initial technical due diligence (DD) of a company's or vendor's technology from
  sell-side material (a pitch deck, an architecture or vendor presentation) plus public sources,
  for non-technical decision makers. Covers the document skeleton, the vocabulary of findings and
  ratings, claim-to-source discipline, staged checks by an independent statement checker, and
  bounded review rounds. Technology only, and no remedies: only what to check, ask or start
  first. Use when asked to review a deck's technology slides for an investor, buyer or board,
  to say what to check first in a vendor's architecture presentation, or to write or continue an
  initial tech DD from such materials. Also use when correcting or re-checking statements in an
  existing DD draft — even a single sentence, as this skill holds the strength rules that stop a
  statement outrunning its source.
problem: "Initial technical due diligence ran late: statements came out stronger than their sources, the document's shape was settled after the body, and checks ran at the end."
related: [adr-review, fpf-thinking, narrative-thinking, writing-for-the-reader]
---

# Initial technical due diligence

Writes, in the main session, an initial technical DD for readers who will not read the
technology themselves: a board member, an investor, non-technical consultants. The document says
what the material shows about the technology, what it does not show, and what to check, ask or
start first. The independent checks run through the `statement-checker` agent; the briefs for it
are in this skill.

Arguments: a deck file or an existing DD folder, and optionally `step=<n>` to run one stage. On
Claude Code the `/techne-tech-dd` command collects the reader, deal type and DD stage first; on
other engines, load this skill and give the same arguments in the request.

## Contents

- [Problem](#problem)
- [Scope](#scope)
- [Start: the workspace](#start-the-workspace)
- [Rules for every sentence](#rules-for-every-sentence)
- [The stages](#the-stages)
- [Dispatching the statement checker](#dispatching-the-statement-checker)
- [Handling review findings](#handling-review-findings)
- [Rounds and the stop criterion](#rounds-and-the-stop-criterion)
- [Reporting and delivery](#reporting-and-delivery)
- [References](#references)

## Problem

| Failure mode | Prevented by |
|---|---|
| Sentences outrun their sources and each one costs a review round | evidence rules; the claim-to-source pass; the statement check before the owner sees a draft |
| The document's shape is settled only after the body exists | stage 2: skeleton and formatting rules fixed before any writing |
| What the business must know is buried | the top block on page one; stage 9 checks it |
| Text extracted from slides misses what only their pictures show | stage 1: slides read as images, with a per-slide list of expected visuals |
| Cached web pages give out-of-date readings | the date rules in `references/evidence-rules.md` |
| A reviewer's mistake is taken as fact | a reviewer is not a source of truth; new facts are verified again |
| A claim already corrected comes back in new text | the register of corrected claims |
| Totals, counts and formulas stop agreeing after fixes | stage 7, repeated after every fix round |
| Independent checks run only at the end | the stage order below |

## Scope

| In scope | Out of scope |
|---|---|
| Technology: components, hosting, data location, dependencies, upkeep, monitoring, security posture as far as the material and public sources show | The deal, price, revenue, the team's composition or history, management |
| What to check, ask or start first, with the stage each step is doable at | Remedies, fixes, recommendations on how to rebuild |
| The markdown source of the document and its working files | Editing the delivery format (for example a shared online document) in place; that is a separate step with its own tooling |
| Public sources read in this session | Logging in to any system, using credentials, changing anything |
| Legal facts as questions for counsel | Legal conclusions |

A later-phase DD with access to systems and code is outside this skill's model: the vocabulary
below assumes the material reaches the "named" level only. Say so if asked to run it there.

## Start: the workspace

1. **Find or create the DD folder** the owner names. It holds client material, so it is never a
   tracked path in a repository; if it sits inside one, confirm it is ignored and never stage it.
   Layout and what each file holds: `references/check-stages.md`, "Workspace".
2. **Seed `decisions.md`** from the conversation: reader, deal type, DD stage, document language,
   word budget for main sections, deadline, and every rule the owner states. Each row carries its
   date and source. Decisions outrank every stage criterion and every reviewer.
3. **Ask only what is missing and only the owner holds**: who reads the document and what they
   must decide; the deal type (investment, acquisition, vendor selection, partnership), because it
   sets which consequences matter to the business; the DD stage. Ask in one batched round with a
   recommended answer each.
4. **Open `corrected-claims.md`** (the register) and `checks.md` (the check record) empty.

The document is written in the language its reader needs; the conversation with the owner may be
in another. Working files are in British English.

## Rules for every sentence

The full rules, with draft and acceptable forms: `references/evidence-rules.md`. The core:

- **Every number and every fact has a source**: a slide number, or a link with the date the page
  was read. A publication date does not replace the read date.
- **No statement stronger than its source.** "The deck says X" is safe; "X is the case" is not.
  Nobody has seen the running system, so the deck reaches only the "named" level
  (`references/vocabulary.md`).
- **A claim about a slide counts only if the slide's image was seen.**
- **Observations are stated with their known context**; neither assert nor guess a cause. Where a
  cause matters, offer rival explanations with the observation that tells them apart.
- **Events after the source's last-saved date are not evidence of the authors' neglect.**
- **No labels** such as [Stated] or [Inferred] and no self-description of the document. A note
  that a source could not be opened stays, with the date of the attempt.
- **Terms**: a term is explained where it first appears, and that first mention links to the
  glossary.
- **One object, one name** across the whole document.
- **Unconditional legal conclusions become a question for counsel.**
- **Add a question or a check only if a plausible answer would change what is checked first.**
- **Every "first step" points to a concrete check, request or question**, doable at its stage, and
  breaking no check rule (no credentials, no changes to anyone's system).

## The stages

Run in this order. Each stage's inputs, outputs and done condition, with the FPF patterns to pass
in briefs: `references/check-stages.md`.

| Stage | Who | Writes |
|---|---|---|
| 1. Read the deck | main session | `source/slides/`, `source/media/`, `source/visuals.md`, `source/deck-meta.md` |
| 2. Fix the skeleton and formatting rules | main session | `dd.md` headings and placeholders; `decisions.md` rows for format |
| 3. Draft the top block and findings table | main session | top block and summary in `dd.md`; `sources.md` |
| 4. Draft the body and appendices | main session | the rest of `dd.md` |
| 5. Claim-to-source and rating-definition passes | main session | fixes in `dd.md`; `changes.md`; `checks.md` |
| 6. Statement check of top block and summary | `statement-checker` | `reviews/NN-statement-check-rN.md` |
| 7. Tables and formulas reconciliation | main session | `checks.md`; fixes in `dd.md` |
| 8. Fresh-eyes review with a missed-items pass | `statement-checker` | `reviews/NN-fresh-eyes-rN.md` |
| 9. Links, and are the critical points at the top | main session | `checks.md` |

- **Stage 1** renders every slide to an image and extracts embedded pictures; slide rendering
  stays in the main session, and the checker reads the images. Look at every image. Record the deck
  file's last-saved date from its metadata, and keep a per-slide list of the visuals a reader
  would expect (diagram, screenshot, table, chart) with whether each was seen.
- **Stage 2** comes before any prose: the skeleton (`references/document-skeleton.md`), the
  rating definitions, table formats and pagination rules. Late shape changes cost the most rework.
- **Stage 3** delivers what the business reads first. The owner may see the top block and
  findings table once stage 6 has passed on them; the body and appendices (stage 4) follow.
- **Stage 7** repeats after every fix round, since a fix in one place moves totals elsewhere.
- **Deadline facts are re-read on every edit day**: end-of-support dates, retirement dates,
  announced regions and anything else that changes with the calendar.

`step=<n>` runs one stage and stops; without it, continue from the first stage whose done
condition in `checks.md` is not met. A planned stage is not a performed one: inspect its output
before relying on it.

## Dispatching the statement checker

Two uses, each with its brief in `references/check-stages.md`:

- **Statement check** (stage 6): every statement of the top block and the summary, labelled,
  checked against the slides, the public sources and the document's own sections.
- **Fresh eyes** (stage 8): deck against document, statement by statement, plus a "missed from the
  deck" pass that lists what the slides show that the document does not use.

Every brief carries: the mode; the absolute paths of the document, the labelled statements, the
deck file, the rendered slides and `source/media/`; `sources.md`; `corrected-claims.md`, with the
instruction to flag any proposed wording that reintroduces a corrected claim; the report path;
today's date; the owner's decisions that bear on the check; and the FPF texts path and recipe from
`references/check-stages.md`, "FPF texts". Nothing else: an idea added to a brief becomes work.

Dispatch the agent named `statement-checker` (if the engine lists it under a prefixed name, use
that). If no such agent is available, run the stage inline from its brief and mark the report
"performed inline by the main session, not independent"; say so in the report to the owner. Run
stages 6 and 8 by separate dispatches, so the fresh eyes are fresh.

## Handling review findings

A reviewer is not a source of truth, the checker included.

- **Two verdict sets, kept apart.** The checker gives each statement confirmed, weaker form,
  wrong (the source contradicts it) or could not verify (the source does not settle it or could
  not be opened). The main session then triages each finding as accept, partial or reject, with
  what was opened to decide it (slide image, page and read date, document section). Record both
  in `reviews/NN-<kind>-rN-triage.md`.
- **A reviewer's proposed wording passes the same strength check** as the original.
- **A claim from a reviewer's memory is rejected as unverified.** Any new fact a reviewer adds is
  verified again before it enters the document.
- **Change only the claim the finding touches, and keep its strength**: "may" is not "is"; "not
  stated" is not "absent". Strengthening a claim needs the owner's go.
- **Propagate every change** to the summary, findings table, body, appendices, glossary and every
  counter that depends on it.
- **Log each change in `changes.md`** as changed, added, removed, weakened or strengthened, with
  its basis.
- **Add each corrected claim to `corrected-claims.md`** (old wording, corrected wording, basis)
  and check all new text, reviewers' drafts included, against the register.
- **Edits by others found between reads are preserved** and reported to the owner; never
  overwrite them silently.

## Rounds and the stop criterion

A round is one review, the fixes, and a re-check of the changed passages against the same checks,
with stage 7 run again. At most three fix rounds per review kind; stop earlier after a round that
closes no finding, or when a fix undoes an earlier one.

Stop when all of these hold:

- every finding has a triage verdict;
- no strengthening went in without the owner's go;
- counters, totals and links agree (stage 7 and stage 9 answered "yes");
- the word budget for the main sections holds.

The word budget does not block new material the owner asks for. A cut that would remove a needed
distinction is refused and reported, not made. No new review round starts unless the owner asks.

Record every check in `checks.md` as yes, no, unknown or not checked (C.41.UA); a check that was
not run is never reported as passed.

## Reporting and delivery

- Reports to the owner follow the `writing-for-the-reader` skill. DD-specific content: one report
  per stop, after every dispatched agent has returned, giving what the document now says at the
  top, the triage verdicts that changed it, and open findings with a recommendation each; never
  report word or character counts.
- `dd.md` is the source of truth for the text. Bringing the delivery format in step with it is a
  separate step with its own tooling; this skill does not describe it.
- The header carries the date, not a version number or "draft"; version history lives outside the
  text.

## References

| File | Read when |
|---|---|
| `references/document-skeleton.md` | Stage 2; any question of where content goes or how it is formatted |
| `references/vocabulary.md` | Stages 2–5; rating a finding; defining the ratings in the document |
| `references/evidence-rules.md` | Writing or changing any sentence; stage 5; handling a finding; the "words to distrust" checklist |
| `references/check-stages.md` | Running any stage; briefing the checker; the workspace layout |

Reference paths are relative to this skill's own directory (on Claude Code,
`${CLAUDE_SKILL_DIR}`; on other engines, the folder this SKILL.md was loaded from). Give agents
the absolute path of a reference file, not its relative name.
