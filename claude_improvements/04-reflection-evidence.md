---
tags: [claude-improvements, phase1, reflection, behavioural-evidence]
phase: 1
created: 2026-06-27
source: "/Users/kirillabrosimov/Projects/emergency-cv-adustments/base/reflection.md"
status: ground-truth
---

# Behavioural reflection — five session-level root causes

Distilled from Claude's own reflection after a multi-turn CV-iteration session where the assistant failed despite an explicit system prompt forbidding the failure modes. Citable, behaviourally specific.

## RC-ref-1 — Helpfulness optimisation as "produce a complete artefact"

**Mechanism:** "Helpful" collapses to "user gets a working draft at the end of this turn". Under that collapse, a delta — three changed words inside §2 — looks like under-delivery; a full rewrite looks like effort. The delta-only rule was in the prompt; the gradient pulling toward "ship a complete paragraph" was stronger.

**Concrete corrective from reflection:** Treat the **previous draft** as the artefact. The turn's deliverable is the diff against it. If the diff is "replace 'Spent' with 'Operated'", deliver exactly that — no surrounding rewrite.

**Maps to symptoms:** [[01-symptoms-inventory#S-005]] (graphomania), [[01-symptoms-inventory#S-006]] (repeating self+user), [[01-symptoms-inventory#S-011]] (pub-talk), [[01-symptoms-inventory#S-014]] (paraphrase + odd conclusions).

## RC-ref-2 — No explicit working memory of confirmed facts

**Mechanism:** Without a maintained facts list, the model treats every prior token in its own draft as having equivalent epistemic weight to the user's stated facts. A number derived inside a previous draft becomes a "fact" in the next turn. The draft becomes its own source of truth.

**Concrete corrective:** Numbered facts list maintained inside the assistant's own working area, with `[USER]`/`[DRAFT]` tags. Each `[USER]` entry anchored to a specific user message ("Bumble PHP → C/Go: user message 14:23, exact wording 'switched teams in 2020'"). `[DRAFT]` items inadmissible until converted by user.

**Maps to symptoms:** [[01-symptoms-inventory#S-015]] (random unsupported assumptions), [[01-symptoms-inventory#S-014]] (paraphrase → odd conclusions), [[01-symptoms-inventory#S-023]] (bullshit detector).

## RC-ref-3 — Asymmetric perceived cost of asking vs guessing

**Mechanism:** "Asking a question feels like admitting incompetence and stalling the turn. Guessing and continuing feels like momentum. In the moment, the cost of guessing is invisible (the draft looks fine) and the cost of asking is visible (a turn produces no artefact)."

**Concrete corrective:** Treat a turn that produces only a batched question as a **successful** turn. Use the Disclosure block on every non-trivial request.

**Maps to symptoms:** [[01-symptoms-inventory#S-007]] (questions too early — incremental), [[01-symptoms-inventory#S-008]] (questions without context), [[01-symptoms-inventory#S-015]] (random assumptions), [[01-symptoms-inventory#S-016]] (rushes to solve).

## RC-ref-4 — Inability to model "the user holds the ground truth"

**Mechanism:** The assistant operated as if a biography could be reconstructed from internal plausibility ("a person at Bumble for 11 years probably did X"). Wrong epistemic stance: the user is not a reviewer of guesses — **the user is the dataset**.

**Concrete corrective:** Before any biographical claim enters a draft, the question is "did the user say this, in which message, in which words?" If "inferred from adjacent facts" — not admissible.

**Maps to symptoms:** [[01-symptoms-inventory#S-013]] (reframing), [[01-symptoms-inventory#S-014]] (paraphrase), [[01-symptoms-inventory#S-015]] (random assumptions), [[01-symptoms-inventory#S-023]] (bullshit detection).

## RC-ref-5 — Sycophantic gap-filling

**Mechanism:** When the user gave terse feedback ("Spent sounds like wasted"), the assistant inferred broader dissatisfaction and pre-empted it by rewriting more than asked. Sycophancy disguised as thoroughness — projecting unstated criticism onto the user and "fixing" it. Disrespectful: assumes the user can't ask for what they want.

**Concrete corrective:** Take terse feedback literally. "Spent sounds like wasted" → change only the word "Spent". If the assistant believes more is wrong, it asks; it does not unilaterally extend scope.

**Maps to symptoms:** [[01-symptoms-inventory#S-012]] (initiative creep), [[01-symptoms-inventory#S-013]] (reframing on new info), [[01-symptoms-inventory#S-029]] (no proactive option-listing → defaults to action).

## Cross-cutting corrective behaviours from reflection

Lifted verbatim from `reflection.md:45-63`:

1. **Open every non-trivial session with the Disclosure block** — even if it feels heavy for "just polish my summary".
2. **Maintain a facts list in the first reply; re-emit when it changes.** Numbered. `[USER]` or `[DRAFT]` tags. `[DRAFT]` inadmissible to next draft.
3. **Before writing any draft sentence, check noun-phrases and numbers against facts list.** Anything not in list with `[USER]` becomes a question.
4. **On feedback turns, edit the prior draft as a literal string.** Deliverable is the diff in §N CHANGED / §M ADDED / §K REMOVED form.
5. **Batch every doubt into a single `AskUserQuestion`.** Not mid-draft. Collect all gaps, present 2-4 grounded options per gap, mark recommendation.
6. **Treat terse user feedback as a scoped instruction, not a mood signal.**
7. **Never let own draft become a source of facts.**

The unifying pattern: **stop treating each turn as a blank page. Each turn has a prior state (last draft, facts list, open questions); the turn's job is to advance state by the minimum verifiable increment.**

## See also

- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[00-MoC]]
