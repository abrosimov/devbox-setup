---
name: diverge-synthesize-select
description: Diverge-Synthesize-Select (DSS) procedure for choosing between genuinely different approaches — generate 3–7 candidates including a boring baseline and a combination, weigh their trade-offs, and present a decision card with a recommendation. Use when a choice is irreversible, spans several files or components, crosses the named scope, has two or three outcome-changing unknowns, or when the user asks for options, alternatives, or solutions. Also covers parallel "advocate" agents for architecture-level decisions. Not to be confused with `fpf-thinking` (problem framing) or `mcp-sequential-thinking` (step chains).
alwaysApply: false
problem: "Consequential decisions collapse into the first workable idea instead of a real comparison of alternatives."
related: [response-templates, fpf-thinking, mcp-sequential-thinking, structured-output, writing-for-the-reader]
---

# Diverge-Synthesize-Select (DSS)

The first workable idea is rarely the best one, and a decision taken with two or more genuine
alternatives on the table fails far less often than a yes/no decision. DSS is the procedure that
turns "here is my plan" into "here are the real options, what each costs, and which I recommend".
The output the user sees is a decision card (template T2 in the `response-templates` skill).

## When to use it

Show 3–7 candidates when any of these holds:

- the choice is irreversible or expensive to undo (public API, data model, wire format, migration);
- it touches several files, components, or services;
- it crosses the scope the user named;
- the user asked for solutions, options, or alternatives;
- two or three unknowns could change the outcome substantially.

Otherwise pick a defensible default and say so in one line, for example: "Using the existing
`retry` helper rather than a new backoff policy — it already covers this call site." The one-liner
keeps the user informed without spending their attention on a choice that does not need them.

If the problem itself is still unclear (what the system is, where its boundary lies), frame it
first with `fpf-thinking`; DSS assumes you know what you are choosing between.

## Procedure

### 1. Frame

Write the decision as one sentence, list the criteria that matter, and name the unknowns that
could swing it. Start from these criteria and add domain ones (latency, security posture, cost)
as the problem needs:

| Criterion | Question |
|-----------|----------|
| Simplicity | Which adds the least new machinery? |
| Consistency | Which fits the patterns already in the codebase? |
| Reversibility | Which is cheapest to change later? |
| Testability | Which is easiest to verify? |

### 2. Find the axes before the candidates

Identify two to four orthogonal dimensions along which solutions differ — for a cache, say,
invalidation (TTL / event-driven), storage (in-process / distributed), and granularity (entity /
query). Choosing axes first is what makes candidates structurally different rather than the same
idea renamed. If you cannot find two meaningful axes, the decision is probably below the threshold:
pick a default and say so.

### 3. Diverge

Generate the candidates before judging any of them; early judgement anchors on the first idea.

- Aim for 3–7. Use the lower end when one trigger holds and the upper end when the choice is
  irreversible and several unknowns are in play. Seven well-separated candidates beat ten blurred
  ones.
- Include a **boring baseline**: the simplest thing that could work, often "extend what exists".
  It is the yardstick every other candidate has to beat, and it often wins.
- Include at least one candidate that challenges an assumption about how the problem "should" be
  solved, when such a candidate is plausible.
- Give each a stable ID paired with a short name: `OPT-1 — extend the job table`.
- Merge candidates that sit at the same axis positions with the same trade-offs.

### 4. Evaluate

Weigh the candidates in an order different from the one you generated them in, which dampens the
pull of whichever came first. Score each criterion `strong`, `adequate`, or `weak`. A candidate
that is weak on simplicity or consistency without a compelling reason, or that needs work outside
the agreed scope, is marked `dropped: <reason>` — it keeps its ID so the user can see it was
considered.

### 5. Combine

Look for strengths that can coexist: does the storage choice of one candidate fit the invalidation
model of another? Offer at least one combination as its own candidate with a new ID, stating which
IDs it draws from. When the strongest parts conflict, say what conflicts; a forced hybrid that
inherits both sets of costs helps nobody.

### 6. Present the decision card

Use template T2 from `response-templates`. Its content, in order:

1. The decision in one sentence and the criteria used.
2. A table of candidates: ID and name, mechanism, pros, cons, combines-with. The boring baseline
   and the combination are both in it; dropped candidates appear with their reason.
3. **Synergies** — which pairings reinforce each other and why.
4. **Trade-offs** — what you give up with each serious contender, in the reader's terms.
5. **Recommendation** — one candidate and the reason it wins under the stated criteria, plus the
   condition that would change your pick.

Present candidates and their trade-offs, not a narration of how you thought about them. When you
ask another agent for input, ask for "candidates with trade-offs"; requests to "show your reasoning"
get refused by newer models and produce worse material anyway.

Write the card so it stands alone: someone who reads only this message should understand every
candidate without scrolling back (see `writing-for-the-reader`).

### 7. Stop at the recommendation

The recommendation is the natural end of the reply. The user's next message is the decision; you do
not need a banner asking for it. If the decision needs input you cannot get, the reply's final
"What I need from you" section says so, as the core protocol describes.

## Follow-ups

| The user says | You do |
|---------------|--------|
| An ID ("OPT-3", "the job table one") | Record the choice and proceed within the approval rules in force |
| "The combination" or a custom mix | Record it with the IDs it draws from and a one-line rationale |
| "More options" | Append new candidates with the next free IDs (OPT-8, OPT-9, …); earlier IDs keep their numbers |
| "Different axes" | Generate a fresh set along the new axes with new IDs; mark superseded ones `dropped: replaced by new axes` |
| A question | Answer it and restate only the candidates it affects, each ID with its name |

IDs never get renumbered, reordered, or merged across turns — the user must be able to trust that
`OPT-4` still means what it meant yesterday.

## Persisted record

When the calling command or workflow asks for a machine-readable record, write `dss_output.json` in
the project directory, following the `dss_output` schema described in `structured-output`: problem
statement, axes, candidates, evaluation, combination, and the selection (`decided_by: "pending"`
until the user chooses). Only the chosen approach needs to travel onward in the conversation; the
record keeps the rest.

## Advocates: parallel agents for architecture-level decisions

For architecture-level work — system design, API contracts, domain boundaries, competing
interpretations of a domain — one mind generating every candidate tends to steelman its favourite
and strawman the rest. Advocates fix that by giving each approach its own champion.

**Who runs it.** The top-level session (the lead) orchestrates. In engines where a subagent cannot
start further subagents, the command or main conversation that would otherwise launch the
specialist launches the advocates instead, then hands their briefs to the specialist or synthesises
them itself.

**Steps.**

1. Frame the decision and find the axes (steps 1–2 above), then pick 3–7 candidate approaches with
   IDs and names, including the boring baseline.
2. Launch one read-only advocate per candidate, all in the same batch so they run in parallel.
   Each brief carries: the decision and criteria; the assigned candidate (ID and name); the names of
   the rival candidates; the sources to read (spec, plan, relevant code paths); the scope
   (read-only, no edits, no questions to the user); and the output format below.
3. Wait until every advocate has returned. Until then, any update is one line:
   "k of n done; waiting for: <names>". Reporting after only some have returned invites a decision
   on half the evidence.
4. Synthesise: check each brief's claims against the evidence it cites, discount unsupported ones,
   build combinations from compatible strengths, and produce one decision card.

**Advocate output format.** Ask for candidates with trade-offs, in this shape:

- Mechanism — how the approach works here, concretely.
- Strongest case — where it beats the rivals, with evidence (`path:line`, doc link).
- Honest costs — what it makes harder, and the conditions under which it loses.
- Combines with — which rival's strengths it could absorb, and what would conflict.

Advocates argue for their candidate, but an advocate that hides costs weakens its own case: the lead
weighs evidence, not enthusiasm.

## Pitfalls

| Pitfall | What prevents it |
|---------|------------------|
| Candidates differ only in naming | Axes chosen first; merge same-position candidates |
| Options staged to justify a choice already made | Axes before candidates; boring baseline required; shuffled evaluation |
| Every small choice becomes a menu | Threshold above; below it, a one-line default |
| Forced hybrid | State the conflict when strengths do not combine |
| Renumbered list after "more options" | Append with the next free IDs |
| Partial report while advocates are still running | One status line until all have returned |
