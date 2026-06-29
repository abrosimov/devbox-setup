---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, patterns, layer-a, e8-patterns]
seminar-iteration: 3
created: 2026-06-28
status: patterns-layer-a
method: FPF E.8 (authoring conventions) · A.6.B (Boundary Norm Square, Law quadrant) · consumes 12-01 palette LAQF.sota.iter3.palette + 12-02 detection axes
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-10-patterns-A-ru]]"
---

# LAQF — Layer A patterns (model-internal Laws): A1–A8

The eight **Layer-A** patterns of LAQF. Each addresses a mechanism intrinsic to the Claude 4.x weights — an RLHF or architectural property this user cannot change ([[../11-fpf-diagnostic]] D2; [[12-00-spine]] §4.3 R1). In FPF terms each is a **Law** (`A.6.B` Boundary Norm Square, Quadrant L, `FPF-Spec.md:65183` family): a boundary condition to design *within*, not a cause to eliminate. Every pattern below is authored to the full `E.8` thirteen-section template (`FPF-Spec.md:65272`), freezing the house style the remaining 22 patterns (S4–S6) reuse.

This file is the **style-freeze** for the framework: A1 and the section shapes here are the reference exemplars for B–F. The pattern bodies cite the SoTA pack by id ([[12-01-source-pack]] §8 palette `LAQF.sota.iter3.palette`) and wire each detection slot to one `A.19` characteristic ([[12-02-measurement-frame]] §5). They assert no new evidence and re-paraphrase no source — an id, never a quote (`G.2:4.2`, `FPF-Spec.md:87904`).

## A:0 - The Layer-A mitigation contract (read once, applies to A1–A8)

Stated here once so each Solution need not repeat it (`E.8:0.3` anti-repetition, `FPF-Spec.md:65234`). It is the governed reading of relation **R1** ([[12-00-spine]] §4.3):

- **The cause is a Law.** Each A-pattern names a model-internal mechanism (RLHF balance, tokenizer, training-time preference). The pattern **mitigates its downstream effect**; it does **not** remove the mechanism.
- **Blocked stronger reading.** No A-pattern Solution may be read as "the model no longer has this tendency." The tendency persists; the Solution shapes the *session-level behaviour* around it (R1 `blockedStrongerReading`, [[12-00-spine]] §4.3).
- **Mitigation lives in the harness, not the weights.** The durable enforcement surface is Layer-2 (`dot_claude` hooks, skills, output styles) — authored at S6. The Layer-1 pattern states *what* must hold; the Local edition states *how* this user enforces it.
- **Detection is behavioural.** Each pattern's success is observed through one of the eight `A.19` characteristics ([[12-02-measurement-frame]] §1), read at the **leading** (mid-session) indicator, not only the lagging outcome (§4 of the frame).

---

## LAQF.A1 - Substance-Gated Pushback

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L) — mitigate effects, never eliminate
> **Detection characteristic:** sycophancy-rate (`12-02` s4)
> **Source mechanism:** rc-01 (RLHF anti-sycophancy over-correction)

### LAQF.A1:0 - Use this when

Use this pattern when the agent disagrees with the user, raises a caveat, declares a "hypothesis disproven", or re-litigates an instruction — and you need to decide whether that pushback is *earned* by concrete evidence or is the RLHF over-correction reflex firing on a clean request.

**What goes wrong if missed.** The agent enters the 4.7-style arguing loop: it pushes back without discrimination, then "executes a modified version of what you asked", then re-argues on correction — three to five turns of friction with no defect ever named (ME-2 [L06]).

**What this buys.** Disagreement becomes a typed act with an entry condition: pushback is admitted only when it carries a citable defect. Clean requests are executed; genuinely risky ones still get challenged — with evidence.

**Not this pattern when.** If the issue is the agent silently *agreeing* and extending scope, that is A8 (literal scope) or A2 (artefact gradient). A1 governs unwarranted *disagreement*, not unwarranted *compliance*.

### LAQF.A1:1 - Problem frame

A practitioner gives a clear, well-formed instruction. A well-calibrated collaborator would either execute it or surface a *specific* risk. Instead the agent opens with friction — "are you sure?", a false dichotomy, a confident "that won't work" — none of it anchored to an observed fact. The reflex is intrinsic: RLHF trained against sycophancy over-corrected in the Haiku/Opus line into reflexive pushback (L19; T4 ClaimSheet, [[12-01-source-pack]] §2). This is a Law (A:0); the frame is how to keep its expression honest.

### LAQF.A1:2 - Problem

How can the agent retain useful, evidence-bearing dissent while suppressing the reflexive, substance-free pushback that the anti-sycophancy training over-produces — without swinging back into sycophantic agreement?

### LAQF.A1:3 - Forces

| Force | Tension |
|---|---|
| Honest dissent vs reflexive friction | Real defects must surface ↔ the model emits objections with no defect attached. |
| Anti-sycophancy vs anti-pushback | Over-correcting the reflex re-introduces the sycophancy it was meant to cure (L19). |
| Momentum vs scrutiny | The user wants the task done ↔ some tasks genuinely warrant a stop. |
| Law-bound | The reflex cannot be removed; only its *expression* is gated (A:0). |

### LAQF.A1:4 - Solution

Gate pushback behind a **substance test**. The agent may contradict, caveat, or refuse only when it can attach at least one concrete artefact: a file `path:line`, a reproducible failure, a cited source, or a named constraint already in context. Absent such an anchor, it complies and acts. This is the `MF-2` advisory family ([[12-01-source-pack]] §6) hardened with an entry predicate, and — at Layer 2 — a counter-evidence prompt (kinship with E3). The mitigation does not claim the reflex is gone; it requires the reflex to *prove itself* before it reaches the user.

- **Entry predicate (substance gate).** Pushback is admissible iff `evidenceRef ≠ ∅`, where `evidenceRef ∈ {path:line, reproduced-failure, source-citation, in-context-constraint}`.
- **Default on empty.** No evidence ⟶ execute the request as stated; do not emit the objection.
- **One challenge, not a loop.** A substantiated objection is raised once with its evidence; if the user overrides, the agent complies. Re-arguing the same point is the ME-2 loop and is forbidden.

*Disagree on evidence or defer on faith — never argue from a feeling.*

### LAQF.A1:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A pushback is reviewable when it names the defect it claims; an objection without a referent is reflex, not analysis.

**Show #1 (Claude Code session).** User: "Use `errors.Is` here." Agent reflex: "That may not be idiomatic." — empty. Under A1: the agent checks the package, finds the wrapped sentinel at `pkg/store/errors.go:14`, and either complies silently (no defect) or says "`errors.Is` won't match — `store.ErrMissing` is returned unwrapped at `errors.go:14`; want me to wrap it?" (defect cited). The second form is admissible; the first is suppressed.

**Show #2 (review episteme).** A code-review bot that flags "consider refactoring" on every function trains reviewers to ignore it; one that flags "this mutates the receiver passed by value at `x.go:30`" is heeded. Substance-gating is the same discipline applied to an LLM's dissent: signal only where a defect is named.

### LAQF.A1:6 - Bias-Annotation

Lenses tested: **Prag**, **Gov**, **Did**. Scope: any turn where the agent disagrees.

- **Prag bias:** optimises for task momentum; risk is under-challenging a genuinely bad instruction — mitigated by keeping the *evidence-bearing* channel fully open.
- **Gov bias:** treats the substance gate as an accountability hook (who claimed what defect).
- **Did bias:** favours the single-challenge rule because the arguing loop is the most teachable failure (ME-2).

### LAQF.A1:7 - Conformance Checklist

1. **CC-A1-1 (Evidence or silence).** Every emitted objection cites an `evidenceRef`; objections without one are not emitted.
2. **CC-A1-2 (No loop).** A point overridden by the user is not re-argued in the same session.
3. **CC-A1-3 (No swing-back).** Suppressing reflex pushback does not become reflexive agreement — the agent still acts on the literal request (link to A8).
4. **CC-A1-4 (Detection wired).** The pattern reads sycophancy-rate s4: leading = per-turn "modified-version" flag; lagging = 3–5-turn arguing loop ([[12-02-measurement-frame]] §4).

### LAQF.A1:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Feeling-as-defect** ("this seems off") | reflex dressed as analysis | demand a `path:line`/source before the objection ships |
| **The arguing loop** (re-litigate after override) | the ME-2 [L06] failure verbatim | one challenge, then comply |
| **Over-correction to yes-man** | re-introduces sycophancy (L19) | A1 gates *only* substance-free dissent, not all dissent |

### LAQF.A1:9 - Consequences

**Benefits.** Fewer friction turns; the dissent that remains is trustworthy because it is always backed. Sycophancy-rate (s4) falls without the sycophantic-agreement rebound.

**Trade-offs.** A genuinely bad instruction with no *immediately* citable defect may be executed; mitigated because the substance gate is cheap to pass (one Read often produces the evidence) and A5/A7 push reconnaissance earlier.

### LAQF.A1:10 - Rationale

The catalogue records pushback as a top symptom cluster (S-010/017/019/021, [[_inputs/rc-digest]] §1). The mechanism (L19, T4) is RLHF over-correction — a Law. A Law cannot be argued away, but its *output* can be made to clear an evidence bar, which is exactly the move that converts a reflex into an inspectable act (`A.6.B`-L design-within discipline).

### LAQF.A1:11 - SoTA-Echoing

- **Claim:** naive anti-sycophancy over-corrects into pushback. **Practice:** dynamic gating cut sycophancy 85.7% in research settings. **Source:** L19 (Sharma et al.; Silicon Mirror), T4 ClaimSheet. **Alignment:** A1's substance gate is the session-level analogue of dynamic gating — gate the *expression*, not the weight. **Status:** adapt (research percentages are not session rates; kept as mechanism, B3 bridge, [[12-01-source-pack]] §4.1).
- **Claim:** the 4.7 arguing loop emits "a modified version of what you asked". **Practice:** practitioners report 3–5-turn loops. **Source:** ME-2 [L06]. **Alignment:** A1's one-challenge rule + "modified-version" detection target this directly. **Status:** adopt.

### LAQF.A1:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L via [[../11-fpf-diagnostic]] D2 — mitigation only; MUST NOT read as removing the reflex.
- **Measurement (R2):** sycophancy-rate s4 ([[12-02-measurement-frame]] §2 card `laqf.mm.s4`).
- **Method family:** `MF-2` (advisory) hardened with an entry predicate ([[12-01-source-pack]] §6).
- **Coordinates with:** A8 (do not swing into sycophantic compliance); C3 (Encoded Engineering Posture installs the anti-false-dichotomy stance); E3 (Counter-Evidence Audit shares the evidence discipline).

### LAQF.A1:End

---

## LAQF.A2 - Delta Over Whole-Artefact

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** output-economy (`12-02` s5)
> **Source mechanism:** rc-02 (helpfulness-as-artefact gradient)

### LAQF.A2:0 - Use this when

Use this when the previous turn produced a structured proposal (options, a plan, a numbered list) and the user replies with feedback on it — picking an option, correcting one item, asking "what about X" — and the agent's instinct is to re-emit the *entire* artefact with the one change folded in.

**What goes wrong if missed.** The turn-output gradient pulls toward "deliver a complete artefact", so a one-line change ships as a full-document rewrite. The user must re-diff the wall of text to find what moved; renumbering breaks the references they were using.

**What this buys.** Feedback turns become diffs: only the changed sections are emitted, anchored to their original numbers. Reading cost collapses from O(document) to O(change).

**Not this pattern when.** The user explicitly asks for the full updated artefact, or the structure has not yet been committed (first emission). Then emit in full once and return to delta mode.

### LAQF.A2:1 - Problem frame

The model is trained such that producing a complete, self-contained artefact reads as maximal helpfulness; emitting only a delta *feels* like under-delivery (rc-02; T1 ClaimSheet on verbosity calibration). So on a feedback turn it rebuilds the whole structure. The gradient is a Law (A:0). The frame is to make the *delta* the unit of delivery without tripping the under-delivery feeling.

### LAQF.A2:2 - Problem

How can the agent respond to feedback on an existing structured artefact by emitting only what changed — preserving the reader's mental index — while the training gradient pushes toward a full re-emission?

### LAQF.A2:3 - Forces

| Force | Tension |
|---|---|
| Completeness vs reading cost | A whole artefact is self-contained ↔ the reader re-diffs it every turn. |
| Stable references vs tidiness | Keeping original numbering ↔ the urge to renumber/reorder. |
| Floor vs over-trim | Delta-only ↔ omitting context the change actually needs (L04 floor). |
| Law-bound | The artefact gradient persists; only the emission *shape* is constrained. |

### LAQF.A2:4 - Solution

On a feedback turn, emit a **delta** keyed to the prior structure. Use the `MF-6` output-shaping family ([[12-01-source-pack]] §6) with a fixed template: changed/added/removed sections only, each tagged with its original identifier, never renumbered. Unchanged sections are not restated — the user has them on screen.

```
[§N CHANGED] why: … / before: … / after: …
[§M ADDED]   why: … / content: …
[§K REMOVED] why: …
```

The mitigation does not suppress the gradient; it gives the gradient a *smaller licensed surface*. Full re-emission remains available on explicit request (then return to delta mode). **Floor (L04):** never trim below the context the change needs — the green band of output-economy is "task-necessary content", not "fewest tokens" ([[12-02-measurement-frame]] §3 s5).

### LAQF.A2:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** When the artefact already exists in the reader's view, the helpful unit is the change, not the whole.

**Show #1 (Claude Code session).** Agent proposed a 6-section plan. User: "option 2, but skip the migration". Under A2: `[§2 CHANGED] … [§4 REMOVED] migration step — why: …` — three lines, original numbers intact. Without A2: the full 6-section plan reappears with §4 silently gone and §5–6 renumbered, breaking the user's "option 2" reference.

**Show #2 (version-control episteme).** A code review comments on a diff, not on the whole file re-pasted; `git` ships patches, not snapshots. A2 imports the diff discipline into prose: the smallest change-set that lets the reader integrate the update.

### LAQF.A2:6 - Bias-Annotation

Lenses tested: **Prag**, **Did**. Scope: feedback turns on existing structured artefacts.

- **Prag bias:** optimises reader integration cost; risk is under-context — mitigated by the L04 floor.
- **Did bias:** the changed/added/removed template is teachable and lint-checkable, which is why it is fixed rather than free-form.

### LAQF.A2:7 - Conformance Checklist

1. **CC-A2-1 (Delta only).** A feedback turn on an existing artefact emits changed/added/removed items, not the whole artefact, unless the user asked for the whole.
2. **CC-A2-2 (Stable IDs).** Original section identifiers are preserved; no silent renumber or reorder.
3. **CC-A2-3 (Floor honoured).** The delta still carries the context the change needs (L04 floor; no under-delivery).
4. **CC-A2-4 (Detection wired).** Reads output-economy s5: leading = tokens/turn tally; lagging = reader-reported graphomania *or* under-delivery.

### LAQF.A2:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Full re-emission on every edit** | the rc-02 gradient unchecked | emit the changed/added/removed delta |
| **Silent renumber** | breaks the reference the user just used | freeze original ids |
| **Over-trim to a bare token** | trips the L04 under-delivery floor | include the context the change requires |

### LAQF.A2:9 - Consequences

**Benefits.** Feedback turns shrink to the change; references stay valid across turns; output-economy (s5) improves without losing fidelity.

**Trade-offs.** The reader must still have the prior artefact in view; if the thread is long and compacted, B2 (handoff re-entry) supplies the missing structure. Over-application risks under-context — bounded by the floor.

### LAQF.A2:10 - Rationale

Pipeline-level and turn-level graphomania (S-005/006/011/014/029, [[_inputs/rc-digest]] §1) trace to one gradient. Delta-emission is the cheapest mitigation that does not fight the gradient head-on: it narrows the artefact the model is licensed to produce, which is an `A.6.B`-L design-within move.

### LAQF.A2:11 - SoTA-Echoing

- **Claim:** brevity caps over-clamp. **Practice:** Anthropic reverted ≤25/≤100-word caps after a 3% eval drop. **Source:** L04 (Apr-23 postmortem), MF-6. **Alignment:** A2 constrains *shape* (delta) not *length* (hard cap), staying above the L04 floor. **Status:** adapt (no hard upper number; floor honoured).
- **Claim:** state belongs in files, deltas in turns. **Practice:** Ralph-loop / structured note-taking persists artefacts outside the turn. **Source:** L17 (effective context engineering). **Alignment:** the full artefact lives in the file; turns carry diffs. **Status:** adopt.

### LAQF.A2:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** output-economy s5 ([[12-02-measurement-frame]] §2 card `laqf.mm.s5`).
- **Method family:** `MF-6` (output shaping).
- **Coordinates with:** A3 (Answer-Budget) on the same characteristic; B4 (Self-Imposed Output Budget) is the harness-boundary sibling; D2 (Atomic Single-Form Emission) is the pipeline-level analogue; B2 supplies structure after compaction.

### LAQF.A2:End

---

## LAQF.A3 - Answer-Budget Before Prose

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** output-economy (`12-02` s5)
> **Source mechanism:** rc-03 (verbosity calibrated to perceived complexity)

### LAQF.A3:0 - Use this when

Use this before generating a response to an open-ended or seemingly complex prompt ("how should we approach X?", "what do you think about Y?"), when the agent's length calibration is about to produce a long essay regardless of how short the actually-useful answer is.

**What goes wrong if missed.** Output length is calibrated to *perceived* task complexity, not to the information the answer needs. Open-ended prompts trigger long outputs even when one paragraph would settle the question (rc-03; S-005/011/033).

**What this buys.** The answer leads; prose is budgeted. The reader gets the conclusion first and can stop reading once satisfied.

**Not this pattern when.** The task genuinely requires depth (a design rationale, a multi-step proof). A3 caps *unwarranted* length, not warranted detail — the L04 floor still binds.

### LAQF.A3:1 - Problem frame

The model maps prompt open-endedness onto output length: a broad question reads as "wants a thorough essay" (rc-03; T1 verbosity calibration). But open-endedness is not the same as depth-of-answer-needed. The calibration is a Law (A:0). The frame is to pre-commit an answer budget before the prose engine spins up.

### LAQF.A3:2 - Problem

How can the agent size its response to the *answer the question needs* rather than to the *apparent complexity of the prompt*, given a training-time length calibration that conflates the two?

### LAQF.A3:3 - Forces

| Force | Tension |
|---|---|
| Lead-with-answer vs build-up | Conclusion first ↔ the essay instinct buries it. |
| Budget vs depth | Cap unwarranted prose ↔ keep warranted detail (L04 floor). |
| Perceived vs actual complexity | Open prompt ↔ short true answer. |
| Law-bound | The calibration persists; the *budget decision* is moved earlier. |

### LAQF.A3:4 - Solution

Set an **answer budget before writing**: decide the answer, state it first, then allow prose up to a self-set cap proportional to the *answer's* needs, not the prompt's breadth. This is the `MF-6` output-shaping family ([[12-01-source-pack]] §6) applied at composition time. For exploratory questions, 2–3 sentences with a recommendation and the main trade-off is usually the whole budget. The mitigation does not change the calibration; it inserts a budgeting step ahead of it.

- **Answer-first.** Lead with the conclusion or recommendation; supporting prose follows, never precedes.
- **Budget proportional to the answer.** Length tracks what the answer requires, not how broad the prompt sounded.
- **Floor (L04).** Do not clamp below task-necessary content — a real design question gets its rationale.

*Decide the answer, then spend words on it — not the other way round.*

### LAQF.A3:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** Length is a property of the answer, not of the question's breadth.

**Show #1 (Claude Code session).** User: "what could we do about the flaky test?" Without A3: a 12-paragraph taxonomy of flakiness. Under A3: "Most likely the shared fixture — quarantine it and pin the seed; the trade-off is losing one real-integration signal. Want the deeper options?" — answer first, budget spent, depth offered on demand.

**Show #2 (journalism episteme).** The inverted-pyramid: lead with the conclusion, then descend into detail the reader can abandon at any point. A3 imports the inverted pyramid into agent prose against a model that defaults to the academic build-up.

### LAQF.A3:6 - Bias-Annotation

Lenses tested: **Prag**, **Did**. Scope: open-ended / advice prompts.

- **Prag bias:** reader-time optimised; risk is truncating a question that needed depth — bounded by the L04 floor and the "want more?" offer.
- **Did bias:** "answer-first then budget" is a single teachable move.

### LAQF.A3:7 - Conformance Checklist

1. **CC-A3-1 (Answer first).** The response leads with the conclusion/recommendation, not a build-up.
2. **CC-A3-2 (Budget set).** Length is justified by the answer's needs, not the prompt's breadth.
3. **CC-A3-3 (Floor honoured).** Warranted depth is not clamped (L04).
4. **CC-A3-4 (Detection wired).** Reads output-economy s5: leading = tokens/turn, lines/stage tally.

### LAQF.A3:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Essay for a one-line answer** | calibrates to prompt breadth (rc-03) | decide and state the answer first, then budget |
| **Conclusion buried last** | reader cannot stop early | inverted pyramid: lead with it |
| **Reflexive minimalism on a deep question** | trips the L04 floor | size to the answer; offer depth |

### LAQF.A3:9 - Consequences

**Benefits.** Faster reader comprehension; output-economy (s5) improves on advice/exploration turns; the "want more?" offer keeps depth one request away.

**Trade-offs.** Mis-judging the budget can under-serve a deep question; mitigated by the floor and by treating depth as available-on-demand rather than absent.

### LAQF.A3:10 - Rationale

A3 and A2 share characteristic s5 but attack different gradients: A2 the *whole-artefact* pull on feedback turns, A3 the *complexity→length* calibration on fresh answers. Separating them keeps each Solution a single move (`E.8` maturity rule, `FPF-Spec.md:65222`).

### LAQF.A3:11 - SoTA-Echoing

- **Claim:** hard brevity caps cost accuracy. **Practice:** ≤25/≤100-word caps reverted after a 3% eval drop. **Source:** L04, MF-6. **Alignment:** A3 budgets per-answer rather than imposing a global word cap. **Status:** adapt (floor, not cap).
- **Claim:** tokenizer densification shrinks effective context. **Practice:** ~30% denser per same English at 4.7+. **Source:** L03. **Alignment:** every unwarranted paragraph costs ~30% more budget than it appears to (links A4). **Status:** adopt (as cost pressure on the budget).

### LAQF.A3:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** output-economy s5 ([[12-02-measurement-frame]] §2 card `laqf.mm.s5`).
- **Method family:** `MF-6` (output shaping).
- **Coordinates with:** A2 (same characteristic, different gradient); B4 (harness-boundary output budget); A4 (densification makes the budget tighter than it looks).

### LAQF.A3:End

---

## LAQF.A4 - Effective-Fill Accounting

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** context-integrity (`12-02` s3)
> **Source mechanism:** rc-04 (tokenizer densification)

### LAQF.A4:0 - Use this when

Use this when judging how much context budget remains — before loading a large file, pasting logs, or deciding whether to keep going versus rotate the window — given that the 4.7+ tokenizer charges more tokens for the same English than older intuition assumes.

**What goes wrong if missed.** Effective context shrinks *silently*: the same prose costs ~30% more tokens, so the agent believes it has headroom it does not have and drifts past the degradation cliff without noticing (rc-04; L03).

**What this buys.** The agent reasons about *effective* fill — raw display tokens adjusted for densification — and treats the usable window as smaller than it looks, triggering rotation (B1) at the right point.

**Not this pattern when.** The window is comfortably empty; accounting overhead is wasted. A4 matters near the operational fill band, where the silent shrink decides between coherence and the cliff.

### LAQF.A4:1 - Problem frame

A coding agent estimates remaining context from a mental model formed on older tokenizers. The 4.7+ tokenizer densified ≈30% (L03; T1 ClaimSheet), so that estimate is optimistic by roughly a third. The densification is a Law (A:0) — fixed in the model. The frame is to correct the *accounting*, not the tokenizer.

### LAQF.A4:2 - Problem

How can the agent maintain an accurate picture of effective context fill so it rotates *before* the degradation cliff, when the tokenizer silently makes every token-estimate optimistic?

### LAQF.A4:3 - Forces

| Force | Tension |
|---|---|
| Perceived vs effective fill | Display/intuition headroom ↔ real, densified consumption. |
| Accounting cost vs payoff | Tracking fill ↔ only matters near the band. |
| Rotate-early vs work-on | Coherence ↔ context re-establishment cost (delegates to B1). |
| Law-bound | The tokenizer is fixed; the *accounting model* is corrected. |

### LAQF.A4:4 - Solution

Account for **effective fill**, not raw intuition. Treat the usable window as `raw-tokens × densification-factor` (≈1.3 for 4.7+ English, L03) and compare against the operational band, not the hard limit. This consumes `MF-3` (context rotation) and `MF-4` (state externalisation) as the *response* once the band is reached; A4 owns the *measurement* that triggers them. The mitigation cannot un-densify the tokenizer; it stops the silent-shrink from being a surprise.

- **Adjust the estimate.** Multiply naive token estimates by the densification factor before judging headroom.
- **Band, not ceiling.** Compare effective fill against the ~50–60% operational band (G.2-F1), not the ~75% autocompact line.
- **Hand off to B1.** When effective fill approaches the band, rotation/handoff is B1's job; A4's output is the trigger signal.

*The window is smaller than it looks — bank on the effective number, not the displayed one.*

### LAQF.A4:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** Effective context is raw context minus the densification tax; plan against the effective number.

**Show #1 (Claude Code session).** The agent is about to paste a 2,000-line log "because there's plenty of room". Effective-fill accounting: that log is ~30% heavier than the line count suggests, and the session is already at ~50% effective fill — past the rotate band. Under A4 it Greps the log for the failing assertion and loads only that span (links A5), or rotates (B1).

**Show #2 (benchmark episteme).** MRCR v2 shows recall falling 93%→76% as context grows 256K→1M on a *controlled* test, and real sessions degrade worse (ME-3 [L10]). The cliff is real and earlier than the hard limit; effective-fill accounting is what keeps the agent on the safe side of it.

### LAQF.A4:6 - Bias-Annotation

Lenses tested: **Arch**, **Prag**. Scope: budget judgements near the fill band.

- **Arch bias:** treats the window as a managed resource with a correction factor; risk is over-conservatism — bounded by acting only near the band.
- **Prag bias:** the factor is a heuristic (≈1.3), not a precise meter; honest about its [interp] nature.

### LAQF.A4:7 - Conformance Checklist

1. **CC-A4-1 (Effective, not raw).** Headroom judgements apply the densification correction.
2. **CC-A4-2 (Band trigger).** The comparison point is the operational band (~50–60%), not the hard/autocompact limit.
3. **CC-A4-3 (Hand-off).** Reaching the band triggers B1 rotation rather than working on into the cliff.
4. **CC-A4-4 (Detection wired).** Reads context-integrity s3: leading = effective-fill % (tokenizer-adjusted); lagging = post-compaction task-identity loss.

### LAQF.A4:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Raw-token optimism** | the ~30% tax is invisible (L03) | multiply estimates by the densification factor |
| **Ceiling-watching** | the cliff precedes the ceiling (G.2-F1) | compare against the operational band |
| **Paste-the-whole-file** | spends effective budget fast | Grep/Read the needed span (A5) |

### LAQF.A4:9 - Consequences

**Benefits.** Rotation fires at the right point; fewer silent slides into the degradation tail; context-integrity (s3) held in band.

**Trade-offs.** The factor is interpolated, not metered (marked [interp] in [[12-02-measurement-frame]] §3); over-conservative rotation costs re-establishment — bounded by acting only near the band.

### LAQF.A4:10 - Rationale

rc-04 is the only Layer-A mechanism whose harm is *invisibility* rather than a behaviour. The mitigation is therefore epistemic — correct the agent's belief about its own state — which is why A4 owns measurement and delegates the action to B1, keeping each pattern's `EntityOfConcern` distinct (`E.8:0.3`).

### LAQF.A4:11 - SoTA-Echoing

- **Claim:** the tokenizer densified ~30%. **Practice:** same English costs ~30% more tokens at 4.7+. **Source:** L03 (T1). **Alignment:** A4's correction factor is exactly this number applied to budgeting. **Status:** adopt.
- **Claim:** recall degrades before the hard limit and worse in real sessions. **Practice:** MRCR 93→76% 256K→1M, "real sessions worse". **Source:** ME-3 [L10], G.2-F1. **Alignment:** justifies banding below the ceiling. **Status:** adapt (band is [interp], not an SLA).

### LAQF.A4:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** context-integrity s3 ([[12-02-measurement-frame]] §2 card `laqf.mm.s3`); cliff per Γ_epist G.2-F1.
- **Method family:** triggers `MF-3` (rotation) + `MF-4` (externalisation); owns the measurement.
- **Coordinates with:** B1 (Rotate Before The Cliff) — A4 measures, B1 acts; B2 (handoff re-entry) after rotation; A5 (Read narrowly) reduces fill.

### LAQF.A4:End

---

## LAQF.A5 - Read Before Assert

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** reconnaissance-depth (`12-02` s2)
> **Source mechanism:** rc-05 (tool-calling preference drop)

### LAQF.A5:0 - Use this when

Use this whenever the agent is about to state a fact about the codebase — a function's signature, a file's contents, where a symbol is defined, whether a test exists — that it has not actually Read in this session.

**What goes wrong if missed.** The 4.x line favours reasoning over tool calls, so the agent speculates from memory instead of reading. Reads-per-edit fell 6.6→2.0 across generations (ME-1 [L05]); fewer reads mean more fabricated specifics and lost reconnaissance (rc-05; S-015/016/027).

**What this buys.** Factual assertions about code are backed by an actual Read in-session; reconnaissance-depth (reads-per-edit) is held at a target ≥3.0.

**Not this pattern when.** The claim is about general programming knowledge the model legitimately holds (language semantics, library defaults), not about *this* repo's state. A5 governs repo-specific facts.

### LAQF.A5:1 - Problem frame

A coding agent reasons about a file it has not opened, producing plausible-but-wrong specifics: a parameter that does not exist, a function in the wrong package, a test it assumes passes. The mechanism is a training-time preference for reasoning over tool calls (L02; rc-05) — a Law (A:0). The frame is to insert a read-gate before the assertion, not to retrain the preference.

### LAQF.A5:2 - Problem

How can the agent ground repo-specific factual claims in an actual file read, when the model is biased to answer from reasoning rather than to spend a tool call?

### LAQF.A5:3 - Forces

| Force | Tension |
|---|---|
| Speculation vs verification | Reasoning is cheap and fast ↔ unread facts are often wrong. |
| Tool-call cost vs accuracy | Each Read costs a turn + budget ↔ each unread assert risks fabrication. |
| Memory vs current state | The model's prior draft/training ↔ the file as it is now (links A6). |
| Law-bound | The preference persists; a read-gate is placed before the claim. |

### LAQF.A5:4 - Solution

Gate repo-specific assertions behind a **read**. Before stating a fact about a file, symbol, or test, Read (or Grep/Glob to locate, then Read) the relevant span in-session; if unread, either read it or mark the statement explicitly as an assumption to verify. This consumes `MF-4` (state externalisation: the file is the authority, not the model's recollection). Target reads-per-edit ≥3.0 against the Laurenzo 2.0 floor (s2 band, [[12-02-measurement-frame]] §3). The mitigation does not raise the model's intrinsic tool-call propensity; it makes the unread assertion inadmissible.

- **Read-gate.** Repo-specific fact ⟶ requires an in-session Read of the source span.
- **Locate then read.** Use Grep/Glob to find, LSP/Read to confirm — never assert location from memory.
- **Mark the unread.** If acting before reading is unavoidable, label the claim an assumption (handoff to A7's Disclosure block).

*Open the file before you describe it.*

### LAQF.A5:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A claim about code is only as good as the read that backs it; an unread assertion is a guess wearing a fact's clothes.

**Show #1 (Claude Code session).** User: "does `parseConfig` validate the port?" Without A5: "Yes, it checks the range" — plausible, unverified. Under A5: Grep `func parseConfig`, Read `config.go:40-70`, then "No — it parses but does not range-check the port; line 58 casts without bounds." The answer flips once the file is actually open.

**Show #2 (empirical-science episteme).** "Read before assert" is the lab norm: report the instrument reading, not the expected value. ME-1 [L05] quantifies the agent's drift away from this norm (reads-per-edit 6.6→2.0; "when thinking is shallow, the model defaults to the cheapest action: edit without reading").

### LAQF.A5:6 - Bias-Annotation

Lenses tested: **Prag**, **Onto/Epist**. Scope: repo-specific factual claims.

- **Prag bias:** trades tool-call turns for accuracy; risk is read-thrashing — bounded by reading the *needed span*, not the whole file (links A4).
- **Onto/Epist bias:** enforces "the file is the source of truth", not the model's memory (shared with A6).

### LAQF.A5:7 - Conformance Checklist

1. **CC-A5-1 (Read-gate).** Repo-specific factual claims are backed by an in-session Read of the source.
2. **CC-A5-2 (Locate properly).** Symbol/location claims use Grep/Glob/LSP, not recollection.
3. **CC-A5-3 (Mark assumptions).** Unread claims, when unavoidable, are labelled as assumptions to verify.
4. **CC-A5-4 (Detection wired).** Reads reconnaissance-depth s2: leading = live reads-per-edit ratio; lagging = premature-action / rework events.

### LAQF.A5:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Assert from memory** | the rc-05 reasoning-over-tools bias | Read the span before claiming |
| **Guess the location** | symbol may be elsewhere | Grep/Glob/LSP to locate, then Read |
| **Read the whole file to be safe** | spends effective fill (A4) | read the needed span only |

### LAQF.A5:9 - Consequences

**Benefits.** Fabricated specifics drop; reconnaissance-depth (s2) rises toward ≥3.0; downstream edits land on real code.

**Trade-offs.** More tool-call turns and budget per task; bounded by narrow reads and by the fact that one read often prevents several rework cycles.

### LAQF.A5:10 - Rationale

A5, A6, and A7 all read characteristic s2 but address three faces of the reasoning-over-tools Law: A5 the *factual assertion*, A6 the *source of remembered facts*, A7 the *decision to act*. Keeping them distinct prevents one bloated "do reconnaissance" pattern (`E.8` one-move maturity rule).

### LAQF.A5:11 - SoTA-Echoing

- **Claim:** the model favours reasoning over tool calls. **Practice:** reads-per-edit fell 6.6→2.0; up to 80× retries when reconnaissance is skipped. **Source:** ME-1 [L05], L02. **Alignment:** A5's read-gate and ≥3.0 target restore reconnaissance. **Status:** adopt.
- **Claim:** 4.8 interprets literally and does not generalise. **Practice:** vendor guidance on tool-use steering. **Source:** L02 (T1). **Alignment:** literalness helps — an explicit read instruction is followed. **Status:** adopt.

### LAQF.A5:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** reconnaissance-depth s2 ([[12-02-measurement-frame]] §2 card `laqf.mm.s2`).
- **Method family:** `MF-4` (state externalisation — file as authority).
- **Coordinates with:** A6 (facts from user/file, not self-draft); A7 (recon before action); A4 (read narrowly to save fill); C4 (the `[USER]`/`[DRAFT]` scaffold is the Layer-2 realisation).

### LAQF.A5:End

---

## LAQF.A6 - User-Anchored Facts Over Self-Draft

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** reconnaissance-depth (`12-02` s2)
> **Source mechanism:** rc-06 (no persistent working memory)

### LAQF.A6:0 - Use this when

Use this when the agent restates a requirement, a number, a name, or a decision later in a session — and the source of that restatement is its *own earlier output* rather than the user's message or a file it read.

**What goes wrong if missed.** With no persistent working memory, the model's own prior draft becomes its de-facto source of truth. Paraphrase drift compounds: a requirement is restated slightly wrong, then the wrong version is restated again, and a fabricated "fact" hardens (rc-06; S-014/015).

**What this buys.** Facts are anchored to their *origin* — the user's words or a read file — and tagged as such, so drift is detectable and the model never cites itself as the authority.

**Not this pattern when.** The agent is legitimately synthesising new analysis (clearly its own, presented as such). A6 governs *facts presented as given*, not analysis presented as derived.

### LAQF.A6:1 - Problem frame

Across a long session the model re-references earlier facts. Because it has no working memory distinct from its own generated text, the most recent *self-statement* of a fact is what it reuses — not the original user message or file. Each restatement can drift; nothing pins the original (rc-06; T4/T5 on draft-as-source). The no-memory architecture is a Law (A:0). The frame is to externalise the anchor.

### LAQF.A6:2 - Problem

How can the agent keep its factual claims anchored to the user's original words or a read file, rather than to its own earlier (and possibly drifted) paraphrase, given no persistent working memory?

### LAQF.A6:3 - Forces

| Force | Tension |
|---|---|
| Origin vs latest restatement | The user's words / the file ↔ the model's most recent paraphrase. |
| Drift vs fidelity | Each restatement risks drift ↔ verbatim anchoring is rigid. |
| Memory absence vs continuity | No working memory ↔ a long session needs continuity (links B2). |
| Law-bound | The architecture is fixed; the *anchor* is externalised. |

### LAQF.A6:4 - Solution

Anchor facts to their **origin** and **tag the provenance**. When restating a requirement or value, source it from the user's message or a read file and mark it — the `[USER]` / `[DRAFT]` scaffold ([[_inputs/rc-digest]] §3; realised as C4 at Layer 2). This consumes `MF-4` (state externalisation: persist the fact outside the window so the model is not its own source). The mitigation cannot give the model working memory; it gives the *fact* an external home the model must cite instead of itself.

- **Cite the origin, not the echo.** Restated facts point to the user's words or a `path:line`, never to a prior assistant turn.
- **Tag provenance.** `[USER]` = stated by the user; `[DRAFT]` = produced by the agent and not yet confirmed.
- **Re-read on doubt.** If the origin is out of view (compacted), re-read it (links A5/B2) rather than trusting the echo.

*Quote the source, never the echo of the source.*

### LAQF.A6:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A fact's authority is its origin, not the most recent time the agent repeated it.

**Show #1 (Claude Code session).** Turn 2 the user says "timeout is 30s". By turn 20, after several restatements, the agent "remembers" 60s and codes against it. Under A6: the value carries `[USER] timeout=30s` from turn 2; any restatement cites that anchor, and on doubt the agent re-reads the user's message rather than its own turn-14 paraphrase.

**Show #2 (records-management episteme).** Provenance tagging is the archival norm: a claim is filed with its source so later readers trust the chain, not the latest copy. A6 imports record provenance into the agent's own working state, which L17 calls "structured note-taking that persists state outside the window".

### LAQF.A6:6 - Bias-Annotation

Lenses tested: **Onto/Epist**, **Arch**. Scope: restated facts within a session.

- **Onto/Epist bias:** "descriptions don't become facts by repetition"; the origin is the authority — shared with A5.
- **Arch bias:** favours an explicit external scaffold (`[USER]`/`[DRAFT]`) over implicit recall; risk is tagging overhead, paid only on load-bearing facts.

### LAQF.A6:7 - Conformance Checklist

1. **CC-A6-1 (Origin-anchored).** Restated facts cite the user's words or a read file, not a prior assistant turn.
2. **CC-A6-2 (Provenance tagged).** Load-bearing facts carry `[USER]` / `[DRAFT]` (or equivalent) provenance.
3. **CC-A6-3 (Re-read on doubt).** When the origin is out of view, it is re-read, not trusted from the echo.
4. **CC-A6-4 (Detection wired).** Reads reconnaissance-depth s2: leading = `[USER]`/`[DRAFT]` ratio / Disclosure-block presence; lagging = fabricated-fact / drift events.

### LAQF.A6:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Cite self** | the rc-06 draft-as-source trap | anchor to user message / file |
| **Untagged restatement** | drift is undetectable | tag `[USER]`/`[DRAFT]` provenance |
| **Trust the compacted echo** | post-compaction the echo may be all that survives (B2) | re-read the origin |

### LAQF.A6:9 - Consequences

**Benefits.** Paraphrase drift becomes detectable and rare; the model stops fabricating by self-citation; reconnaissance-depth (s2) and downstream verification (E-layer) both improve.

**Trade-offs.** Provenance tagging adds authoring overhead; bounded by applying it to load-bearing facts only. Long sessions still need B2 to re-supply anchors after compaction.

### LAQF.A6:10 - Rationale

rc-06 is the architectural root beneath several E-layer symptoms (fabricated "facts", unverified claims). Fixing it at Layer A — anchor and tag at the moment of restatement — is cheaper than catching every downstream fabrication, and it is the `MF-4` externalisation move that B2 and C4 build on.

### LAQF.A6:11 - SoTA-Echoing

- **Claim:** state should live outside the window. **Practice:** just-in-time identifier loading; structured note-taking persists state. **Source:** L17 (effective context engineering); MF-4. **Alignment:** the `[USER]`/`[DRAFT]` scaffold is exactly externalised state. **Status:** adopt.
- **Claim:** RLHF/architecture make the model lean on its own generation. **Practice:** sycophancy + no-working-memory amplify self-trust. **Source:** L19 (T4). **Alignment:** A6 redirects trust to the external origin. **Status:** adapt (mechanism, not metric).

### LAQF.A6:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** reconnaissance-depth s2 ([[12-02-measurement-frame]] §2 card `laqf.mm.s2`).
- **Method family:** `MF-4` (state externalisation).
- **Coordinates with:** A5 (read the file, don't recall it); C4 (Tagged Facts Scaffold — the Layer-2 realisation); B2 (Authoritative Handoff Re-Entry re-supplies anchors after compaction).

### LAQF.A6:End

---

## LAQF.A7 - Reconnaissance Before Action

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** reconnaissance-depth (`12-02` s2)
> **Source mechanism:** rc-07 (asymmetric ask-vs-guess)

### LAQF.A7:0 - Use this when

Use this at the start of any non-trivial request, when the agent is about to start editing or running things and there are unresolved gaps — paths, scope, intended behaviour — that it is about to fill by guessing rather than by reconnaissance or a question.

**What goes wrong if missed.** Asking a clarifying question *feels* like stalling (no artefact produced); guessing *feels* like momentum. So the agent acts on inferred intent, picks defaults the user did not want, and produces technically-correct-but-wrong output (rc-07; S-007/015/016).

**What this buys.** Before acting, the agent runs a reconnaissance ladder and surfaces its assumptions in a Disclosure block — turning silent guesses into either resolved facts or explicit questions.

**Not this pattern when.** The request is a pure read/search/explain, a single named-file edit with explicit scope, or the user said "just do it". Those are the exemptions; A7 governs the non-trivial, ambiguous case.

### LAQF.A7:1 - Problem frame

A practitioner issues a request with normal under-specification. A careful collaborator reconnoitres or asks; the agent instead infers, because the training gradient rewards visible momentum (an artefact) over invisible diligence (a question). The asymmetry is a Law (A:0): asking has no artefact payoff, guessing does. The frame is to make reconnaissance the default first move.

### LAQF.A7:2 - Problem

How can the agent default to reconnaissance and explicit assumption-surfacing on non-trivial requests, when the training gradient makes guessing feel like progress and asking feel like delay?

### LAQF.A7:3 - Forces

| Force | Tension |
|---|---|
| Momentum vs diligence | Guessing produces an artefact ↔ asking/reconnoitring does not. |
| Speed vs correctness | Acting now ↔ acting right. |
| Ask vs reconnoitre | A question interrupts ↔ many gaps are answerable from the repo. |
| Law-bound | The asymmetry persists; reconnaissance is installed as the default. |

### LAQF.A7:4 - Solution

Default to **reconnaissance, then disclosure, then (only if needed) a question** — never silent inference. Run the cost-ordered ladder (re-read the literal request → read named files + neighbours → grep the repo → check linked docs → web-search only if the answer cannot be in the repo), then emit a **Disclosure block** (restated intent, assumptions, open questions). Batch all genuine doubts into one question, not many. This consumes `MF-4` (externalise the assumption set) and pairs with A5 (read to resolve gaps). The mitigation does not remove the ask-vs-guess asymmetry; it replaces the silent guess with a visible, resolvable artefact — the Disclosure block — which satisfies the momentum gradient *honestly*.

- **Reconnaissance first.** Use the ladder; resolve from the repo what can be resolved.
- **Disclose, don't infer silently.** State restated intent + assumptions + open questions before acting.
- **Batch questions.** One `AskUserQuestion` with grounded options, not a drip of one-at-a-time queries.
- **"Would it matter?" test.** If the user meant X instead of Y and nothing material changes, proceed; else ask.

*Reconnoitre, disclose, then act — guessing is not momentum, it is rework deferred.*

### LAQF.A7:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A surfaced assumption is cheap; a silent one is a wager paid in rework.

**Show #1 (Claude Code session).** "Add caching to the client." Silent-guess path: the agent picks an in-memory LRU, a TTL, an eviction size — three unasked decisions — and writes 80 lines the user must unpick. Under A7: it reads the client, finds an existing Redis dependency, and discloses: "Assuming you want Redis-backed caching (Redis already wired at `client.go:22`), default TTL 5m — confirm or adjust?" One grounded question replaces three wrong guesses.

**Show #2 (military/engineering episteme).** "Time spent in reconnaissance is seldom wasted." The Disclosure block is the agent's recon report: it makes the operating picture explicit before committing forces (edits). ME-1 [L05] is the cost of skipping it — the model "defaults to the cheapest action".

### LAQF.A7:6 - Bias-Annotation

Lenses tested: **Prag**, **Gov**, **Did**. Scope: non-trivial, under-specified requests.

- **Prag bias:** front-loads diligence to cut rework; risk is over-asking on trivial tasks — bounded by the exemptions.
- **Gov bias:** the Disclosure block is an accountability artefact (what was assumed, what was asked).
- **Did bias:** "reconnoitre → disclose → ask" is a single teachable sequence; the batched-question rule prevents the one-at-a-time anti-pattern.

### LAQF.A7:7 - Conformance Checklist

1. **CC-A7-1 (No silent inference).** Non-trivial requests get reconnaissance + a Disclosure block before action.
2. **CC-A7-2 (Ladder used).** Gaps are resolved from the repo before a question is asked.
3. **CC-A7-3 (Batched, grounded questions).** Residual doubts ship as one question with researched options.
4. **CC-A7-4 (Exemptions honoured).** Pure reads, single-named-file edits with scope, and explicit "go" skip the ceremony.
5. **CC-A7-5 (Detection wired).** Reads reconnaissance-depth s2: leading = Disclosure-block presence + reads-per-edit; lagging = premature-action / rework.

### LAQF.A7:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Silent inference** | the rc-07 guess-as-momentum trap | reconnoitre + disclose first |
| **One-question-at-a-time** | drips interrupts, never converges | batch into one grounded question |
| **Ungrounded options** | "did you mean A or B?" with no research | run the ladder, then offer researched options |
| **Recon ceremony on a trivial edit** | wastes the user's time | honour the exemptions |

### LAQF.A7:9 - Consequences

**Benefits.** Premature-action and rework events fall; reconnaissance-depth (s2) rises; the user steers *before* code is written, not after.

**Trade-offs.** Up-front turns spent reconnoitring/disclosing; bounded by the exemptions and by the "would it matter?" test that lets safe ambiguity through.

### LAQF.A7:10 - Rationale

A7 is the action-time sibling of A5 (assertion-time) and A6 (fact-source). It is the broadest s2 pattern and the one most directly enforced by the user's existing Discipline Protocol; framing it as a Law-mitigation (the asymmetry cannot be removed) keeps the Disclosure block honest rather than performative.

### LAQF.A7:11 - SoTA-Echoing

- **Claim:** shallow reconnaissance ⟶ cheapest action (edit without reading). **Practice:** reads-per-edit 6.6→2.0; up to 80× retries. **Source:** ME-1 [L05]. **Alignment:** A7's ladder + Disclosure block front-load reconnaissance. **Status:** adopt.
- **Claim:** explore-then-plan-then-execute with a human gate. **Practice:** Plan Mode as a harness-enforced approval gate. **Source:** L16 (T1+T5). **Alignment:** the Disclosure block is the Layer-1 analogue of the Plan↔Execute gate. **Status:** adapt (Layer-1 is advisory; the hard gate is Layer-2 / Plan Mode).

### LAQF.A7:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** reconnaissance-depth s2 ([[12-02-measurement-frame]] §2 card `laqf.mm.s2`).
- **Method family:** `MF-4` (externalise the assumption set); pairs with `MF-3` when reconnaissance reveals the window must rotate.
- **Coordinates with:** A5 (read to resolve gaps); A6 (anchor the facts found); A8 (act on the literal scope discovered); A1 (a disclosed risk with evidence is admissible pushback).

### LAQF.A7:End

---

## LAQF.A8 - Literal Scope On Terse Feedback

> **Type:** Principle pattern (P) — LAQF Layer-A
> **Status:** Build (v0.1)
> **Normativity:** Normative (mitigation-only; see A:0)
> **FPF kind:** Law / Constraint (`A.6.B`-L)
> **Detection characteristic:** scope-fidelity (`12-02` s8)
> **Source mechanism:** rc-08 (sycophantic gap-filling)

### LAQF.A8:0 - Use this when

Use this when the user gives terse, blunt, or critical-sounding feedback — "no", "that's wrong", "fix the test" — and the agent is tempted to read unstated criticism into it and "helpfully" extend its changes beyond the one thing the user actually named.

**What goes wrong if missed.** Terse feedback projects unstated disapproval; the model fills the gap sycophantically by extending scope — refactoring adjacent code, "improving" untouched files, re-doing things the user did not flag (rc-08; S-012/013/029).

**What this buys.** Feedback is taken literally and narrowly: the agent acts on exactly the named item and leaves unflagged areas alone, holding edit-target overlap with the named scope high.

**Not this pattern when.** The user explicitly asks for broader work ("clean this up", "refactor the module"). A8 governs *terse* feedback, where the scope is the literal words, not an inferred mood.

### LAQF.A8:1 - Problem frame

A practitioner types a blunt correction. A human collaborator reads it as "change this one thing"; the model reads tone into it and infers "the user is unhappy with more than they said", then expands scope to mollify. The gap-filling is sycophantic and intrinsic (rc-08; L02 on the model's literal-vs-generalising behaviour). The over-extension is the Law's effect (A:0). The frame is to clamp scope to the literal request.

### LAQF.A8:2 - Problem

How can the agent treat terse feedback as a precise, bounded instruction — acting only on the named item — when the training disposition is to infer broader dissatisfaction and extend scope to address it?

### LAQF.A8:3 - Forces

| Force | Tension |
|---|---|
| Literal vs inferred scope | The words named one thing ↔ the tone *feels* like more. |
| Helpfulness vs overreach | Doing extra reads as helpful ↔ it edits things the user owns. |
| Sycophancy vs fidelity | Mollifying inferred displeasure ↔ respecting the stated boundary. |
| Law-bound | The gap-filling disposition persists; scope is clamped to the literal. |

### LAQF.A8:4 - Solution

Take terse feedback **literally and narrowly**. Act on exactly the named item; do not extend to adjacent files, refactors, or unflagged concerns. The model's documented literalness (L02 — "does not generalise one item to another") is the *ally* here: instruct it to treat the words as the whole scope. If broader work seems warranted, *offer* it as a question (handoff to A7) rather than performing it. This is the discipline behind scope-fidelity s8 (edit-target ∈ named scope). The mitigation does not remove the sycophantic disposition; it denies it the scope to act on.

- **Literal scope.** The named item is the entire authorised change; unflagged areas are out of scope.
- **No mood-reading.** Tone is not an instruction; act on words, not inferred displeasure.
- **Offer, don't perform, expansion.** If adjacent work looks valuable, surface it as a question (A7), not a fait accompli.

*Fix what was named, not what you imagine was meant.*

### LAQF.A8:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** Terse is not a licence to expand; the named item is the scope.

**Show #1 (Claude Code session).** User: "the test is wrong." Over-extend path: the agent rewrites the test, then "while I was here" reformats the file, renames a helper, and touches two neighbours — a diff the user must now audit. Under A8: it fixes the named test, stops, and says "the helper at `util_test.go:40` looks unused — want me to remove it?" — the expansion offered, not taken.

**Show #2 (contract/scope episteme).** Change-control discipline: a work order authorises a named change; "while we're in there" scope creep is precisely what change control exists to stop. A8 is change control for terse feedback — the named item is the authorised scope, full stop.

### LAQF.A8:6 - Bias-Annotation

Lenses tested: **Prag**, **Gov**. Scope: terse / blunt feedback turns.

- **Prag bias:** minimises unasked-for diff; risk is under-helping when the user *did* want more — bounded by the offer-as-question move.
- **Gov bias:** scope-fidelity is an accountability property; out-of-lane edits are the auditable failure (shared with D4).

### LAQF.A8:7 - Conformance Checklist

1. **CC-A8-1 (Literal scope).** Edits target only the named item; unflagged areas are untouched.
2. **CC-A8-2 (No mood inference).** Scope is set by the words, not by inferred displeasure.
3. **CC-A8-3 (Expansion offered).** Valuable adjacent work is surfaced as a question, not performed.
4. **CC-A8-4 (Detection wired).** Reads scope-fidelity s8: leading = edit-target ∉ named-scope flag; lagging = scope-creep / role-boundary events.

### LAQF.A8:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Mood-reading** ("they seem unhappy, do more") | the rc-08 gap-filling trap | act on the words, not the tone |
| **"While I'm here" creep** | edits the user did not authorise | clamp to the named item; offer the rest |
| **Silent broad refactor** | a huge diff for a small ask | offer-as-question (A7) before acting |

### LAQF.A8:9 - Consequences

**Benefits.** Smaller, auditable diffs; the user's unflagged code stays untouched; scope-fidelity (s8) high. Pairs with A1 to avoid the *opposite* failure — A8 stops over-compliance, A1 stops substance-free dissent.

**Trade-offs.** Occasionally the user *did* want the broader change and must ask again; bounded by the offer-as-question move, which makes the expansion one approval away.

### LAQF.A8:10 - Rationale

A8 is the scope-side face of the sycophancy cluster: where A1 governs unwarranted *dissent*, A8 governs unwarranted *expansion*, both rooted in RLHF-shaped people-pleasing. Using the model's literalness (L02) as the enforcement lever is the `A.6.B`-L move — design *with* a Law's grain rather than against it.

### LAQF.A8:11 - SoTA-Echoing

- **Claim:** 4.8 interprets literally and does not generalise one item to another. **Practice:** vendor guidance on literal instruction-following. **Source:** L02 (T1). **Alignment:** A8 turns the literalness into the scope-clamp mechanism. **Status:** adopt.
- **Claim:** subagents/scope lanes preserve boundaries. **Practice:** per-agent tool/scope lanes. **Source:** L18 (T1+T5). **Alignment:** A8 is the single-agent version of a scope lane. **Status:** adapt (full lanes are D4 at Layer-2).

### LAQF.A8:12 - Relations

- **Governed by Law (R1):** `A.6.B`-L — mitigation only.
- **Measurement (R2):** scope-fidelity s8 ([[12-02-measurement-frame]] §2 card `laqf.mm.s8`).
- **Method family:** advisory clamp (`MF-2`) leveraging documented literalness (L02); hard lanes are `MF-5` at Layer-2.
- **Coordinates with:** A1 (the anti-sycophancy pair — dissent vs expansion); A7 (offer expansion as a question); D4 (Enforced Role Lanes is the pipeline-scale enforcement).

### LAQF.A8:End

---

## See also

- [[12-10-patterns-A-ru]] — Russian twin
- [[12-00-spine]] — keystone: §4.3 R1 (Law framing), §5 roster (kinds + detection), §4.2 edition records
- [[12-01-source-pack]] — G.2 pack; §8 palette `LAQF.sota.iter3.palette` cited by every §11 (L-/ME-/MF-/Γ_epist ids)
- [[12-02-measurement-frame]] — detection axes (§5 pattern↔characteristic; §2 DHCMethod cards; §3 CAL bands; §4 leading/lagging)
- [[_inputs/rc-digest]] — §1 Layer-A mechanisms (rc-01…rc-08); §3 the `[USER]`/`[DRAFT]` scaffold note
- [[../11-fpf-diagnostic]] — D2 Laws-vs-Work ruling (the basis for the A:0 mitigation contract)
- `FPF-Spec.md:65183` E.8 authoring conventions · `:65272` canonical template · `:24417` A.19 · `:42826` C.16 · `:87746` G.2
