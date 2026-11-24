# Review workspace layout

## Contents

- [Tree](#tree)
- [Who writes what](#who-writes-what)
- [Aliases](#aliases)
- [Facts, review points and evidence](#facts-review-points-and-evidence)
- [Versions and sessions](#versions-and-sessions)
- [Where the review root is](#where-the-review-root-is)
- [Formats of the shared registers](#formats-of-the-shared-registers)

## Tree

Shared artefacts live once at the `AI/` root; everything specific to one drafted comment set
lives in its version folder, so versions sit side by side and can be compared.

```text
ADR-0NN Review/
  ADR-0NN Review.md          human note: ADR link, status, current version, posted links
  AI/
    decisions.md             the user's binding decisions for this review; outrank all criteria
    facts.md                 verifiable facts, each with a checkable reference; must-keep flag
    points.md                review points: claims about the ADR, each naming the facts it rests on
    vocabulary.md            the ADR's own terms, and terms not to import
    sources/
      SOURCES.md             what each snapshot is, where it came from, its page version or SHA
      ADR-0NN-pPP.md         the reviewed ADR at page version PP; immutable
      <related>.md           related documents, context only; immutable
    raw/                     cached API responses and collector outputs; append-only
    scripts/                 read-only collectors
    published/
      comment-vNN.md         what was posted for version NN, with date and comment links
    vNN/                     one folder per version, two digits: v01, v02, …
      HANDOFF.md             current state of the version, rewritten each session
      00-feedback.md         human feedback on v(NN-1), verbatim (absent in v01)
      10-goal.md             goal, decision per feedback point, checks, early/late class
      2N-explore-<topic>.md  exploration reports, one per topic (20, 21, …); only when content changes
      40-comment.md          the comment set: paste note, top comment, replies, inline comments
      41-changes.md          editor's handoff: what changed per goal item, losses, round sections
      5N-review-rN.md        review round N (51-review-r1 … 55-review-r5)
      60-acceptance.md       acceptance
      70-checks.md           checks run before the user sees the draft
      <name>-ticket.md       optional: draft ticket text for details that go to Jira
```

Stage numbers mean the same thing in every version. One comment file per version; no companion
documents.

## Who writes what

| File | Written by | Changed by | Lifetime |
|---|---|---|---|
| `ADR-0NN Review.md` | user | main session, only its "AI review" section | whole review |
| `decisions.md` | goal setter, from the user's words | goal setter; the user | whole review; a decision is superseded by a dated entry, never edited away |
| `facts.md` | main session, from the explorers' proposed facts | main session; goal setter marks facts kept, reopened or dropped on a new ADR page version | whole review; a fact is revalidated when its source changes |
| `points.md` | goal setter (v01), explorers propose rows | goal setter (status per version) | whole review |
| `vocabulary.md` | goal setter | goal setter on a new ADR page version | whole review |
| `sources/*` | main session | never | immutable; a new page version is a new file |
| `vNN/00-feedback.md` | main session, verbatim | never | immutable |
| `vNN/10-goal.md` | goal setter | goal setter, only on a user override | the version |
| `vNN/2N-explore-*.md` | explorer | never after the version | immutable after the version |
| `vNN/40-comment.md` | editor | editor in fix rounds | the version; frozen when the next version opens |
| `vNN/41-changes.md` | editor | editor appends a section per round | the version |
| `vNN/5N-review-rN.md` | reviewer | never | immutable |
| `vNN/60-acceptance.md` | acceptor | never | immutable |
| `vNN/70-checks.md` | main session | main session reruns | the version |
| `vNN/HANDOFF.md` | main session | main session, every session | the version |
| `published/comment-vNN.md` | main session after the user posts | never | immutable |

Agents write only the file their brief names and the registers their contract allows.

## Aliases

File names repeat across version folders. Every Markdown file in the workspace therefore carries
an Obsidian `aliases:` entry that contains the ADR id and a version, so it can be found and linked
by alias. Non-Markdown files in `raw/` carry none.

```yaml
---
aliases:
  - ADR-042 v09 comment
---
```

| File kind | Alias pattern | Example |
|---|---|---|
| Feedback | `ADR-0NN feedback on vMM` (MM = NN − 1, the version the feedback is about) | `ADR-042 feedback on v08` |
| Goal | `ADR-0NN vNN goal` | `ADR-042 v09 goal` |
| Exploration | `ADR-0NN vNN explore <topic>` | `ADR-042 v05 explore code` |
| Comment | `ADR-0NN vNN comment` | `ADR-042 v09 comment` |
| Changes | `ADR-0NN vNN changes` | `ADR-042 v09 changes` |
| Review round | `ADR-0NN vNN review rN` | `ADR-042 v09 review r1` |
| Acceptance | `ADR-0NN vNN acceptance` | `ADR-042 v09 acceptance` |
| Checks | `ADR-0NN vNN checks` | `ADR-042 v09 checks` |
| Handoff | `ADR-0NN vNN handoff` | `ADR-042 v09 handoff` |
| Ticket draft | `ADR-0NN vNN ticket <name>` | `ADR-042 v06 ticket store-access` |
| Published | `ADR-0NN vNN published` | `ADR-042 v09 published` |
| Shared register or note | `ADR-0NN <name> (from vNN)`, where NN is the version in which the file was created, so the alias never changes | `ADR-042 decisions (from v01)` |
| Source snapshot | `ADR-0NN source page PP (from vNN)` | `ADR-042 source page 33 (from v01)` |

Rules:

- The version in an alias is always two digits.
- Links in handoffs and stage files use the path and the alias:
  `[[ADR-042 Review/AI/v09/40-comment|ADR-042 v09 comment]]`. The path part makes the link unique
  although the file name repeats; the alias part is what a reader sees. An agent resolves the
  path part against the review root.
- `40-comment.md` keeps its frontmatter; the paste note says that frontmatter is not posted.

## Facts, review points and evidence

Terms: a **review point** is a claim about the ADR with a proposal (what earlier reviews called a
finding). A **finding** is what the reviewer stage reports about the drafted comment. A
**feedback point** is one item of the human feedback. Keeping three words stops the register of
claims about the ADR from being confused with the review rounds on the comment.

Evidence, facts and review points are linked but kept apart, because they answer different
questions and change for different reasons.

| | Says | Changes when | Lives |
|---|---|---|---|
| Evidence (exploration report) | what was read or run, and what it showed, at a pinned point | never after its version; superseded by a newer report | `vNN/2N-explore-<topic>.md` |
| Fact | one checkable statement, with its reference and the date it was checked | its source changes (A.10.1) | a row in `facts.md` |
| Review point | what the ADR text lacks or gets wrong, and the proposal | the ADR page, the author's answer or the user's decision changes (C.11.DBR) | a row in `points.md` |

One fact supports several review points and one review point rests on several facts. Keeping
each fact once, with its reference and its check date, gives a single place to revalidate when
its source changes (A.10.1), and gives the must-keep check a row to point at. Drift of copied
evidence is prevented by that revalidation trigger and by pinned references: a merged note with
pinned references and a revalidation rule would not drift either; the split's gain is one
revalidation point, not less drift. The
registers link facts and points instead of copying:

- each point row names, by slug, the facts it rests on;
- each fact row names its reference and the points that use it;
- each reference is pinned (a commit, a page version), never a moving branch or "latest";
- a fact used by a point that is still in the comment is **must-keep**: an edit may shorten its
  wording but not drop it or its link without recording the loss in `41-changes.md`. Where the
  code-citation rule (`text-rules.md`, "Claims and evidence") rules out a code link, carrying the
  fact's documentation instead is not a loss.

Write a separate note for one point only when its argument does not fit a register row; link it
from the row.

## Versions and sessions

- A new version starts only with new human feedback on the previous delivered draft. Fixes found
  during a version go into that version's `40-comment.md`.
- The current version is the highest `vNN` folder. The human note's "current version" line is
  updated by the main session when a version opens; if the two disagree, the folder wins and the
  note is corrected.
- One version may span several sessions. `HANDOFF.md` is the version's current state, rewritten
  at the end of each session, with one appended line per session (date, what it established).
- Opening a version: create `vNN/`, save the feedback verbatim with its alias, copy nothing else
  from the previous version; the goal reads the previous comment in place.
- `00-feedback.md` names its author in the frontmatter (`author: user` or the person's name and
  role). Only the user's constraints become rows in `decisions.md`; another reader's points
  become goal items, decided adopt, adapt or reject.

```yaml
---
aliases:
  - ADR-042 feedback on v08
author: user
received: 2026-11-23
---
```

## Where the review root is

The review root is the folder that holds the `ADR-0NN Review/` folders. The main session
resolves it once per session, in the order given in `SKILL.md`, "Start", step 1; agents receive
absolute paths and never resolve it themselves.

## Formats of the shared registers

`decisions.md`, one row per decision:

| Decision | Source | Since | Superseded by |
|---|---|---|---|
| Credentials and access paths stay in Jira, linked from the comment | user, feedback on v03 | v04 | |

`facts.md`, one row per fact:

| Slug | Fact | Reference | Checked | Must-keep | Used by |
|---|---|---|---|---|---|
| `queue-no-dedup` | The current render queue accepts the same request twice | `<repo>@<sha>:<path>:<lines>` with link | 2026-11-20 | yes | `dedup-unstated` |

References are one of: code pinned to a commit SHA, a ticket key with link, an MR link, a
document section anchor, a Confluence page with its page version, a command with its output in
`raw/`. A statement without one stays out of `facts.md`; it may live in an exploration report
marked as an inference.

`points.md`, one row per review point:

| Slug | Claim about the ADR | ADR section | Facts | Proposal | Deadline | Status by version |
|---|---|---|---|---|---|---|
| `dedup-unstated` | The ADR does not say what happens when the same thumbnail is requested twice | Queue | `queue-no-dedup`, `store-overwrite` | State whether duplicates are merged or rendered twice | before acceptance | v05 adopted; v09 adapted |

Status values: `proposed`, `adopted`, `adapted`, `rejected`, `answered by author`, `dropped`, each
with its version.

Slugs are short, readable names. They are working labels: they never appear in posted text.
