---
tags: [claude-improvements, phase2, fpf-diagnostic, audit]
phase: 2
created: 2026-06-28
status: diagnostic
method: FPF (First Principles Framework) — A.7, A.6.B, A.3.1, A.15, A.19, C.16
---

# FPF diagnostic — structural audit of the catalogue

Applied FPF as a specification lens against the catalogue's own claims, cross-references, and proposed fixes. Not a retelling of FPF — only the patterns that expose structural problems in this material.

## D1 — Solution contradicts diagnosis (A.7 Strict Distinction)

The catalogue diagnoses attention budget overflow as a compounding root cause:

- [[rc-11-claude-md-attention-budget]]: model attends ~150 instructions; system prompt eats ~50.
- [[rc-13-claude-md-bloat]]: effective CLAUDE.md stack 509 lines — 2.5–5× over Anthropic guidance.
- [[10-root-causes-overview#Cross-cutting design observations]] observation #2: "Bloat compounds all other root causes. Trim CLAUDE.md before piling on new rules."

Then prescribes across the 30 RC files:

- ~25 new skills ([[00-MoC#Fix surface frequency (across all 30 RCs)]])
- ~15 new output-styles (same source)
- ~10 new hooks (same source)
- ~10 new commands (same source)

**FPF violation (A.7):** the EntityOfConcern of the problem (model attention capacity — a finite, measurable budget) and the EntityOfConcern of the solution (volume of configuration rules consuming that budget) are in the same CharacteristicSpace but moving in opposite directions. The catalogue notices the constraint but builds a plan as if it does not bind.

No RC file contains a **token-cost balance**: how many tokens each proposed fix adds vs how many it frees. The constraint is acknowledged as text but not operationalised as a selection criterion.

## D2 — Layer A RCs are Laws, not fixable causes (A.6.B Quadrant L vs A.15 Work)

[[10-root-causes-overview#Layer A — Model-internal (training / architecture)]] contains 8 RCs classified as "root causes" with "fix proposals":

- [[rc-01-rlhf-pushback-loop]] — RLHF anti-sycophancy overcorrection
- [[rc-02-helpfulness-as-artefact]] — turn-output gradient toward complete artefact
- [[rc-03-verbosity-task-complexity]] — 4.8 length calibration to perceived complexity
- [[rc-04-tokenizer-densification]] — 4.7+ tokenizer 12–35% denser
- [[rc-05-tool-calling-preference-drop]] — 4.8 prefers reasoning over tool calls
- [[rc-06-no-working-memory]] — no persistent working-memory mechanism
- [[rc-07-asymmetric-ask-vs-guess]] — asking feels like stalling
- [[rc-08-sycophantic-gap-filling]] — terse feedback triggers scope extension

In FPF terms (A.6.B Boundary Norm Square), these are **Laws** (Quadrant L) — properties of the model's training and architecture that this user cannot change. They are boundary conditions to design within, not causes to eliminate.

The word "fix" in each RC file's "Fix proposals" section creates a false expectation: that after executing the fix, the cause disappears. None of the Layer A fixes eliminate their cause — all mitigate downstream effects. The catalogue itself says this in [[10-root-causes-overview#Layer A — Model-internal (training / architecture)]]: "We can mitigate via prompting, hooks, and topology — we cannot directly change them." But the file template ([[_writer-instructions#Per-RC file template]]) applies the same "Fix proposals" framing regardless of layer, erasing the distinction.

**FPF-correct framing:**

| Layer | FPF kind | Relation to Work |
|---|---|---|
| A (model-internal) | Laws / Constraints (A.6.B-L) | Design within; mitigate effects |
| B (harness) | Environment boundary | Adapt to; propose upstream changes |
| C (config) | Design space | Direct transformation via Work |
| D (workflow) | Design space | Direct transformation via Work |
| E (verification) | Design space | Direct transformation via Work |
| F (process) | Design space | Direct transformation via Work |

## D3 — No measurement baseline (C.16)

Acceptance signals in RC files contain quantitative claims without a measured current state:

- [[rc-02-helpfulness-as-artefact#Acceptance signal]]: "Average output token count on feedback turns drops by ≥40% vs current baseline" — no file contains the current baseline value.
- [[rc-15-engineering-attitude-skill-missing#Acceptance signal]]: "In 10 sessions involving stack-change questions, ≥7 propose shadow-mode or CBC pattern without the user prompting" — no current frequency recorded.
- [[rc-24-done-without-verification]] (referenced in [[10-root-causes-overview]]): "tests pass" claim audit — no current false-positive rate.

Per C.16 (Measurement & Metrics Characterisation), an acceptance signal without a measurement template containing actual pre-intervention values is untestable. These are aspirations formatted as evidence.

## D4 — MethodDescription and WorkPlan not separated (A.3.1, A.15.2)

The catalogue is structured as "pick an RC → implement fixes" — this is a MethodDescription (how-to-do-it). A WorkPlan (when, in what order, with what dependencies) is absent.

Hard dependencies exist between fixes but are not modelled as a DAG:

| Prerequisite | Blocked fixes | Why |
|---|---|---|
| [[rc-13-claude-md-bloat]] trim | Any new `alwaysApply: true` skill | Adding to a 509-line stack worsens the diagnosed cause |
| [[rc-11-claude-md-attention-budget]] budget accounting | Deciding how many new always-on assets fit | Without a budget number, selection is unconstrained |
| [[rc-14-inter-asset-conflicts]] conflict resolution | Any new rule that could conflict with existing rules | New rules on top of existing conflicts compound |

[[00-MoC#How to use this catalogue across sessions]] suggests "Pick the RC with the highest impact-for-your-pain combination" — this is selection without dependency ordering. It invites starting with the most painful symptom (e.g. RC-15 engineering-attitude) rather than the prerequisite (RC-13 trim), which would increase bloat while trying to reduce its effects.

## D5 — Fix proposals mix surfaces without interaction accounting

Example from [[rc-15-engineering-attitude-skill-missing#Fix proposals]]:

- F1: new `engineering-attitude` skill (`alwaysApply: true`) — adds always-on attention cost
- F2: extend reviewer agents — adds review checklist items
- F3: per-SE-agent frontmatter references — adds per-agent load
- F4: new `engineer-posture` output-style — adds opt-in output overhead
- F5: extend `proposal_discipline.py` hook — adds UserPromptSubmit injection

Five fixes proposed independently. No interaction model: what happens when F1 + F2 + F3 + F5 all fire simultaneously on one turn? The combined attention cost is not estimated. Per A.15.5 (Work-Entry Readiness), the precondition "does this fit within the attention budget?" is not checked before any individual fix is marked ready for implementation.

## D6 — Where a generic AI response would be useless

A typical AI response to this catalogue: "Excellent analysis. Let's prioritise RC-15 (engineering-attitude) and RC-02 (delta-discipline) — they address the most painful symptoms."

This is useless because:

1. Adding `engineering-attitude` (`alwaysApply: true`) to a 509-line stack reinforces [[rc-13-claude-md-bloat]], which the catalogue identifies as compounding all other causes.
2. Starting with add-fixes instead of trim-fixes works against the catalogue's own cross-cutting observation #2 ([[10-root-causes-overview#Cross-cutting design observations]]).
3. Without a baseline measurement (D3 above), no fix can be verified as working — the effort produces unfalsifiable claims.

## Proposed next working move

**Build an attention-budget ledger** — a CharacteristicSpace (A.19) with a C.16 measurement baseline.

Concrete steps:

1. **Measure current always-on token load.** Count tokens in: `USER_AUTHORITY_PROTOCOL.md` + all `alwaysApply: true` SKILL.md files + hooks' `additionalContext` injections + system prompt overhead. This is one number: current budget consumption.
2. **Set a target budget.** Based on [[02-external-research#R6.1]] (IFScale: 68% accuracy at 500 instructions) and [[rc-11-claude-md-attention-budget]] (~150 effective instructions), define a target ceiling — e.g. 200 effective lines after trim.
3. **Tag each proposed fix with two numbers:** tokens added, tokens freed. Fixes that only add (new skill, new hook injection) get a positive cost. Fixes that trim (RC-13 CLAUDE.md reduction, RC-14 conflict removal) get a negative cost.
4. **This turns 150+ fix proposals into constrained selection** (A.19.SelectorMechanism): maximise symptom coverage within the attention budget.

Result: [[rc-13-claude-md-bloat]] moves from "one of 30 RCs" to a **prerequisite with a concrete numeric target**. All add-fixes get a numeric entry criterion: they fit within the remaining budget, or they do not.

## See also

- [[00-MoC]]
- [[10-root-causes-overview]]
- [[rc-11-claude-md-attention-budget]]
- [[rc-13-claude-md-bloat]]
- [[rc-14-inter-asset-conflicts]]
- [[rc-15-engineering-attitude-skill-missing]]
- [[rc-02-helpfulness-as-artefact]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
