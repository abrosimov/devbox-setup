---
tags: [claude-improvements, fpf-seminar, naming, katoptron, f18]
seminar-iteration: 2
created: 2026-06-28
status: decided
method: FPF F.18 — Local-First Unification Naming Protocol
decision: Κάτοπτρον (Katoptron)
relates-to: choosing_name.md
supersedes: none
---

# Choosing the project name — independent F.18 run

Iteration 0 ([[choosing_name]]) selected **Κάτοπτρον** using three judgement principles
(A.7 Strict Distinction, A.6.B Laws vs Work, A.15 Work). This file re-runs the naming
question through **F.18 — Local-First Unification Naming Protocol** as an *independent*
exercise: the protocol is applied without presupposing the earlier answer, so the result
is free to confirm Κάτοπτρον, refine it, or replace it.

F.18 is a different instrument from the iteration-0 principles. Where A.7/A.6.B/A.15 ask
*"what kind of thing is this and what may its name claim?"*, F.18 asks *"what is the
durable, reusable, collision-checked label for an already-governed value, chosen from a
visible candidate set on declared ordinal dimensions, with lineage recorded?"*
(`FPF-Spec.md:85840`, `:85914`).

> **Spec note.** The seminar refers to this protocol as "F18 / F.48". The FPF
> specification contains **F.18 — Local-First Unification Naming Protocol**
> (`FPF-Spec.md:344`, `:85840`); there is no F.48 (the F-series ends at F.19). The
> filename keeps the literal `_48` requested for the seminar; the *method* applied
> throughout is F.18.

## Step 1 — Recover the governed value (F.18:0, F.18:4 step 1)

F.18's first move is to recover the governed value and its governing pattern *before*
choosing a label, so the name does not smuggle in ontology (`FPF-Spec.md:85853`).

| Question (F.18:4.1 invariants) | Answer for this project |
|---|---|
| **Governed value first** | The `claude_improvements/` project: an ongoing **diagnostic-and-mitigation Work** (`A.15`) that produces and consumes a **reflective corpus** characterising Claude Code's behavioural space (`A.19` CharacteristicSpace). 36 files, ~4900 lines, 41 symptoms → 30 root causes → 150+ fix proposals ([[../00-MoC]]). |
| **Governing pattern visible** | `A.15` (Work) for the activity; `A.19` (CharacteristicSpace) for the corpus; the durable label itself is chosen under `F.18`. |
| **Bounded context visible** | `AION_AUTOPOIESEON` workspace, `claude_improvements` project context. Not Core-facing, not cross-context — so `F.17` public term-row publication is **not** invoked (F.18:4.4). |
| **Local sense visible** | "A reflective self-examination instrument for Claude Code's behaviour: symptoms are distortions in the mirror, root causes are the optics, the FPF seminar checks the mirror's own curvature." |

**The dual-kind tension (recorded explicitly).** The governed value reads two ways:

- **Instrument reading** — the project *is* a reflective surface / corpus. The corpus
  refers to itself this way ("the Katoptron catalogue", "mirror") in
  [[11-fpf-diagnostic]] and [[../00-MoC]]. A noun naming an instrument fits.
- **Work reading** — the project *is* ongoing activity (diagnose, prescribe, audit). An
  activity- or method-shaped name fits better.

This choice of reading drives the **MorphologicalActionFit** dimension below, so it is
declared up front rather than hidden inside scoring. Iteration 0 settled on the
*instrument* reading (its decision-rationale point 1: "Katoptron names the *thing the
project is* — a reflective surface"). This run adopts the same primary reading **and**
carries the Work reading as a recorded residual risk (see Selection rationale and
RefreshCondition).

## Step 2 — Mint / Reuse / DocumentLegacy decision (F.8 via F.18:4)

**MintNew** (the F.18 default, `FPF-Spec.md:13640`). No externally fixed standard label
exists; there is nothing to `DocumentLegacy`. Iteration 0's Κάτοπτρον is an in-house
prior choice, not an external standard — this run is free to re-mint.

## Step 3 — Candidate set (F.18:4.3)

F.18 requires 5–10 candidates from **at least two head-term families**, judged on
ordinal dimensions, **never averaged into one score** (`FPF-Spec.md:85974`–`:85981`).

### Family A — Optical / reflection
- **A1 · Κάτοπτρον (Katoptron)** — mirror; reflective *instrument*. κατά + ὄπτομαι = "to look at oneself".
- **A2 · Κατοπτρισμός (Katoptrismos)** — reflection / mirroring *as a process* (the -ισμός activity suffix). Also the ordinary-Greek sense "mirage".
- **A3 · Δίοπτρα (Dioptra)** — a *sighting / measuring* instrument (seeing-through, not seeing-self).

### Family B — Diagnostic / medical
- **B1 · Ἀνάμνησις (Anamnesis)** — patient history / recollection.
- **B2 · Διάγνωσις (Diagnosis)** — discernment-through; names the diagnostic *act*.

### Family C — Dialectic / examination
- **C1 · Ἔλεγχος (Elenchus)** — Socratic cross-examination; names an examination *activity/method*.

### Family D — Paradox
- **D1 · Φάρμακον (Pharmakon)** — remedy that is also poison.

## Step 4 — Ordinal scoring and NQD-front (F.18:4.3)

Dimensions are F.18's own lexical-quality vector (`FPF-Spec.md:25024`,
`:85976`–`:85979`): **SemanticFidelity** (preserves the governed value without adding /
losing conditions), **CognitiveErgonomics** (reader can say and remember it),
**MorphologicalActionFit** (word-shape fits the kind being named), **AliasRisk** (will a
careful reader import a wrong sense — *lower is better*).

Scale is ordinal: `High / Med / Low`. Values are **not** averaged.

| # | Candidate | SemanticFidelity | CognitiveErgonomics | MorphologicalActionFit | AliasRisk *(low = good)* |
|---|---|---|---|---|---|
| A1 | Κάτοπτρον | **High** — mirror = self-examination; "catoptrics" (the science of reflection) carries extensibility | **High** | **High** for the *instrument* reading | **Low** — "catoptric" is obscure enough not to import a wrong prototype |
| A2 | Κατοπτρισμός | High — reflection-as-process | Med — longer, less crisp | High for the *Work* reading | **High** — "mirage" connotes *illusion / unreal*, which undercuts a diagnostic's truth claim |
| A3 | Δίοπτρα | Med — sighting through, not reflecting self | Med | Med | Med — surveying-instrument prototype |
| B1 | Ἀνάμνησις | Med — memory-only; the project is broader | Med | Med | High — medical + Platonic baggage |
| B2 | Διάγνωσις | Med — names only the diagnostic half; the project also prescribes and audits | High — internationally familiar | High for the *Work* reading | High — pure clinical prototype |
| C1 | Ἔλεγχος | Med — names the *method*, not the object | Med | High for the *Work* reading | Med — confrontational tone may overread |
| D1 | Φάρμακον | Med — names the *tension*, not the project | Med | Low — names a *substance*, not work or instrument | High — later sense "witchcraft / poison" |

**Dominance rule.** Candidate *X* dominates *Y* iff *X* is at least as good as *Y* on all
four dimensions and strictly better on at least one (AliasRisk inverted). The **NQD-front**
is the set of non-dominated candidates.

**Front under the primary (instrument) reading:**

- **A1 Κάτοπτρον** — non-dominated. Nothing beats it on any dimension under this reading.
- A2, A3, B1, B2, C1, D1 — each is dominated by A1: A1 matches or exceeds them on every
  dimension. (E.g. A1 vs A2: equal SemanticFidelity, A1 wins CognitiveErgonomics and
  AliasRisk, equal-or-better MorphologicalActionFit → A1 dominates A2. A1 vs C1: A1 wins
  SemanticFidelity, CognitiveErgonomics and AliasRisk, ties MorphologicalActionFit only
  under the *Work* reading → A1 dominates C1 under the instrument reading.)

→ **Front = { Κάτοπτρον }** (a legitimate singleton: one candidate dominates).

**Front under the alternative (Work) reading** — recorded, not selected:

- If the governed value is privileged as *ongoing Work* rather than *instrument*, the
  MorphologicalActionFit column flips for the activity-shaped names, and the front opens
  to **{ Κάτοπτρον, Ἔλεγχος, Κατοπτρισμός }** — Ἔλεγχος and Κατοπτρισμός each then beat
  Κάτοπτρον on MorphologicalActionFit while losing on AliasRisk, so none dominates.

## Step 5 — Selection and Name Card (F.18:4.2)

Selected: **Κάτοπτρον**, with the residual MorphologicalActionFit risk stated, as F.18
requires ("one candidate can win even when it is not perfect, but the SelectionRationale
must say what it buys and what risk remains", `FPF-Spec.md:85983`).

```text
NameCard:
  NameCardId:        katoptron-f18-iter2
  GovernedValueRef:  claude_improvements project — reflective diagnostic Work (A.15)
                     producing a behavioural CharacteristicSpace corpus (A.19)
  GoverningPatternRef: A.15 (Work) + A.19 (CharacteristicSpace); label under F.18
  BoundedContextRef: AION_AUTOPOIESEON / claude_improvements
  LocalSenseRef:     "reflective self-examination instrument for Claude Code behaviour"
  TechLabel:         Κάτοπτρον (Katoptron)
  PlainLabel:        the Katoptron catalogue / the mirror
  CandidateSet:      A1 Κάτοπτρον; A2 Κατοπτρισμός; A3 Δίοπτρα;
                     B1 Ἀνάμνησις; B2 Διάγνωσις; C1 Ἔλεγχος; D1 Φάρμακον
  RejectedCandidates:
    - Κατοπτρισμός: AliasRisk High — "mirage" connotes illusion, corrodes a diagnostic's
      truth claim; dominated by Κάτοπτρον on the instrument reading.
    - Ἔλεγχος / Διάγνωσις: name a method or a half of the work, not the object; high
      clinical / confrontational AliasRisk. Different governed values, not worse synonyms.
    - Ἀνάμνησις: too narrow (memory only); high baggage.
    - Φάρμακον: names the paradox, not the project; substance-morphology mismatch; high
      "poison" AliasRisk.
    - Δίοπτρα: "sighting through", not "reflecting self" — semantic drift from self-examination.
  SelectionRationale:
    Buys — top SemanticFidelity (mirror = self-examination; catoptrics gives an
    extensible scientific frame for new symptoms / optics / curvature checks); lowest
    AliasRisk on the front; top CognitiveErgonomics; lineage continuity with iteration 0
    (no rename churn). Independently reached here on F.18's four dimensions — not inherited.
    Residual risk — MorphologicalActionFit is top only under the *instrument* reading of
    the governed value. If the project's centre of gravity shifts from reflection to
    active remediation as its primary mode, an activity- or method-shaped name (Ἔλεγχος)
    would fit better and the front would reopen.
  BridgeRefs:        AION_AUTOPOIESEON (self-creation); MNEMOSYNE_PERISTASEOS (memory of
                     circumstances) — see [[choosing_name]] ecosystem links.
  UnifiedTermRowRef: none — local to this workspace; F.17 not invoked (F.18:4.4).
  LineageEntries:
    - iter-0 (choosing_name.md): minted Κάτοπτρον via A.7 / A.6.B / A.15.
    - iter-2 (this file): independent F.18 run; confirms Κάτοπτρον on SemanticFidelity,
      CognitiveErgonomics, MorphologicalActionFit (instrument reading), AliasRisk.
  RefreshCondition:
    Reconsider when (a) the project's primary mode becomes active remediation rather than
    reflection; (b) the governing pattern of the governed value changes; or (c) repeated
    reader error treats "mirror" as "passive / no fixes".
```

## What this run adds over iteration 0

Two FPF instruments, applied independently, converge on the same name — which is the
strongest validation F.18 can offer for a name already in use. Beyond confirmation, this
run contributes three things iteration 0 left implicit:

1. **A visible candidate set with a dominance rule** — iteration 0 compared four
   candidates in prose; F.18 makes the front and the non-dominated reasoning explicit and
   auditable.
2. **AliasRisk as a first-class axis** — it surfaces a concrete demerit (Κατοπτρισμός =
   "mirage") that the prose comparison did not name.
3. **A RefreshCondition** — the instrument-vs-Work tension that iteration 0 flagged as a
   "productive weakness" is now an operational trigger for re-opening the name, not just a
   rhetorical note.

## See also

- [[choosing_name]] — iteration 0 (A.7 / A.6.B / A.15 naming)
- [[seminar_timeline]] — seminar MOC
- [[11-fpf-diagnostic]] — first structural audit
- [[../00-MoC]] — main catalogue hub
- `FPF-Spec.md:85840` — F.18 Local-First Unification Naming Protocol
