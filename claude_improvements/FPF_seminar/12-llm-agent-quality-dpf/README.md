---
tags: [claude-improvements, fpf-seminar, laqf, dpf, index, first-entry-carrier]
seminar-iteration: 3
created: 2026-06-28
status: index
framework: LAQF — LLM-Agent Quality Principle Framework
method: FPF E.4.DPF (authoring spine) · E.4.PFAD · E.4.PFR · F.18 · E.5.3 · G.2 · G.11 · E.21 · E.19
---

# LAQF — LLM-Agent Quality Principle Framework

A two-layer **Domain Principle Framework** for troubleshooting and improving the quality of LLM coding agents (Claude Code as the grounding instance). It was authored through the FPF Domain-Principle-Framework spine (`E.4.DPF`, `FPF-Spec.md:64163`) and lands as a **local monolith** in this folder — it writes nothing into `FPF-Spec.md` / FPF Core (`E.5.3`, `FPF-Spec.md:64474`).

This README is the framework's **first-entry carrier** (`E.4.DPF` step 10) and the home of its quality cycle (§6 `E.21`) and admission note (§7 `E.19`). It is **iteration 3** of the Κάτοπτρον FPF seminar ([[../seminar_timeline]]).

- **Layer 1 — Domain Principle edition (LAQF):** 30 reusable, context-independent quality patterns (`E.8`) across six causal layers, plus a measurement frame.
- **Layer 2 — Local Practice edition:** this user's `dot_claude/` realisation, depending on Layer 1 via `E.5.3` (upward-only, acyclic).

Every unit has an engineering **British-English** file and a parity-controlled engineering **Russian** `-ru` twin. Service files (`PROGRESS.md`, `_inputs/rc-digest.md`) stay in English.

---

## §1 Where to start

| If you want to … | Read |
|---|---|
| Understand the architecture, name, edition/relation discipline | [[12-00-spine]] (`E.4.PFAD` decision, `F.18` Name Card, `E.4.PFR` records, 30-pattern index, `G.11` refresh) |
| See the empirical grounding (sources + currentness) | [[12-01-source-pack]] (`G.2` pack — 24 sources, PRISMA flow) |
| See how quality is measured | [[12-02-measurement-frame]] (`A.19` CharacteristicSpace + `C.16` cards + CAL bands) |
| Pick a quality pattern to apply | the six pattern files below, or the roster in §3 |
| See this user's realisation + its gap backlog | [[12-20-local-practice-edition]] |
| Audit the build itself | [[PROGRESS]] (durable build ledger, sessions S0–S7) |

---

## §2 File map

| Unit | EN · RU | What it is | Session |
|---|---|---|---|
| Keystone spine | [[12-00-spine]] · [[12-00-spine-ru]] | Context, `E.4.PFAD` architecture decision, ratified `F.18` name, edition + relation records, 30-pattern index, `G.11` refresh route | S1 |
| Source pack | [[12-01-source-pack]] · [[12-01-source-pack-ru]] | `G.2` SoTA Synthesis Pack — 5 traditions, 24-source ledger, two `Γ_epist` fusions, PRISMA flow | S2 |
| Measurement frame | [[12-02-measurement-frame]] · [[12-02-measurement-frame-ru]] | `A.19` CharacteristicSpace (8 axes, no single score), 8 `C.16` method cards, separately-declared CAL band overlay | S2 |
| Layer A — Laws | [[12-10-patterns-A]] · [[12-10-patterns-A-ru]] | 8 model-internal Law patterns (A1–A8) | S3 |
| Layer B — Boundary | [[12-11-patterns-B]] · [[12-11-patterns-B-ru]] | 4 harness-boundary patterns (B1–B4) | S4 |
| Layer C — Configuration | [[12-12-patterns-C]] · [[12-12-patterns-C-ru]] | 7 configuration design patterns (C1–C7) | S4 |
| Layer D — Workflow | [[12-13-patterns-D]] · [[12-13-patterns-D-ru]] | 4 workflow-topology patterns (D1–D4) | S5 |
| Layer E — Verification | [[12-14-patterns-E]] · [[12-14-patterns-E-ru]] | 5 verification-surface patterns (E1–E5) | S5 |
| Layer F — Process | [[12-15-patterns-F]] · [[12-15-patterns-F-ru]] | 2 process / git-hygiene patterns (F1–F2) | S6 |
| Local Practice edition | [[12-20-local-practice-edition]] · [[12-20-local-practice-edition-ru]] | Layer-2 realisation onto all 30 patterns via `E.4.PFR` | S6 |

---

## §3 The 30 patterns at a glance

IDs are frozen (decision #3); titles ratified via `F.18` in S1. Each pattern wires to one `A.19` detection characteristic (§4) with an early-stage leading indicator. Layer-A patterns frame the Solution as **mitigation of a Law** (never elimination); Layer B **adapts downstream + proposes upstream**; Layers C–F are **direct Work**.

**A — model-internal Laws** ([[12-10-patterns-A]])

| ID | Title | RC | Detection |
|---|---|---|---|
| A1 | Substance-Gated Pushback | rc-01 | sycophancy-rate |
| A2 | Delta Over Whole-Artefact | rc-02 | output-economy |
| A3 | Answer-Budget Before Prose | rc-03 | output-economy |
| A4 | Effective-Fill Accounting | rc-04 | context-integrity |
| A5 | Read Before Assert | rc-05 | reconnaissance-depth |
| A6 | User-Anchored Facts Over Self-Draft | rc-06 | reconnaissance-depth |
| A7 | Reconnaissance Before Action | rc-07 | reconnaissance-depth |
| A8 | Literal Scope On Terse Feedback | rc-08 | scope-fidelity |

**B — harness boundary** ([[12-11-patterns-B]])

| ID | Title | RC | Detection |
|---|---|---|---|
| B1 | Rotate Before The Cliff | rc-09 | context-integrity |
| B2 | Authoritative Handoff Re-Entry | rc-10 | context-integrity |
| B3 | Attention-Budget Ledger | rc-11 | attention-budget-load |
| B4 | Self-Imposed Output Budget | rc-12 | output-economy |

**C — configuration** ([[12-12-patterns-C]])

| ID | Title | RC | Detection |
|---|---|---|---|
| C1 | Instruction-Stack Within Budget | rc-13 | attention-budget-load |
| C2 | Single-Owner Rule Resolution | rc-14 | attention-budget-load |
| C3 | Encoded Engineering Posture | rc-15 | sycophancy-rate |
| C4 | Tagged Facts Scaffold | rc-16 | reconnaissance-depth |
| C5 | Deterministic Over Advisory | rc-17 | instruction-adherence |
| C6 | Whole-Path Permission Coverage | rc-18 | instruction-adherence |
| C7 | Enforced Skill Invocation | rc-19 | instruction-adherence |

**D — workflow** ([[12-13-patterns-D]])

| ID | Title | RC | Detection |
|---|---|---|---|
| D1 | Re-Entry Across Phase Boundary | rc-20 | scope-fidelity |
| D2 | Atomic Single-Form Emission | rc-21 | output-economy |
| D3 | Roadmap-Anchored Dispatch | rc-22 | scope-fidelity |
| D4 | Enforced Role Lanes | rc-23 | scope-fidelity |

**E — verification** ([[12-14-patterns-E]])

| ID | Title | RC | Detection |
|---|---|---|---|
| E1 | Claim Requires Observed Event | rc-24 | verification-fidelity |
| E2 | Enforced Citation Anchors | rc-25 | verification-fidelity |
| E3 | Counter-Evidence Audit | rc-26 | verification-fidelity |
| E4 | Input-Order Fidelity | rc-27 | verification-fidelity |
| E5 | Quiet Toolchain Output | rc-28 | output-economy |

**F — process** ([[12-15-patterns-F]])

| ID | Title | RC | Detection |
|---|---|---|---|
| F1 | Bounded Branch Freshness | rc-29 | verification-fidelity |
| F2 | Deterministic Commit Hygiene | rc-30 | instruction-adherence |

---

## §4 Measurement frame — the eight characteristics

`A.19` CharacteristicSpace axes ([[12-02-measurement-frame]]). No cross-slot normalisation, no single composite score; each pattern names ≥1 as its detection signal.

| # | Characteristic | Polarity | Lead indicator (early-stage) |
|---|---|---|---|
| 1 | instruction-adherence | higher | stated-rule-violated event within session |
| 2 | reconnaissance-depth | higher (diminishing) | reads-per-edit; Disclosure-block present |
| 3 | context-integrity | target (below cliff) | effective fill % vs practitioner cliff |
| 4 | sycophancy-rate | lower | "modified version of what was asked" / 50 turns |
| 5 | output-economy | lower (floored) | tokens/turn; lines/stage |
| 6 | verification-fidelity | higher | claim-without-evidence rate |
| 7 | attention-budget-load | lower (ceiling) | instruction-stack lines; conflicting pairs |
| 8 | scope-fidelity | higher | edit-target overlap with named scope |

---

## §5 Layer-2 Local Practice status

The Local Practice edition ([[12-20-local-practice-edition]]) maps this user's `dot_claude/` onto all 30 patterns. Realisation tally (grounded in [[../../03-current-config-map]]):

- **✅ realised (2):** B2 (handoff re-entry), D4 (role lanes).
- **◐ partial (19):** broad advisory/hook coverage that does not yet fully meet the pattern.
- **⬜ gap (9):** B3, C1, C2, C3, C4, C7, E2, E4, F1 — the improvement backlog.

The 9 gaps concretise `compatibilityBoundary: Local may lag Domain` — they are **lag, not contradiction**, hence `E.5.3`-conformant (Local → Domain → Core, acyclic). They are not Layer-1 admission blockers (§7).

---

## §6 Quality cycle — E.21 evaluation

**`E.22` frame (purpose):** `floorEvaluation` for landing — an admission-floor read of the Layer-1 edition, not an `exceptionalImprovementEvaluation`. Coordinate values are honest floors, not improvement targets.

```text
PatternQualityEvaluation (E.21, FPF-Spec.md:77424):
  PatternOfConcernRef:   LAQF Layer-1 Domain edition v0.1 (this local monolith)
  ClaimScope:            landing input — admission as a local-monolith first-entry carrier
  WorkingReaderScope:    FPF-literate practitioner improving an LLM coding agent, cold first use
  IntendedUse:           admit for declared use (local-monolith landing) + drive Layer-2 backlog
  QualificationWindow:   FPF-Spec.md repo copy (S0 line map); G.2 anchors as of 2026-06-28
  EvaluationEvidenceBasis: 30 pattern bodies (12-10…12-15); editions (12-00, 12-20);
                         measurement frame (12-02); source pack (12-01); PROGRESS spine.
                         Missing: filled worked-case matrix at edition level (caps case coords at 3).
  PrecisionRestorationProfile:
    overallEffect: boundedLocal
    wordHeadUsePrecision: clean (F.18 Name Card ratifies LAQF; residual alias risk recorded)
    phraseApparatus: clean
    repetitionAndNegativeDistribution: bounded-local (A:0/B:0/C:0 shared contracts, by design)
    onticAndSlotRelationClarity: clean (Law/Boundary/Design kinds held across all 30)
    descriptionPublicationSourceBoundary: clean (measurement/source quarantined to 12-01/12-02)
    checkedLoci: H-1 titles, :End sentinels, §11 pack-id bindings across all units
    affectedCoordinates: none lowered below 3 by precision findings
```

| Coordinate | Value | ShortRationale |
|---|---:|---|
| WorkingSituationAndUseBoundaryRecognizability | 4 | Each pattern opens with a `:0` Use-this-when; spine §1 non-use boundary explicit. <5: no edition-level replayable cold-start slice. |
| EntityOfConcernAndClaimScopeStability | 4 | Law-vs-Work stance held across all 30 + both editions via A:0/B:0/C:0 contracts. <5: some patterns lean on the shared contract for scope. |
| PatternApplicationGuidance | 4 | Every Solution gives an executable first move; 12-20 shows realisation. <5: not every pattern carries a filled worked slice. |
| ClosureAndBoundedNonUseRecoverability | 4 | Consequences + Conformance per pattern; Law non-elimination boundary explicit; G.11 stop. <5: few worked overturn cases. |
| SemanticKindAndNameRecoverability | 4 | F.18 ratifies LAQF; IDs frozen; "LLM-Agent" disambiguates A.13 `Agent`. <5: residual alias risk recorded honestly. |
| NeighborAuthorityAndBoundedUseFit | 4 | §11/§12 cite real anchors; C5 routes deterministic-vs-advisory; E.5.3 direction. <5: some authority carried in shared-contract prose. |
| EntityOfConcernPrimacyAndSemioBiasResistance | 4 | Patterns lead with behaviour-subject + action; source/measurement material quarantined. <5: not stress-tested across readers. |
| PracticalUseDeltaAndHarmPrevention | 4 | Each maps to a named RC/symptom + prevented misuse; ME-1…ME-4 anchor harm. <5: harm shown by reference, few near-miss replays. |
| UseAffordabilityAndApparatusProportionality | 3 | Thin first use exists, but the full E.4.PFAD/PFR + 19-coordinate apparatus is heavy for an ordinary reader. |
| RepairLocalityAndChangeImpactPredictability | 4 | One file per layer, footer sentinels, Layer-2 gaps localised in 12-20. <5: no worked downstream-impact slice. |
| ProxyForValueSubstitutionResistance | 3 | Frame bans single score; output-economy floored against over-clamp; "what got worse" applied in B4/E5 — but not per pattern. |
| ClaimJustificationTraceabilityCurrentnessAndReplayability | 4 | Every claim → pack id (L../ME../MF..); PROGRESS replays the build; G.11 currentness. <5: some operator-family bindings are stubs. |
| CaseCountercaseAndTransferCoverage | 3 | Archetypal Grounding (Tell-Show-Show) per pattern + ME-1…ME-4, but no broad anti-case/transfer matrix. |
| MaturePatternParityAndSelectedContentSufficiency | 3 | Mature comparators named per pattern (CI/trunk, RBAC, 3NF, stable-sort, falsificationism), but selected ingredients discharged narratively, not all by-value. |
| SoTABindingAndCurrentness | 4 | G.2 pack (24 sources, PRISMA, SoTA_Set=22); per-pattern §11 binds pack ids with reopen discipline. <5: freshness windows young. |
| FormalClaimAdmissibilityAndLensFit | 4 | A.19 declared with no cross-slot normalisation/single score; C.16 thresholds excluded per rule; CAL bands a separate overlay. <5: bands partly interpolated. |
| FalsifiabilityAndLoweringCondition | 4 | Leading indicators + green/amber/red bands give lowering signals; G.11 T1–T5 reopen triggers. <5: thresholds not yet field-calibrated. |
| CorpusEntryProjectionAndEcologyFit | 3 | This README is the first-entry carrier + seminar_timeline/00-MoC wiring, but the entry surface is freshly authored and unproven. |
| EvolutionFrontAndRefreshDiscipline | 4 | G.11 RefreshPlan (5 triggers) + the Layer-2 gap backlog as an explicit evolution front. <5: no completed refresh cycle yet. |

```text
  PatternQualityStatus: sufficientlyExpressedForDeclaredUse
                        (landing as a local monolith v0.1, status=build)
  StopCondition:        Stop polishing at v0.1 landing. Reopen when (a) any G.11 trigger
                        T1–T5 fires, or (b) a coordinate capped at 3–4 gains a filled
                        worked slice / by-value maturity discharge / field-calibrated band.
                        Layer-2 gaps (§5) are tracked in 12-20 — not Layer-1 stop conditions.
```

No `5` is claimed: no coordinate has reinforcing replayable evidence without a named limit. The honest floor is **landing-sufficient, improvement-open**.

---

## §7 Admission note — E.19

**`E.19` run record** (`FPF-Spec.md:76336`) — admission of the Layer-1 edition for local-monolith landing. This consumes the §6 `E.21` result; it does not re-assign coordinate values.

**Baseline triage (PCP-BASE).**

1. *Internal coherence* — Problem ↔ Conformance ↔ Solution aligned per pattern; no orphan/unclaimed requirements found. **pass**
2. *Lexical discipline* — FPF terms (`A.19`, `C.16`, `E.5.3`, `E.4.PFR`) reused, not redefined; "LLM-Agent" minted via F.18 to avoid the `Agent`/A.13 collision. **pass**
3. *SoTA-Echoing* — present per pattern §11, bound to the G.2 pack (no untracked narrative); divergences stated. **pass**
4. *Cross-pattern compatibility* — relations consistent; edition dependency acyclic (`E.5.3`); impact radius on Core = **none**. **pass**
5. *Didactic grounding* — Archetypal Grounding (Tell-Show-Show) present in every pattern. **pass**
6. *Reader-fit* — bodies addressed to the practitioner; package/QA rationale kept in spine, this README, and 12-20. **pass**
7. *Template integrity* — H-1 titles + `:End` sentinels verified across all six pattern files. **pass**
8. *Modularity & contradiction hygiene* — one file per layer; shared `:0` contracts state cross-cutting rules once. **pass**
9. *Substantive adequacy* — still solves the 30 RCs; claim-bearing material sits with its governing pattern. **pass**

**Risk-driven profiles applied.** `PCP-PRAG` (Normative practice guidance — recognition text + first move present) · `PCP-SOTA` (G.2 binding + reopen discipline) · `PCP-BRIDGE` (the two `Γ_epist` fusions G.2-F1/F2 carry explicit `residualLoss`, no silent fusion) · `PCP-TERM` (F.18 Name Card with recorded alias risk) · `PCP-REFRESH` (G.11 plan present).

**Delta-Class:** `Δ-0` relative to FPF Core — a new local framework that writes nothing into `FPF-Spec.md`. Core impact radius: none.

**Admission decision:** **admit for landing as a local monolith (v0.1, status=build-with-gaps).** The 9 Layer-2 gaps (§5) are `E.5.3`-conformant lag, **not** Layer-1 admission blockers. Coordinates capped at 3 (affordability, case coverage, maturity-by-value, corpus-entry, proxy-resistance) are recorded as the refresh front, not blockers for the declared landing use.

**Project-side reuse boundary** (`E.19:4.1`, `FPF-Spec.md:76418`). This is an **FPF pattern-quality result**, not certification of the `dot_claude/` realisation or of any project outcome. Reusing it as project evidence, gate input, or release justification requires opening the project-side governing relation for that claim by value (e.g. `A.10` evidence, `A.21` gate). "Pattern review passed" ≠ "the agent is fixed".

---

## §8 Provenance & refresh

- **Build spine:** authored across sessions S0–S7 against the durable [[PROGRESS]] ledger (the single source of truth for resumption). Method `E.4.DPF` 11-step spine; patterns `E.8`; relations/editions `E.4.PFR`; naming `F.18`; dependency `E.5.3`.
- **Refresh route (`G.11`):** triggers T1–T5 in [[12-00-spine]] §6 — new model generation, new SoTA source pack, instruction-budget drift, harness-cliff shift, Layer-2 gap closure. Reopen the affected unit, not the whole framework.
- **Seminar context:** iteration 3 of Κάτοπτρον — [[../seminar_timeline]]. Prior iterations: 0 naming, 1 `A.7`/`A.6.B`/`C.16` diagnostic ([[../11-fpf-diagnostic]]), 2 `F.18` naming re-run ([[../choosing_name_with_fpf_48]]).

## See also

- [[../../00-MoC]] — Κάτοπτρον catalogue hub (30 root causes, 41 symptoms)
- [[../../10-root-causes-overview]] — the 30 RCs this framework patterns
- [[../../02-external-research]] — SoTA corpus behind the G.2 pack
- [[../seminar_timeline]] — FPF seminar timeline (this is iteration 3)
- [[PROGRESS]] — durable build ledger
