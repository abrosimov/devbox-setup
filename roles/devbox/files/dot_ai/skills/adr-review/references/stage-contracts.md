# Stage contracts

What each role receives, what it must produce, and when it is done. Patterns are named by ID;
read their text when the stage needs more than the checks below. The brief gives the absolute
path of the FPF references folder (SKILL.md, "Briefing a role agent"): `FPF-Spec.md` holds every
pattern with a letter ID; `DPFs/` holds GOALS
(`Management DPF Suite/GOAL-CONSTRUCTION-AND-REGULATION-PRINCIPLES-FRAMEWORK.md`), NSTD
(`Narrativization-and-Narrative-Studies-Principles-Framework.md`), PSDA
(`DECISION-DESIGN-PRINCIPLES-FRAMEWORK.md`) and EXD (`EXPLANATION-DESIGN-PRINCIPLES-FRAMEWORK.md`).
Recipe: `grep -n '^## <ID> ' <file>`, then read from that line to the next `^## `. If the brief
says the folder is unavailable, work from the checks below and say so in the stage file.

## Contents

- [All stages](#all-stages)
- [Goal](#goal)
- [Explore](#explore)
- [Edit](#edit)
- [Review](#review)
- [Accept](#accept)
- [Checks and hand-over](#checks-and-hand-over)


## All stages

- Read `decisions.md` first. A decision outranks this contract.
- Write only your output files, each with its alias. Stage files use the handoff form of
  `handoff-template.md`; `40-comment.md` (the comment set) and `00-feedback.md` (verbatim
  feedback) are exempt from that form. Touch the shared registers only where the stage's section
  allows it.
- Write working files in British English. Working labels (slugs, check names, finding numbers)
  are fine there and never reach posted text.
- A fact without a checkable reference is an inference and is marked as one.
- A planned, proposed or listed step is not performed work (A.7). Say "proposed" or "not run"
  when that is the truth.
- Return to the orchestrator: outcome, file written, the decisions you took with their reasons,
  and open items that pass the stop list with a recommended answer. No questions to the user; the
  orchestrator holds the user's context. A handoff grants no authority: a stage acts only within
  its contract and its brief.

## Goal

**Agent** `adr-goal-setter`. **Patterns** GOALS.1, GOALS.2, GOALS.7, A.1.STM (decided); C.11.DBR,
F.2, C.32.ADA (adopted).

**Reads** `decisions.md`, `vNN/00-feedback.md`, the previous `40-comment.md`, the ADR snapshot,
`points.md`, `facts.md`, `vocabulary.md`, the human note.

**Produces** `vNN/10-goal.md` with:

1. **Purpose**: who reads the comment, on which page, and what they must be able to do after it
   (A.1.STM: use first, then the committee's acceptance work it serves). Reader context that
   changes what a criterion means goes here (for example, a product installed on customers'
   hardware changes what exit criteria can rest on).
2. **The reviewed ADR**: title, page id, page version; related documents named as context only.
   Its **kind**: it describes or changes an implemented system, it proposes something not yet
   built, or it is mixed, naming which parts are which. The kind decides where the comment may
   cite code (`text-rules.md`, "Claims and evidence").
3. **Kind of goal** (GOALS.1:4.2) and **class**, with the reason. This is the one definition of
   the class: a version is **late** when its goal is a point edit, meaning the feedback on the
   previous version names passages to change, adds no new review point and asks for no
   reorganisation; or when the user (not another reader) called the previous draft publishable
   and the feedback asks for no reorganisation. A reorganisation request always makes the version
   early; v01 is early. Every other version is early. The round bounds that follow from the class
   are in SKILL.md, "Review–fix rounds".
4. **Decision per feedback point**: adopt, adapt or reject, each with its reason grounded in the
   ADR text, a fact or a decision. Every point gets a row; none is silently dropped. Quote the
   feedback point briefly so the row reads on its own.
5. **What must be preserved**: decisions in force, must-keep facts used by live review points,
   protected passages quoted exactly, what the previous version did well per the feedback.
6. **Achievement checks** (GOALS.2:4.2): each observable in the next comment, each with the
   failing case it catches. Challenge each: could it pass while the goal is missed? Revise until
   it could not.
7. **Non-goals**: what this version will not change.
8. **Next operation**: which stages run, and whether exploration is needed (only when content
   changes).

**Feedback author**: only the user's constraints become rows in `decisions.md`; points from any
other reader become goal items with a decision (adopt, adapt, reject). The author is in the
frontmatter of `00-feedback.md`.

**May update** `decisions.md` (new decisions from the user's feedback, with source and version),
`vocabulary.md` (on v01 and on a new ADR page version, harvested with F.2, with the terms not to
import), `points.md` (status per version; on v01, the initial rows, seeded from a C.32.ADA
evaluation of the ADR: every coordinate, no averaging, each weak one with its repair), and
`facts.md` (kept, reopened or dropped, on a new ADR page version).

**Checks the source pointers**: the ADR snapshot, the human note's link and the brief name the
same page; a mismatch is an open item, never resolved by guessing.

**On v01** there is no `00-feedback.md`: the goal starts from the ADR, `decisions.md` and the
reader context the main session gathered, and the decision-per-feedback-point section is empty.

**Must not** write a check that conflicts with a decision. A numeric size cap is never a check;
the length budget is structural (`length-budget.md`). On a new ADR page version, compare the
facts and review points that rest on changed text (C.11.DBR) and mark each kept, reopened or dropped.

**Done when** every feedback point has a decision, every check names its failing case, and no
check conflicts with `decisions.md`.

## Explore

**Agent** `adr-explorer`, one instance per topic (code, documents and tickets, tests,
operations), in parallel. **Patterns** A.10, C.28.CM; C.32.ADA when the topic is the ADR's own
adequacy.

**Reads** the goal's exploration questions, the ADR snapshot, the domain skills its brief names,
the repositories and sources its brief names (read only).

**Produces** `vNN/2N-explore-<topic>.md`: each question, what was read or run, the result, and
the reference pinned. A pinned reference contains: for code, the repository, the full commit SHA,
the path and the lines, with a permalink; for Confluence, the page id, the page version and the
section anchor; for a ticket or MR, its key or number with its link; for a command, the command
and its output saved under `raw/`. Observed, inferred and not checked stay apart; a citation you
did not open is not evidence (A.10). For a causal claim (C.28.CM), a serious rival account and
the observation that tells them apart. When the topic is the ADR itself, name any C.32.ADR
anti-pattern found.

**Proposes** facts in a closing "Proposed facts" table in the `facts.md` row format, and new
review points in the report. The main session appends the facts to `facts.md` after every explorer has
returned, so parallel explorers never write the same file.

**Must not** write outside its file, change any repository, or post anything.

**Done when** every question has an answer with a reference, a named gap, or "not checked" with
the reason.

## Edit

**Agent** `adr-editor`. **Patterns** F.19, A.6.3.CSC, NSTD.1, NSTD.2, NSTD.3 (decided); EXD.3,
C.42 (adopted).

**Reads** `decisions.md`, `10-goal.md`, the previous `40-comment.md` (or, in v01, `points.md`
and `facts.md`), `vocabulary.md`, `text-rules.md`, `length-budget.md`; in a fix round, the review
file.

**Produces** `vNN/40-comment.md` and `vNN/41-changes.md`:

- the comment set in the order a reader needs (NSTD.2): opening, the asks by deadline, then one
  section per theme with its evidence; inline comments last, each anchored to an ADR section;
- each sentence with its governing message first and its participants recoverable (F.19);
- for every shortening, the source passage, the shorter text, and what was lost, in
  `41-changes.md` (A.6.3.CSC); no claim is added or strengthened by the rewording;
- every must-keep fact still present with its link, or its loss recorded with the reason and the
  decision that allows it; replacing a code link by the fact's design-level source, as the ADR's
  kind requires, is not a loss;
- code links only as the code-citation rule allows (`text-rules.md`, "Claims and evidence");
- protected passages byte-identical;
- a split into one to three comments that keeps every decisive condition with its claim (EXD.3);
- proposals cut to what the committee decides, details by link (C.42: each proposal names the
  condition it changes, and nothing is kept that does not serve the reader's decision).

**In a fix round**: apply the review's findings in severity order, change only the cited
passages, append a round section to `41-changes.md` (finding, old text, new text, or "not
applied" with the reason).

**Done when** the goal's checks can be answered from the comment and `41-changes.md` names every
change and every loss.

## Review

**Agent** `adr-reviewer`, never the session or agent that edited the text. **Patterns** E.23,
NSTD.6, C.28.CM (decided); F.13, A.10 (adopted).

**Reads** `decisions.md`, `10-goal.md`, `40-comment.md`, `41-changes.md`, the ADR snapshot,
`facts.md`, `vocabulary.md`, `text-rules.md`, `checks.md`; in a re-review, the earlier review
files.

**Produces** `vNN/5N-review-rN.md`:

- the declared evaluation before any finding (E.23:4.1 step 1): the object (this comment
  version), the reader and use, the checks (the goal's checks plus human readability,
  correctness, and whether each problem is stated adequately), and the stop condition. Use the
  same evaluation (checks, severity rules, stop condition) in every round of this version, so
  rounds compare (E.23 re-evaluation);
- any C.32.ADR anti-pattern the comment fails to name where the goal asks for review points
  about the ADR, or names wrongly;
- one row per finding: location, evidence, severity (must fix, should fix, consider), and the
  exact replacement text;
- correctness: every claim traced to the ADR line or a fact's reference, quotes verbatim, an
  inference marked as one, a contested reading turned into a question; for every causal claim, a
  serious rival account and what would distinguish them (C.28.CM);
- readability for the declared reader (NSTD.6), judged by what the reader can recover, not by
  fluency. Three characteristics, on NSTD.6's 0–5 scale, floor 4:
  - **relation recovery**: for each ask, a cold reader recovers problem, place, ask and deadline;
    below the floor, name the missing relation and supply it;
  - **ordering recoverability**: the reading order (opening, asks by deadline, sections) does not
    suggest a cause or a priority the source does not support; below the floor, reorder or state
    the relation;
  - **source return**: every claim the reader may want to check has its link at the point of use;
    below the floor, add the link or mark the claim as an inference;
- code citations: a code link the code-citation rule (`text-rules.md`, "Claims and evidence")
  rules out is a should-fix finding, with the documentation to cite instead;
- vocabulary: terms against `vocabulary.md`; a term that changed between ADR page versions is
  followed through (F.13);
- adequacy: each problem says what goes wrong, for whom and under which condition; an ADR defect
  the comment misses is raised only if the goal asks for new review points;
- text rules: the scans of `checks.md` run with the Grep tool over the posted parts, each real
  hit reported;
- what got worse since the previous round (E.23:4.1 step 8);
- a decision: stop or continue, with the reason;
- the alias `ADR-0NN vNN review rN`.

**Severity rules**: must-fix is reserved for a wrong or unverifiable claim, a broken decision, a
lost must-keep fact, a session label or security detail in posted text, or a failed goal check
that does not conflict with a decision. A goal check that conflicts with a decision is reported
as "conflict: check <name> against decision <name>" for the orchestrator, not enforced. Length
alone is never must-fix, and counts of words or characters are never reported as findings.

**In a re-review**: the earlier findings and the lines the fixes touched; a new finding elsewhere
states why the earlier review could not have seen it.

**Done when** every goal check has an answer and every finding has a replacement or a reason why
none is possible.

## Accept

**Agent** `adr-acceptor`. **Patterns** C.39.WI, C.42 (decided); C.41.UA, A.7 (adopted).

**Reads first, cold**: `40-comment.md` and the ADR snapshot only, as the ADR author would. Then
`10-goal.md`, `decisions.md`, the last review file.

**Produces** `vNN/60-acceptance.md`:

- the cold read: for each ask, can the author tell what the problem is, where it is (ADR section,
  code, ticket), and the first step and its deadline (C.39.WI)? Pass or fail, with the sentence
  that decides it;
- for each proposal, the condition it changes and whether any part does not serve the author's
  next step (C.42), naming the exact sentence that could go;
- the goal's checks answered yes, no, unknown or not checked (C.41.UA), each with its basis; a
  fix that was listed but not applied counts as not done (A.7);
- the verdict: accept, accept with listed fixes (each with exact replacement), or not accepted
  with the reason. Listed fixes go to the editor, then to a changed-passages re-review that counts
  as a round within the bound (SKILL.md, "Review–fix rounds"). A failure that conflicts with a
  decision is reported as a conflict, never as a reason to reject;
- the alias `ADR-0NN vNN acceptance`.

**Done when** every ask and every goal check has an answer and the verdict follows from them.

## Checks and hand-over

The main session runs `checks.md`, writes `vNN/70-checks.md`, rewrites `vNN/HANDOFF.md`, and
reports to the user per SKILL.md.

