---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, keystone, e4-dpf]
seminar-iteration: 3
created: 2026-06-28
status: keystone
method: FPF E.4.DPF (authoring spine) · E.4.PFAD (architecture decision) · E.4.PFR (relation/edition discipline) · F.18 (naming) · E.5.3 (unidirectional dependency) · G.11 (currentness)
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-00-spine-ru]]"
---

# LAQF — keystone spine (E.4.DPF)

This is the keystone of the **LLM-Agent Quality Principle Framework (LAQF)**, authored through the FPF Domain-Principle-Framework spine (`E.4.DPF`, `FPF-Spec.md:64163`). It fixes the parts of the spine the rest of the framework depends on — context, architecture decision, ratified name, edition and relation discipline, the selected 30-pattern set, and the refresh route — so the pattern bodies (S3–S6) and the measurement frame (S2) can be authored against a stable foundation.

The pattern bodies do **not** live here. This file is the architecture, not the catalogue. It is a *reading and authoring* artefact: it creates no imports, APIs, runtime dependencies, or build semantics (`E.4.PFR`, `FPF-Spec.md:64478`).

## §0 DPF spine coverage (E.4.DPF:4, `FPF-Spec.md:64247`)

The eleven-step spine, and where each step is owned. This file (S1) fixes the keystone steps; the remainder are forward-referenced to later sessions per [[PROGRESS]] §7.

| Step | E.4.DPF spine element | Owner | State |
|---|---|---|---|
| 1 | Context declaration | this file §1 | ✅ S1 |
| 2 | Source pack (`G.2`) | [[12-01-source-pack]] | S2 |
| 3 | Architecture decision (`E.4.PFAD`) | this file §2 | ✅ S1 |
| 4 | Name preparation (`E.10` / `F.18`) | this file §3 | ✅ S1 |
| 5 | Carrier admission (`C.33`–`C.35`) | this file §4.4 (note); full at S7 | ◐ S1 note |
| 6 | Pattern drafting (`E.8`) | [[12-10-patterns-A]] … [[12-15-patterns-F]] | S3–S6 |
| 7 | Relation & edition discipline (`E.4.PFR`) | this file §4 (per-pattern relations ship with patterns) | ✅ S1 |
| 8 | Quality cycle (`E.22`/`E.21`/`E.23`) | [[README]] + QA | S7 |
| 9 | Admission review (`E.19`) | [[README]] + QA (only if admission claimed) | S7 |
| 10 | Local-monolith landing | this folder; [[README]] first-entry carrier | S7 |
| 11 | Currentness route (`G.11`) | this file §6 | ✅ S1 |

---

## §1 Context declaration (E.4.DPF:1, `FPF-Spec.md:64247`)

| Slot | Declaration |
|---|---|
| **Bounded context** | `AION_AUTOPOIESEON` workspace → `claude_improvements` project → FPF seminar **iteration 3**. Built on the Κάτοπτρον catalogue ([[../../00-MoC]]) and its seminar audits ([[../11-fpf-diagnostic]], [[../choosing_name_with_fpf_48]]). |
| **Subject domain** | Troubleshooting and quality improvement of **LLM coding agents** — Claude Code as the grounding instance, but Layer-1 patterns are context-independent. |
| **Intended reader** | An FPF-literate practitioner improving an LLM coding agent's behaviour; secondarily the maintainer of this user's `dot_claude/` realisation (Layer 2). No prior FPF-developer knowledge assumed for first use (`E.4.DPF` didactic characteristic, `FPF-Spec.md:64271`). |
| **First use** | Select and apply quality patterns to diagnose, mitigate, and verify agent failures **within a finite attention/context budget** — the binding constraint surfaced by [[../11-fpf-diagnostic]] D1. |
| **Non-use boundary** | Not a benchmark suite, not a patch to Claude's weights, not a generic prompt-engineering guide. Layer-A patterns **mitigate Laws, never eliminate them** ([[../11-fpf-diagnostic]] D2). The framework **never lands into `FPF-Spec.md` / FPF Core** (`E.5.3`, `FPF-Spec.md:64474`). |

**Two-layer shape** (frozen decision #1, [[PROGRESS]] §2):

- **Layer 1 — Domain Principle edition (LAQF):** 30 reusable, context-independent quality patterns (`E.8`) + a measurement frame (`A.19` CharacteristicSpace + `C.16` operational bands).
- **Layer 2 — Local Practice edition:** this user's `dot_claude/` realisation (hooks, skills, settings), depending on Layer 1 via `E.5.3`.

---

## §2 Architecture decision — E.4.PFAD (`FPF-Spec.md:63995`)

One `PrincipleFrameworkArchitectureDecision@Context` relation, filled in the order prescribed at `FPF-Spec.md:64054`.

```text
PrincipleFrameworkArchitectureDecision@Context:
  frameworkDecisionId:        LAQF.PFAD.iter3-s1
  governedFrameworkRef:       LAQF — LLM-Agent Quality Principle Framework
                              (Layer-1 Domain edition + Layer-2 Local Practice edition)
  boundedContextRef:          AION_AUTOPOIESEON / claude_improvements / FPF-seminar:iter3
  frameworkEditionRef:        LAQF v0.1 (Domain Principle edition, status=build)
  fpfCoreEditionRef:          FPF-Spec.md (repo edit-tracked copy) — depends on
                              E.4 family, E.8, A.17–A.19, C.16, E.5.3, F.18, G.2, G.11
  decisionQuestion:           "What framework edition characterises and improves
                              LLM-coding-agent quality — as a two-layer DPF built with
                              E.4.DPF, landing as a local monolith, depending on FPF Core,
                              writing nothing into Core?"
  sourceBasisRefs:            [[../../01-symptoms-inventory]] (41 symptoms);
                              [[../../10-root-causes-overview]] (30 RCs);
                              [[../../02-external-research]] (~80 SoTA sources);
                              [[../../04-reflection-evidence]]; [[../11-fpf-diagnostic]] (D2 Laws-vs-Work);
                              [[_inputs/rc-digest]] (working digest)
  sotaSynthesisPackRefs:      → [[12-01-source-pack]] (G.2 pack, S2);
                              current anchors in [[_inputs/rc-digest]] §8
                              (IFScale; Laurenzo reads-per-edit; MRCR v2; tokenizer
                              densification; Anthropic brevity-cap reversion; CLAUDE.md
                              advisory ceiling; 509-line instruction stack)
  namingDecisionRefs:         this file §3 (F.18 Name Card `laqf-f18-iter3`);
                              ratifies frozen decision #2
  selectedPatternSetRefs:     this file §5 (30-pattern roster); published as
                              12-10…12-15 across S3–S6
  selectedPatternRelationRefs: this file §4.3 (representative records);
                              per-pattern §12 relations ship with each pattern
  publicationUnitRefs:        local monolith = folder `12-llm-agent-quality-dpf/`;
                              first-entry carrier = [[README]] (S7) + this spine
  dependencyAndEditionRefs:   this file §4.1–§4.2 (FrameworkEditionDependencyRecords +
                              FrameworkPackageManifest); direction per E.5.3
  qualityEvaluationRefs:      → E.22 framing + E.21 evaluation, S7 (E.4.PFAD:4 note,
                              `FPF-Spec.md:64066`)
  admissionReviewRefs:        → E.19, S7, only if admission / external-review readiness
                              is claimed (`FPF-Spec.md:64066`)
  rejectedAlternatives:       (a) single-layer (patterns without a Local edition) —
                              loses the user's realisation and the E.5.3 dependency story;
                              (b) landing into FPF-Spec.md — forbidden by E.5.3
                              (Core never depends on a domain edition);
                              (c) a subset of RCs as patterns — frozen #1 requires all 30;
                              (d) one measurement scale only — frozen #1 keeps both the
                              abstract A.19 space and the operational bands
  rationaleRefs:              [[../11-fpf-diagnostic]] (D1 budget constraint, D2 Laws-vs-Work,
                              D3 baseline, D4 WorkPlan DAG); [[PROGRESS]] §2 frozen decisions
  consequences:               30 full E.8 patterns is a large authoring effort — mitigated
                              by the S1–S7 session DAG + subagent delegation in S4–S6;
                              Layer-A solutions can only mitigate Laws (must be framed so);
                              bilingual EN + -ru doubles the surface
  localMonolithLandingRefs:   `12-llm-agent-quality-dpf/` (frozen #4, #5); not FPF-Spec.md
  sourceReturnConditions:     return to G.2 / [[../../02-external-research]] when a SoTA anchor
                              decays; return to E.4.PFAD if scope or layering changes
  refreshOrSupersessionConditions: new model generation; FPF Core edition bump;
                              Layer-2 dot_claude config drift; repeated reader error —
                              see §6 (G.11)
```

The decision projection (an ADR-like carrier via `C.32.ADR` / `E.17`) is **not** published here; per `FPF-Spec.md:64064` the decision relation must exist first — this section is that relation.

---

## §3 Name ratification — F.18 run for LAQF (`FPF-Spec.md:85840`)

Frozen decision #2 provisionally chose **LAQF**; `E.4.DPF:4` step 4 sends durable names to `F.18`. This is an **independent** F.18 run that ratifies — or would reopen — the name, mirroring the method of [[../choosing_name_with_fpf_48]].

### §3.1 Recover the governed value (F.18:4.1, `FPF-Spec.md:85926`)

| Invariant | Content |
|---|---|
| Governed value first | The Layer-1 **Domain Principle Framework edition** — 30 context-independent quality patterns + measurement frame for LLM coding agents. |
| Governing pattern visible | `E.4.DPF` owns the framework kind; `A.19`/`C.16` own the measurement value; the label itself is chosen under `F.18`. |
| Bounded context visible | `claude_improvements` / FPF-seminar:iter3. Local to this workspace — **`F.17` public term row not invoked** (`FPF-Spec.md:85985`, F.18:4.4). |
| Local sense visible | "A reusable pattern framework for characterising and raising the behavioural quality of LLM coding agents." |

**Mint/Reuse (F.8 via F.18):** MintNew. No external standard fixes this label; the provisional LAQF is an in-house prior, free to be re-minted or confirmed.

### §3.2 Candidate set — 8 candidates, 4 head-term families (F.18:4.3, `FPF-Spec.md:85974`)

- **Family A — Quality + Principle-Framework (DPF-kind-faithful):** A1 · **LLM-Agent Quality Principle Framework (LAQF)**; A2 · Coding-Agent Quality Principle Framework (CAQF); A3 · Agent Quality Principle Framework (AQPF).
- **Family B — single-characteristic:** B1 · LLM-Agent Reliability Framework (LARF); B2 · LLM-Agent Behaviour Framework.
- **Family C — practice / Work-shaped:** C1 · LLM-Agent Quality *Practice* Framework; C2 · Coding-Agent Improvement Framework.
- **Family D — ecosystem / Greek continuity:** D1 · Katoptron Quality Framework.

### §3.3 Ordinal scoring (F.18:4.3 — High/Med/Low, never averaged; AliasRisk: low = good)

| # | Candidate | SemanticFidelity | CognitiveErgonomics | MorphologicalActionFit | AliasRisk *(low good)* |
|---|---|---|---|---|---|
| A1 | LAQF | **High** — domain + characteristic + DPF kind | **High** — crisp 4-letter acronym | **High** — "Principle Framework" = DPF shape | **Low** — "LLM-Agent" dodges FPF `A.13` Agent; "Quality" mildly broad |
| A2 | CAQF | High — "Coding-Agent" most domain-precise | Med — CAQF less crisp; "C" ambiguous (Claude? Coding?) | High | Med — narrows to coding-only; Layer-1 is context-independent |
| A3 | AQPF | Med — drops the LLM/coding qualifier | Med | High | **High** — bare "Agent" collides with FPF `A.13` + agentic hype |
| B1 | LARF | Med — "Reliability" is one of eight characteristics | Med | High | Med — imports SRE/reliability-engineering prototype |
| B2 | — | Med — "Behaviour" vague | Med | Med | Med |
| C1 | — | Med — names quality | Med | Med | **High** — "Practice Framework" collides with this project's own **Layer-2 Local *Practice* edition** |
| C2 | — | Med — names the Work, not the artefact | Med | **Low** — Work-shaped; we are naming an edition | Med |
| D1 | — | **Low** — "Katoptron" names the parent catalogue/corpus, not this edition | High | Low — conflates instrument with framework | **High** — reader imports the catalogue identity |

**Dominance rule (F.18:4.3, `FPF-Spec.md:85981`).** *X* dominates *Y* iff *X* is ≥ *Y* on all four dimensions (AliasRisk inverted) and strictly better on ≥1. A3, B1, B2, C1, C2, D1 are each dominated by A1. **A2 is not dominated** — it edges A1 on SemanticFidelity (coding-precise) while losing CognitiveErgonomics and AliasRisk.

→ **NQD-front = { A1 LAQF, A2 CAQF }.**

### §3.4 Selection (F.18:4.3, `FPF-Spec.md:85983`)

Selected: **A1 — LAQF**, from a two-candidate front. *What it buys:* breadth (Layer-1 is **context-independent** agent quality, not coding-only), the crispest acronym, and collision-avoidance with FPF `A.13` Agent. *Residual risk:* "Quality" is a broad head, and "LLM-Agent" is marginally less domain-precise than "Coding-Agent"; the acronym elides the kind-word *Principle*. These are recorded, not eliminated — exactly the F.18 allowance that one candidate may win without being perfect.

### §3.5 Name Card (F.18:4.2, `FPF-Spec.md:85941`)

```text
NameCard:
  NameCardId:        laqf-f18-iter3
  GovernedValueRef:  Layer-1 Domain Principle Framework edition — 30 context-independent
                     LLM-coding-agent quality patterns + measurement frame (A.19 + C.16)
  GoverningPatternRef: E.4.DPF (framework kind); A.19/C.16 (measurement value); label under F.18
  BoundedContextRef: AION_AUTOPOIESEON / claude_improvements / FPF-seminar:iter3
  LocalSenseRef:     "reusable pattern framework for raising LLM-coding-agent behavioural quality"
  TechLabel:         LAQF — LLM-Agent Quality Principle Framework
  PlainLabel:        the agent-quality framework
  CandidateSet:      A1 LAQF; A2 CAQF; A3 AQPF; B1 LARF; B2 LLM-Agent Behaviour Framework;
                     C1 LLM-Agent Quality Practice Framework; C2 Coding-Agent Improvement
                     Framework; D1 Katoptron Quality Framework
  RejectedCandidates:
    - CAQF (A2): on the front, but coding-only narrowing raises AliasRisk against a
      context-independent Layer-1; less crisp acronym. Selected against, not dominated.
    - AQPF (A3): bare "Agent" collides with FPF A.13 Agent role and agentic hype.
    - LARF (B1): "Reliability" names one of eight characteristics, not the quality space.
    - C1: "Practice Framework" collides with this project's own Layer-2 Local Practice edition.
    - C2: names the Work (improvement), not the framework edition (morphology mismatch).
    - D1 Katoptron-*: names the parent catalogue/corpus, a different governed value.
  SelectionRationale:
    Buys — breadth (context-independent agent quality), crisp acronym, collision-avoidance
    with A.13 Agent. Residual — "Quality" is broad; "LLM-Agent" slightly less precise than
    "Coding-Agent"; acronym elides "Principle". Ratifies frozen decision #2 independently.
  BridgeRefs:        none — spelling matches to FPF "Agent" / "Quality" are NOT sameness
                     claims (F.18:4.1 bridge invariant, FPF-Spec.md:85938).
  UnifiedTermRowRef: none — local; F.17 not invoked (F.18:4.4).
  LineageEntries:
    - frozen decision #2 ([[PROGRESS]] §2): provisional LAQF, "LLM-Agent" to dodge A.13.
    - iter3-S1 (this file): independent F.18 run; confirms LAQF on a 2-candidate NQD-front.
  RefreshCondition:
    Reconsider when (a) scope narrows to coding-only (→ CAQF reopens); (b) scope broadens
    beyond agents; (c) FPF renames/extends A.13 Agent; or (d) repeated reader error reads
    "Quality" as QA/testing rather than the characteristic space.
```

Pattern IDs keep the ratified stem **`LAQF.<Layer><n>`** (frozen #3).

---

## §4 Edition, relation & dependency discipline — E.4.PFR + E.5.3 (`FPF-Spec.md:64387`, `:64835`)

### §4.1 Edition dependency direction (E.5.3, `FPF-Spec.md:64863`)

Upward-only, acyclic — dependencies point toward greater stability; the more stable edition never depends back (`E.5.3` CC-UD.1/2, `FPF-Spec.md:64890`).

```text
Layer-2 Local Practice edition  ⟶  LAQF (Layer-1 Domain edition)  ⟶  FPF Core (FPF-Spec.md)
        (volatile: dot_claude)          (semi-stable: 30 patterns)        (stable: never depends back)
```

### §4.2 Framework edition dependency records (E.4.PFR, `FPF-Spec.md:64435`)

```text
FrameworkEditionDependencyRecord@Context:                # Domain → Core
  frameworkEditionRef:          LAQF v0.1 (Domain Principle edition)
  dependsOnEditionRefs:         FPF Core (FPF-Spec.md) — E.4 family, E.8, A.17–A.19,
                                C.16, E.5.3, F.18, G.2, G.11
  dependencyReason:             borrows pattern-authoring conventions, the characteristic /
                                metric vocabulary, naming, source-pack and refresh discipline
  compatibilityBoundary:        depends on Core pattern *semantics*, not on line numbers;
                                line refs are convenience pins, re-grep on Core edition bump
  deprecationOrSupersessionRefs: —
  refreshConditionRefs:         §6 (G.11) — Core edition bump trigger
  e53ConformanceNote:           acyclic, upward-only; Core does not depend on LAQF (CC-UD.1/2)

FrameworkEditionDependencyRecord@Context:                # Local → Domain (+ Core)
  frameworkEditionRef:          LAQF-Local v0.1 (Layer-2 Local Practice edition)
  dependsOnEditionRefs:         LAQF v0.1 (Domain); transitively FPF Core
  dependencyReason:             the dot_claude realisation instantiates Domain patterns as
                                concrete hooks, skills, settings, commands
  compatibilityBoundary:        Local edition may lag Domain; a Domain pattern change does
                                not silently rewrite Local config — it raises a refresh line
  deprecationOrSupersessionRefs: —
  refreshConditionRefs:         §6 (G.11) — Domain pattern change + dot_claude drift triggers
  e53ConformanceNote:           Local → Domain → Core; no back-edge (CC-UD.1/2)
```

### §4.3 Representative pattern-framework relation records (E.4.PFR, `FPF-Spec.md:64421`)

Architecture-level relations fixed now; each pattern's full §12 relations ship with the pattern (S3–S6).

```text
R1  PatternFrameworkRelationRecord@Context:
  relationId: LAQF.R.layerA-as-law
  sourceRef: LAQF Layer-A patterns (A1–A8)   targetRef: FPF A.6.B Boundary Norm Square (Law quadrant)
  relationFunction: governing-pattern relation (Law framing)
  governedUse: Layer-A solutions frame as *mitigation of a Law*, never elimination
  directGoverningPatternRef: A.6.B + [[../11-fpf-diagnostic]] D2
  blockedStrongerReading: MUST NOT read as removing the model-internal cause
R2  relationId: LAQF.R.measurement
  sourceRef: 12-02-measurement-frame (8 characteristics)   targetRef: A.19 CharacteristicSpace + C.16
  relationFunction: governing-pattern relation
  governedUse: the eight axes are A.19 characteristics; operational bands via C.16 DHCMethod
  directGoverningPatternRef: A.19 / C.16   blockedStrongerReading: bands are not hard SLAs
R3  relationId: LAQF.R.sota
  sourceRef: each pattern §11 SoTA-Echoing   targetRef: G.2 pack over [[../../02-external-research]]
  relationFunction: source/decision reuse (by value)
  directGoverningPatternRef: G.2   sourceReturnCondition: anchor decay → re-harvest (§6)
R4  relationId: LAQF.R.local-edition
  sourceRef: Layer-2 Local Practice edition   targetRef: LAQF Domain edition
  relationFunction: framework edition dependency
  directGoverningPatternRef: E.5.3 + G.11   dependencyOrEditionEffect: upward, acyclic
R5  relationId: LAQF.R.e8-conformance
  sourceRef: all 30 pattern bodies   targetRef: E.8 authoring conventions
  relationFunction: specialization (each body conforms to the 13-section E.8 shape)
  directGoverningPatternRef: E.8   blockedStrongerReading: not a new pattern meta-format
```

### §4.4 Framework package manifest (E.4.PFR, `FPF-Spec.md:64444`)

```text
FrameworkPackageManifest@Context:
  frameworkEditionRef:           LAQF v0.1 (Domain Principle edition)
  selectedPatternSetPublicationRef: §5 roster → 12-10…12-15 (G.5 selected-set, S3–S6)
  relationRecordRefs:            §4.3 R1–R5 + per-pattern §12 (S3–S6)
  dependencyAndEditionRecordRefs: §4.2 (Domain→Core, Local→Domain)
  editionStatus:                 build (S1 keystone fixed; bodies pending)
  deprecationOrSupersessionRefs: —
  sourcePackRefs:                [[12-01-source-pack]] (S2); [[_inputs/rc-digest]]
  qualityEvidenceRefs:           → E.21/E.22, S7
  refreshPlanOrCurrentnessRefs:  §6 (G.11)
  firstEntryCarrierRefs:         [[README]] (S7) + this spine
  blockedRuntimeOrBuildReading:  LAQF is a reading/authoring framework — the manifest
                                 creates no imports, APIs, runtime deps, or build semantics
                                 (FPF-Spec.md:64478)
```

**Carrier-admission note (E.4.DPF:4 step 5, `FPF-Spec.md:64251`).** The local monolith and this spine are relied on as the first-entry carrier; carrier admission for captured/lost/produced structure is owned by `C.33`/`C.34`/`C.35` and is completed at S7, not fabricated here.

---

## §5 Selected pattern set — 30-pattern index (forward to E.8, S3–S6)

The selected set for the manifest (§4.4). FPF kind per [[../11-fpf-diagnostic]] D2: **Law** (design within; mitigate) · **Boundary** (adapt; propose upstream) · **Design** (transform via Work). Detection characteristic is **provisional** — finalised against [[12-02-measurement-frame]] (S2). Titles provisional pending per-pattern authoring.

ID scheme (frozen #3): `LAQF.A1..A8`, `B1..B4`, `C1..C7`, `D1..D4`, `E1..E5`, `F1..F2` (30). Each pattern body carries the footer sentinel `### LAQF.<id>:End` (H-9, content-free).

| LAQF | RC | Provisional title | Kind | Detection characteristic (prov.) | S |
|---|---|---|---|---|---|
| **A1** | rc-01 | Substance-Gated Pushback | Law | sycophancy-rate | S3 |
| **A2** | rc-02 | Delta Over Whole-Artefact | Law | output-economy | S3 |
| **A3** | rc-03 | Answer-Budget Before Prose | Law | output-economy | S3 |
| **A4** | rc-04 | Effective-Fill Accounting | Law | context-integrity | S3 |
| **A5** | rc-05 | Read Before Assert | Law | reconnaissance-depth | S3 |
| **A6** | rc-06 | User-Anchored Facts Over Self-Draft | Law | reconnaissance-depth | S3 |
| **A7** | rc-07 | Reconnaissance Before Action | Law | reconnaissance-depth | S3 |
| **A8** | rc-08 | Literal Scope On Terse Feedback | Law | scope-fidelity | S3 |
| **B1** | rc-09 | Rotate Before The Cliff | Boundary | context-integrity | S4 |
| **B2** | rc-10 | Authoritative Handoff Re-Entry | Boundary | context-integrity | S4 |
| **B3** | rc-11 | Attention-Budget Ledger | Boundary | attention-budget-load | S4 |
| **B4** | rc-12 | Self-Imposed Output Budget | Boundary | output-economy | S4 |
| **C1** | rc-13 | Instruction-Stack Within Budget | Design | attention-budget-load | S4 |
| **C2** | rc-14 | Single-Owner Rule Resolution | Design | attention-budget-load | S4 |
| **C3** | rc-15 | Encoded Engineering Posture | Design | sycophancy-rate | S4 |
| **C4** | rc-16 | Tagged Facts Scaffold | Design | reconnaissance-depth | S4 |
| **C5** | rc-17 | Deterministic Over Advisory | Design | instruction-adherence | S4 |
| **C6** | rc-18 | Whole-Path Permission Coverage | Design | instruction-adherence *(nearest)* | S4 |
| **C7** | rc-19 | Enforced Skill Invocation | Design | instruction-adherence | S4 |
| **D1** | rc-20 | Re-Entry Across Phase Boundary | Design | scope-fidelity | S5 |
| **D2** | rc-21 | Atomic Single-Form Emission | Design | output-economy | S5 |
| **D3** | rc-22 | Roadmap-Anchored Dispatch | Design | scope-fidelity | S5 |
| **D4** | rc-23 | Enforced Role Lanes | Design | scope-fidelity | S5 |
| **E1** | rc-24 | Claim Requires Observed Event | Design | verification-fidelity | S5 |
| **E2** | rc-25 | Enforced Citation Anchors | Design | verification-fidelity | S5 |
| **E3** | rc-26 | Counter-Evidence Audit | Design | verification-fidelity | S5 |
| **E4** | rc-27 | Input-Order Fidelity | Design | verification-fidelity | S5 |
| **E5** | rc-28 | Quiet Toolchain Output | Design | output-economy | S5 |
| **F1** | rc-29 | Bounded Branch Freshness | Design | verification-fidelity *(nearest)* | S6 |
| **F2** | rc-30 | Deterministic Commit Hygiene | Design | instruction-adherence | S6 |

The eight detection characteristics (instruction-adherence, reconnaissance-depth, context-integrity, sycophancy-rate, output-economy, verification-fidelity, attention-budget-load, scope-fidelity) are defined as the `A.19` CharacteristicSpace in [[PROGRESS]] §5 and operationalised with bands in [[12-02-measurement-frame]] (S2). Each pattern wires to ≥1 (frozen authoring convention, [[PROGRESS]] §3).

---

## §6 Currentness & refresh route — G.11 (`FPF-Spec.md:91923`)

One `RefreshPlan@Context` for LAQF: name the affected object, currentness object kind, governing pattern, scoped action, and report ref (`G.11:0.2`, `FPF-Spec.md:91949`). LAQF is a DPF-seed artefact, so the refresh line names the currentness object directly (`G.11:0.3`, `FPF-Spec.md:91952`).

```text
RefreshPlan@Context:
  RefreshPlanId:    LAQF.refresh.v0
  EntityOfConcernRef: LAQF v0.1 (Domain edition) + Layer-2 Local Practice edition
  TargetScope:      whole framework (pattern set, measurement bands, source pack, editions)
  PlannedTriggers (RSCR-style refresh causes):
    T1 model-generation change  → new Claude generation (e.g. 5.x): re-test every Law (A1–A8);
                                  re-measure baselines; the eight bands may shift
    T2 SoTA source decay        → an [[../../02-external-research]] anchor superseded
                                  (IFScale, MRCR v2, reads-per-edit, tokenizer, brevity-cap):
                                  re-harvest via G.2 → [[12-01-source-pack]]
    T3 FPF Core edition bump     → E.4/E.8/A.19/C.16/F.18/G.11 change: re-grep line pins;
                                  re-check E.5.3 conformance
    T4 Layer-2 config drift      → dot_claude/ change (hook/skill/settings): refresh the
                                  Local Practice edition mapping, not the Domain patterns
    T5 repeated reader error     → name/scope misread (e.g. "Quality" → QA): reopen §3 Name Card
  PlannedActions:   each delegates to its governing pattern — G.2 (source pack), E.21/E.23
                    (pattern quality/improvement), E.4.PFR (edition records), F.18 (name)
  RequiredPins:     FPF Core edition; Claude model generation; SoTA anchor set; dot_claude commit
  RefreshReportRef: → recorded in [[PROGRESS]] §9 session log on each refresh
```

`G.11` records currentness, source decay, edition change, and the scoped action; it does **not** decide whether the framework improved — that is `E.21`/`E.23` (`FPF-Spec.md:91952`).

---

## §7 Spine completeness check (E.4.DPF:4 close, `FPF-Spec.md:64275`)

The spine is complete only when a reader can answer all six:

1. **What framework edition is authored?** LAQF v0.1, a two-layer DPF (Domain + Local Practice) — §1, §2, §3.
2. **Which sources and decisions shaped it?** The Κάτοπτρον catalogue (41 symptoms → 30 RCs → ~80 SoTA sources) + the seminar diagnostic, via the E.4.PFAD record — §2, `sourceBasisRefs`.
3. **Which patterns and relations were selected?** 30 patterns (A1–F2) + relation records R1–R5 and the manifest — §4, §5.
4. **Where is it published?** Local monolith `12-llm-agent-quality-dpf/`, first-entry carrier [[README]] + this spine; never FPF Core — §2, §4.4.
5. **How does quality improve?** E.22 framing → E.21 evaluation → E.23 improvement at S7; detection via the eight characteristics — §0, §5, §6.
6. **When does it return for refresh or repair?** Five G.11 triggers (model generation, SoTA decay, Core bump, config drift, reader error) — §6.

> Keystone fixed. Next: **S2** — [[12-01-source-pack]] (G.2 SoTA pack) + [[12-02-measurement-frame]] (A.19 + C.16 bands). S2 may run in parallel with **S3** (style-freeze + Layer A) once this spine is ratified ([[PROGRESS]] §7).

## See also

- [[12-00-spine-ru]] — Russian twin
- [[PROGRESS]] — build ledger (frozen decisions §2, conventions §3, session DAG §7)
- [[_inputs/rc-digest]] — 30-RC + 8-characteristic working digest
- [[../11-fpf-diagnostic]] — Laws-vs-Work ruling (D2), budget constraint (D1)
- [[../choosing_name_with_fpf_48]] — F.18 exemplar (Name Card method)
- [[../../00-MoC]] · [[../../10-root-causes-overview]] · [[../../02-external-research]]
- `FPF-Spec.md:64163` E.4.DPF · `:63995` E.4.PFAD · `:64387` E.4.PFR · `:64835` E.5.3 · `:85840` F.18 · `:91923` G.11
