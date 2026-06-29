---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, progress-ledger]
created: 2026-06-28
status: build-ledger
iteration: 3
---

# LAQF DPF — build ledger

Durable, on-disk progress spine for authoring the **LLM-Agent Quality Principle Framework (LAQF)** — a two-layer Domain Principle Framework built with FPF method `E.4.DPF`. This file survives `/clear`, compaction, and session gaps. **It is the single source of truth for "where we stopped and where to start."** TaskList is session-scoped and does not survive; this ledger does.

---

## §0 How to resume (read this first, every session)

1. Read this whole file (it is small by design).
2. Go to **§8 File inventory** and find the first row that is **not** `✅ done`. That is your start point.
3. Read **§2 Frozen decisions** and **§3 Authoring conventions** — do not re-litigate them.
4. Read the **refs listed for the current session** in **§7 Session plan** (only those — not the whole FPF spec).
5. Read `_inputs/rc-digest.md` (the 30-RC + measurement digest) — it replaces re-reading all 30 source files.
6. Do the session's work. Author EN first, then the `-ru` twin per file.
7. When a file is finished: update its **§8** row to `✅`, and append a dated entry to **§9 Session log**.
8. **Stop at the session boundary.** Do not roll into the next session unless the user says so.

Resume in one line: *open §8 → first non-✅ row → that session's refs in §7 → author → tick §8 → log §9 → stop.*

---

## §1 What we are building

- **Subject domain:** troubleshooting and quality improvement of LLM coding agents (Claude Code specifically).
- **Artefact:** a Domain Principle Framework (DPF) in **two layers** —
  - **Layer 1 — Domain Principle edition (LAQF):** 30 reusable, context-independent quality patterns + a measurement frame.
  - **Layer 2 — Local Practice edition:** this user's `dot_claude/` realisation (hooks, skills, settings), depending on Layer 1 via E.5.3.
- **Two full language versions:** engineering **British English** + engineering **Russian** (`-ru` twin per file).
- **Method:** `E.4.DPF` 11-step spine. Patterns follow `E.8`. Relations/editions follow `E.4.PFR`. Dependency direction governed by `E.5.3`.
- **Lands as a local monolith** in this seminar folder — **NOT** into `FPF-Spec.md` / FPF Core.
- This is **seminar iteration 3** (wire into `seminar_timeline.md` + `00-MoC.md` at the end).

---

## §2 Frozen decisions (do not re-open without explicit user request)

| # | Decision | Status |
|---|---|---|
| 1 | Scope: two-layer; **all 30** root causes as **full E.8 patterns**; **both** measurement layers (abstract A.19 CharacteristicSpace + operational overlay with bands) | approved 2026-06-28 |
| 2 | Framework name: **LAQF = LLM-Agent Quality Principle Framework** ("LLM-Agent" chosen to avoid collision with FPF's own `Agent`/A.13 term). Finalise/ratify via F.18 Name Card in S1 | provisional → ratify S1 |
| 3 | Pattern ID scheme: `LAQF.A1..A8`, `B1..B4`, `C1..C7`, `D1..D4`, `E1..E5`, `F1..F2` (30 total). Footer sentinel `### LAQF.A1:End` per pattern | frozen |
| 4 | Layout: subfolder `12-llm-agent-quality-dpf/`; one EN file + one `-ru` twin per unit | frozen |
| 5 | Landing: local monolith only, **not** into `FPF-Spec.md` (E.5.3 — domain edition never writes into Core) | frozen |
| 6 | Language: Russian `-ru` twins are an explicit exception to the British-English-only artefact rule. Service files (`PROGRESS.md`, `_inputs/rc-digest.md`) stay in English | frozen |
| 7 | Edition dependency direction (E.5.3): Local Practice → Domain (LAQF) → FPF Core. Core never reverse-depends. Acyclic | frozen |

---

## §3 Authoring conventions

### E.8 pattern body — canonical 13 sections (every pattern)

```
Title:  ## <FullId> - <Title>            (H-1: hashes, space, FullId, " - ", Title)
Header block: Type, Status; optional Normativity
 1 Problem frame
 2 Problem
 3 Forces
 4 Solution
 5 Archetypal Grounding        (Tell-Show-Show; ≥1 content-bearing slice)
 6 Bias-Annotation
 7 Conformance Checklist
 8 Common Anti-Patterns and How to Avoid Them
 9 Consequences
10 Rationale
11 SoTA-Echoing               (S-13: claim → practice → source → alignment → adopt/adapt/reject)
12 Relations
13 Footer:  ### <PatternId>:End            (H-9 sentinel, content-free)
```

- **Recognition text first, assurance text second:** Use-this-when + upper Problem-frame/Problem/Solution/Consequences before checklists/bias/conformance.
- **Layer A patterns** frame the Solution as *mitigation of a Law*, never elimination (per `11-fpf-diagnostic` D2). Layers C–F frame as direct Work.
- Every pattern's §11 cites a real `02-external-research` anchor (see digest §8) — no invented sources.
- Each pattern names ≥1 of the eight measurement characteristics (§5) as its detection signal, with an early-stage (leading) indicator.

### E.4.PFR records (Layer-2 wiring, authored in S1 + S6)

- `PatternFrameworkRelationRecord@Context`: relationId, sourceRef, targetRef, relationFunction, governedUse, directGoverningPatternRef, dependencyOrEditionEffect?, preservationOrAdmissionRef?, blockedStrongerReading, sourceReturnCondition?, refreshOrSupersessionCondition?
- `FrameworkEditionDependencyRecord@Context`: frameworkEditionRef, dependsOnEditionRefs, dependencyReason, compatibilityBoundary, deprecationOrSupersessionRefs?, refreshConditionRefs?, e53ConformanceNote
- `FrameworkPackageManifest@Context`: frameworkEditionRef, selectedPatternSetPublicationRef, relationRecordRefs, dependencyAndEditionRecordRefs, editionStatus, deprecationOrSupersessionRefs?, sourcePackRefs, qualityEvidenceRefs, refreshPlanOrCurrentnessRefs, firstEntryCarrierRefs, blockedRuntimeOrBuildReading

### E.4.PFAD decision slots (S1 keystone record)

frameworkDecisionId, governedFrameworkRef, boundedContextRef, frameworkEditionRef, fpfCoreEditionRef, decisionQuestion, sourceBasisRefs, sotaSynthesisPackRefs, namingDecisionRefs, selectedPatternSetRefs, selectedPatternRelationRefs, publicationUnitRefs, dependencyAndEditionRefs, qualityEvaluationRefs, admissionReviewRefs, rejectedAlternatives, rationaleRefs, consequences, localMonolithLandingRefs, sourceReturnConditions, refreshOrSupersessionConditions.

### F.18 naming (S1) — NQD-front axes

SemanticFidelity · CognitiveErgonomics · MorphologicalActionFit · AliasRisk. Produce a Name Card per the `choosing_name_with_fpf_48` exemplar; add RefreshCondition.

### House style (match existing seminar files)

Bilingual EN + `-ru` pairs · FPF-section citations as `FPF-Spec.md:<line>` · fact-dense British English · Obsidian wikilinks · frontmatter with tags/created/status.

---

## §4 Reference index

### FPF spec — repo copy (edit-tracked): `roles/devbox/files/dot_claude/docs/FPF-Spec.md`
Deployed copy (read-only convenience): `~/.claude/docs/FPF-Spec.md` (~93,316 lines — **never** load whole; grep `## <ID> - Title` then Read targeted range). Line numbers below were captured in S0; if a number does not land, re-grep the header.

| Section | Line | Section | Line |
|---|---|---|---|
| A.17 Characteristics | 24129 | E.5 Dependency | 64580 |
| A.18 CSLC | 24265 | E.5.3 Unidirectional Dep. | 64835 |
| A.19 CharacteristicSpace | 24417 | E.8 Authoring Conventions | 65183 |
| C.16 Measurement/Metrics | 42826 | E.19 Admission review | 76336 |
| E.4 (DPF family root) | 63805 | E.21 Eval | 77424 |
| E.4.PFAD Architecture Decision | 63995 | E.22 Framing | 77795 |
| E.4.DPF Authoring spine | 64163 | E.23 Improvement | 78010 |
| E.4.PFR Relation/Edition | 64387 | F.18 Local-First Naming | 85840 |
| G.0 SoTA root | 86968 | G.2 SoTA Synthesis Pack | 87746 |
| G.11 Currentness/refresh | 91923 | | |

### Source catalogue: `claude_improvements/`
`00-MoC.md` · `01-symptoms-inventory.md` (41 symptoms) · `02-external-research.md` (~80 SoTA sources — measurement backbone) · `03-current-config-map.md` · `04-reflection-evidence.md` · `10-root-causes-overview.md` (30 RCs) · `_writer-instructions.md` · `rc-01..rc-30-*.md`.

### House-style exemplars: `claude_improvements/FPF_seminar/`
`11-fpf-diagnostic.md` (+`-ru`) · `choosing_name_with_fpf_48.md` (+`-ru`) · `choosing_name.md` (+`-ru`) · `seminar_timeline.md`.

### Build inputs: this folder
`_inputs/rc-digest.md` (30-RC + 8 measurement characteristics + SoTA anchors).

---

## §5 Measurement characteristics (the eight)

CharacteristicSpace axes for `12-02-measurement-frame`. Full signals + RC indices live in `_inputs/rc-digest.md §7`.

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

Each pattern (S3–S6) must wire to ≥1 of these as its detection signal.

---

## §6 Pattern roster (RC → LAQF ID → provisional title)

Titles provisional; ratify via F.18 in S1.

**A — model-internal Laws:** A1 rc-01 Substance-Gated Pushback · A2 rc-02 Delta Over Whole-Artefact · A3 rc-03 Answer-Budget Before Prose · A4 rc-04 Effective-Fill Accounting · A5 rc-05 Read Before Assert · A6 rc-06 User-Anchored Facts Over Self-Draft · A7 rc-07 Reconnaissance Before Action · A8 rc-08 Literal Scope On Terse Feedback

**B — harness boundary:** B1 rc-09 Rotate Before The Cliff · B2 rc-10 Authoritative Handoff Re-Entry · B3 rc-11 Attention-Budget Ledger · B4 rc-12 Self-Imposed Output Budget

**C — configuration:** C1 rc-13 Instruction-Stack Within Budget · C2 rc-14 Single-Owner Rule Resolution · C3 rc-15 Encoded Engineering Posture · C4 rc-16 Tagged Facts Scaffold · C5 rc-17 Deterministic Over Advisory · C6 rc-18 Whole-Path Permission Coverage · C7 rc-19 Enforced Skill Invocation

**D — workflow:** D1 rc-20 Re-Entry Across Phase Boundary · D2 rc-21 Atomic Single-Form Emission · D3 rc-22 Roadmap-Anchored Dispatch · D4 rc-23 Enforced Role Lanes

**E — verification:** E1 rc-24 Claim Requires Observed Event · E2 rc-25 Enforced Citation Anchors · E3 rc-26 Counter-Evidence Audit · E4 rc-27 Input-Order Fidelity · E5 rc-28 Quiet Toolchain Output

**F — process:** F1 rc-29 Bounded Branch Freshness · F2 rc-30 Deterministic Commit Hygiene

---

## §7 Session plan (DAG)

Each session is sized to fit one context window. Within a session: author EN, then `-ru` twin. Stop at the boundary.

| S | Goal | Produces | Refs to read |
|---|---|---|---|
| **S1** | **Keystone** — Context declaration, E.4.PFAD decision record, F.18 Name Card (ratify LAQF), edition records, 30-pattern index, G.11 refresh plan | `12-00-spine.md` (+`-ru`) | E.4.DPF, E.4.PFAD, E.4.PFR, F.18, G.11; exemplar `choosing_name_with_fpf_48` |
| **S2** | **Evidence + scales** — SoTA pack (claim/method-family cards); measurement frame (~12 A.19 slots, C.16 DHCMethod each, green/amber/red bands + leading indicators) | `12-01-source-pack.md`, `12-02-measurement-frame.md` (+`-ru`) | G.2, A.17–A.19, C.16; `02-external-research`; digest §7–§8 |
| **S3** | **Style-freeze + Layer A** — author A1 (Law exemplar) + one design exemplar by hand to freeze house style, then A2–A8 full E.8 | `12-10-patterns-A.md` (+`-ru`) | E.8; digest §1; exemplar `11-fpf-diagnostic` |
| **S4** | **Layers B + C** — 11 patterns (B1–B4, C1–C7) | `12-11-patterns-B.md`, `12-12-patterns-C.md` (+`-ru`) | E.8; digest §2–§3; frozen A-exemplars |
| **S5** | **Layers D + E** — 9 patterns (D1–D4, E1–E5) | `12-13-patterns-D.md`, `12-14-patterns-E.md` (+`-ru`) | E.8; digest §4–§5; frozen exemplars |
| **S6** | **Layer F + Local edition** — F1–F2; Local Practice edition with E.4.PFR relation/dependency records | `12-15-patterns-F.md`, `12-20-local-practice-edition.md` (+`-ru`) | E.8, E.4.PFR, E.5.3; digest §6; `03-current-config-map` |
| **S7** | **Integrate + QA** — README index; wire `seminar_timeline.md` + `00-MoC.md` as iteration 3; E.21/E.19 quality + admission notes | `README.md`; edits to timeline + MoC | E.19, E.21; whole folder |

**Dependencies:** S1 → {S2, S3}; S3 freezes style for S4 → S5 → S6; S6 needs the pattern set (S3–S5); S7 needs everything. S2 may run in parallel with S3 after S1.

**Subagent note:** in S4–S6, per-layer drafting may be delegated to a subagent against the **frozen** S3 exemplars to protect the main context window; review each layer before ticking §8.

---

## §8 File inventory (state ledger)

Legend: ⬜ not started · 🟡 in progress · ✅ done.

| State | File | Session |
|---|---|---|
| ✅ | `_inputs/rc-digest.md` | S0 |
| ✅ | `PROGRESS.md` | S0 |
| ✅ | `12-00-spine.md` | S1 |
| ✅ | `12-00-spine-ru.md` | S1 |
| ✅ | `12-01-source-pack.md` | S2 |
| ✅ | `12-01-source-pack-ru.md` | S2 |
| ✅ | `12-02-measurement-frame.md` | S2 |
| ✅ | `12-02-measurement-frame-ru.md` | S2 |
| ✅ | `12-10-patterns-A.md` | S3 |
| ✅ | `12-10-patterns-A-ru.md` | S3 |
| ✅ | `12-11-patterns-B.md` | S4 |
| ✅ | `12-11-patterns-B-ru.md` | S4 |
| ✅ | `12-12-patterns-C.md` | S4 |
| ✅ | `12-12-patterns-C-ru.md` | S4 |
| ✅ | `12-13-patterns-D.md` | S5 |
| ✅ | `12-13-patterns-D-ru.md` | S5 |
| ✅ | `12-14-patterns-E.md` | S5 |
| ✅ | `12-14-patterns-E-ru.md` | S5 |
| ✅ | `12-15-patterns-F.md` | S6 |
| ✅ | `12-15-patterns-F-ru.md` | S6 |
| ✅ | `12-20-local-practice-edition.md` | S6 |
| ✅ | `12-20-local-practice-edition-ru.md` | S6 |
| ✅ | `README.md` | S7 |
| ✅ | `seminar_timeline.md` (wire iteration 3) | S7 |
| ✅ | `00-MoC.md` (wire iteration 3) | S7 |

---

## §9 Session log

- **2026-06-28 — S0 (recon + plan).** Confirmed scope (two-layer, all 30 full E.8, both scales). Mapped 30 RCs → LAQF IDs with provisional titles. Derived the eight shared measurement characteristics from the RCs and cross-checked against `02-external-research`. Captured FPF spec line numbers. Created folder `12-llm-agent-quality-dpf/` + `_inputs/`. Wrote `_inputs/rc-digest.md` and this ledger. **Next start point: S1 — `12-00-spine.md`.**
- **2026-06-28 — S1 (keystone spine).** Authored `12-00-spine.md` + `-ru` twin (section-for-section parity). Contents: §0 DPF spine coverage (11-step ownership map); §1 Context declaration (two-layer shape); §2 full `E.4.PFAD` decision record (all 21 slots, `LAQF.PFAD.iter3-s1`); §3 independent **F.18** run — 8 candidates / 4 head families, ordinal NQD-front {A1 LAQF, A2 CAQF}, **selected A1 LAQF**, Name Card `laqf-f18-iter3` (ratifies frozen #2 with honest residual risk); §4 `E.5.3` direction + 2 `FrameworkEditionDependencyRecord` + 5 representative `PatternFrameworkRelationRecord` (R1–R5) + `FrameworkPackageManifest` + carrier-admission note; §5 30-pattern index (Law/Boundary/Design kind + provisional detection characteristic; rc-18, rc-29 marked "nearest"); §6 `G.11` `RefreshPlan` (5 triggers T1–T5); §7 six-question completeness check. Frozen decisions untouched. **Next start point: S2 — `12-01-source-pack.md` + `12-02-measurement-frame.md`** (may run parallel with S3).
- **2026-06-28 — S2 (source pack, EN).** Authored `12-01-source-pack.md` — a reference-grade **G.2** SoTA Synthesis Pack grounding the whole framework's empirical claims. Contents: §0 Scope & plurality (CG-FrameContext, entityOfConcern ⟨agent-in-session, world plane⟩, 5 Traditions T1 Vendor / T2 Long-context benchmarks / T3 IF benchmarks / T4 Sycophancy-RLHF / T5 Practitioner, `FamilyCoverageFloorK=3` pass); §1 CorpusLedger (24 sources L01–L24, anchor+tradition+triage+claim); §2 ClaimSheets per tradition (bounded context/claims/validity/freshness/failure modes/reuse); §3 OperatorAndObjectInventory (8 characteristics → A.19 slots + 6 operator-family stubs → C.16); §4 BridgeMatrix B1–B6 + two **Γ_epist** fusion records (G.2-F1 operational context cliff = T2+T5; G.2-F2 instruction-adherence ceiling = T3+T5, each with explicit residualLoss — no silent fusion); §5 MicroExamples ME-1…ME-4; §6 MethodFamilyCards MF-1…MF-6; §7 PRISMA Flow Record (24 ledgered → 19 include / 4 park / 1 retire, SoTA_Set=22); §8 SoTAPaletteDescription (consumable surface, ids bound for 12-02 + per-pattern §11 handoff); §9 conformance & refresh.
- **2026-06-28 — S2 (remainder, via subagents).** Completed S2 by dispatching three subagents in parity-controlled order (two parallel + one dependent). (1) `12-01-source-pack-ru.md` — Russian twin, strict section-for-section parity (10 sections, 24-row CorpusLedger, all ids/anchors/percentages verbatim, prose translated). (2) `12-02-measurement-frame.md` (EN) — the **A.19 CharacteristicSpace** `LAQF.charspace.iter3` (8 slots, no cross-slot normalisation, no single score) + 8 **C.16** `U.DHCMethod` cards (thresholds excluded per C.16 rule) + a separately-declared **CAL band overlay** `LAQF.cal.iter3` (green/amber/red + leading indicators, every band citing a pack id; interpolated bands incl. the ~55% cliff marked `[interp]`; output-economy floored to L04) + leading-vs-lagging table + pattern↔characteristic index (all 30 patterns) + conformance/refresh. (3) `12-02-measurement-frame-ru.md` — Russian twin, strict parity (7 sections, all 8 cards mirrored, fenced declaration blocks verbatim). Ledger bookkeeping done by orchestrator (no subagent touched PROGRESS.md). **S2 complete — all four files ✅. Next start point: S3 — `12-10-patterns-A.md` + `-ru` (the 8 Layer-A Law patterns), consuming the 12-01 palette + 12-02 detection axes.**
- **2026-06-28 — S3 (style-freeze + Layer A).** Authored `12-10-patterns-A.md` (EN) by hand as the **house-style freeze** for all 30 patterns: intro + a shared `## A:0` Layer-A mitigation contract (states the Law-mitigation / `blockedStrongerReading` rule once, governed reading of R1) + the **8 Layer-A Law patterns A1–A8**, each to the full `E.8` thirteen-section template with header block (Type/Status/Normativity/FPF kind `A.6.B`-L/Detection characteristic/Source mechanism), a `:0` Use-this-when, sections 1–12, and footer sentinel `### LAQF.<id>:End`. Coverage: A1 Substance-Gated Pushback (rc-01, s4; ME-2 [L06], L19), A2 Delta Over Whole-Artefact (rc-02, s5; L04, L17, MF-6 + the `[§N CHANGED/ADDED/REMOVED]` template), A3 Answer-Budget Before Prose (rc-03, s5; L04, L03), A4 Effective-Fill Accounting (rc-04, s3; L03, ME-3 [L10], G.2-F1 — owns measurement, delegates rotation to B1), A5 Read Before Assert (rc-05, s2; ME-1 [L05], L02, target ≥3.0 reads-per-edit), A6 User-Anchored Facts Over Self-Draft (rc-06, s2; L17, MF-4, `[USER]`/`[DRAFT]` scaffold), A7 Reconnaissance Before Action (rc-07, s2; ME-1 [L05], L16, ladder + Disclosure block), A8 Literal Scope On Terse Feedback (rc-08, s8; L02, L18). Each §11 cites pack ids only (no quotes, G.2:4.2); each wires one A.19 detection slot with a leading indicator. RU twin `12-10-patterns-A-ru.md` produced via one parity-controlled subagent — confirmed identical structure (112 `###` headings, 8 `:End` sentinels, 10 `##` headings, 2 fenced blocks byte-for-byte; all L-/ME-/MF-/`FPF-Spec.md:` ids verbatim; twin-pointer swapped), prose translated to engineering Russian. Orchestrator-only ledger bookkeeping. **S3 complete — both files ✅. Next start point: S4 — `12-11-patterns-B.md` + `12-12-patterns-C.md` (+`-ru`), the 11 Boundary/Design patterns B1–B4, C1–C7, drafted against the frozen S3 exemplars.**
- **2026-06-28 — S4 (Layers B + C).** Authored `12-11-patterns-B.md` (EN) by hand: intro + a shared `## B:0` Layer-B **boundary contract** (the Boundary analogue of A:0 — cause is the harness environment; adapt downstream + propose upstream, never assume eliminable; governed reading per `11-fpf-diagnostic` D2) + the **4 Layer-B Boundary patterns B1–B4**, each to the full `E.8` template with header block (FPF kind = Boundary). Coverage: B1 Rotate Before The Cliff (rc-09, s3; G.2-F1, MRCR cliff, MF-3), B2 Authoritative Handoff Re-Entry (rc-10, s3; MF-4, post-compaction task-identity), B3 Attention-Budget Ledger (rc-11, s7; L21, MF-2 — measures the stack that C1 trims / C2 de-conflicts), B4 Self-Imposed Output Budget (rc-12, s5; L20-ME-3 brevity-cap reverted, MF-6, floored so as not to over-clamp). Then authored `12-12-patterns-C.md` (EN) by hand: intro + a shared `## C:0` Layer-C **design contract** (the Design analogue — cause is user-owned config, neither Law nor harness boundary; direct Work, no hedge; Layer-1 states *what*, Layer-2/S6 realises *how*; prefer MF-1 deterministic over MF-2 advisory where a rule must hold, pointing to C5) + the **7 Layer-C Design patterns C1–C7**. Coverage: C1 Instruction-Stack Within Budget (rc-13, s7; trim to ~150, move conditional rules to on-demand skills via L17), C2 Single-Owner Rule Resolution (rc-14, s7; one rule one owning asset, 3NF analogy), C3 Encoded Engineering Posture (rc-15, s4; skill encoding Fisher's maxim / anti-false-dichotomy / shadow-mode-CBC / kill-two-birds; MF-2), C4 Tagged Facts Scaffold (rc-16, s2; `[USER]`/`[DRAFT]`/`[FILE path:line]` template; MF-4; realises A6), C5 Deterministic Over Advisory (rc-17, s1; the **meta-pattern** — classify must-hold→MF-1 hook vs judgement→MF-2 advisory; don't hook everything), C6 Whole-Path Permission Coverage (rc-18, s1 *(nearest)*; allowlist covers whole routine path, mine telemetry; MF-1 under C5), C7 Enforced Skill Invocation (rc-19, s1; PreToolUse trigger-match hook blocks bypass; MF-1 instance of C5). Each §11 cites pack ids only; each wires one A.19 detection slot with a leading indicator. RU twins `12-11-patterns-B-ru.md` + `12-12-patterns-C-ru.md` produced via two parity-controlled subagents against the frozen EN files — both confirmed structurally identical (B: 6 `##` / 56 `###` / 4 `:End` / 44 table rows; C: 9 `##` / 98 `###` / 7 `:End` / 77 table rows; independently re-verified by orchestrator), all ids/citations/wikilinks verbatim, prose translated to engineering Russian, twin-pointers swapped. Orchestrator-only ledger bookkeeping (no subagent touched PROGRESS.md). **S4 complete — all four files ✅. Next start point: S5 — `12-13-patterns-D.md` + `12-14-patterns-E.md` (+`-ru`), the 9 Design patterns D1–D4, E1–E5, drafted against the frozen S3 exemplars.**
- **2026-06-28 — S5 (Layers D + E).** Authored `12-13-patterns-D.md` (EN) by hand: intro + a shared `## D:0` Layer-D **design contract** that **inherits the C:0 design contract** (D–F are all Design / direct-Work per `11-fpf-diagnostic` D2), specialised to workflow topology — cause is the user-owned pipeline shape, not config inside one agent — + the **4 Layer-D Design patterns D1–D4**, each to the full `E.8` template (FPF kind = Design / workflow topology). Coverage: D1 Re-Entry Across Phase Boundary (rc-20, s8; MF-3 controlled return, L16 Plan↔Execute gate, L18; spiral-model episteme; distinct from B2's *context*-break re-entry), D2 Atomic Single-Form Emission (rc-21, s5; MF-6 at stage granularity, L04 floor, build-system single-source episteme; turn-scale sibling of A2/B4), D3 Roadmap-Anchored Dispatch (rc-22, s8; MF-5 parallel dispatch + MF-4 durable roadmap, L18 +90.2%, L17; make/Bazel DAG episteme — fixes both no-parallelism and no-tracking via one anchor), D4 Enforced Role Lanes (rc-23, s8; MF-1 per-agent tool/scope hook + MF-5, ME-4 [L20], L18; RBAC/least-privilege episteme; per-agent instance of the C5 meta-pattern). Then authored `12-14-patterns-E.md` (EN) by hand: intro + a shared `## E:0` Layer-E **design contract** (inherits C:0, specialised to the verification surface) + the **5 Layer-E Design patterns E1–E5** (FPF kind = Design / verification surface). Coverage: E1 Claim Requires Observed Event (rc-24, s6; MF-1 Stop/SubagentStop history check, ME-4 [L20], L16; pre-flight-checklist episteme; cheapest E-gate — harness already records the evidence), E2 Enforced Citation Anchors (rc-25, s6; MF-1 resolve-or-block Stop scan, L15, A6 link; scholarly-citation episteme; boundary-check complement of A6's write-side anchoring), E3 Counter-Evidence Audit (rc-26, s6; **MF-2 advisory** — judgement claims have no mechanical check; Fisher's maxim shared with A1/C3; falsificationism episteme; L19, ME-2 [L06]), E4 Input-Order Fidelity (rc-27, s6; MF-6 order check, L02 literalness; stable-sort episteme; distinct from A2 delta), E5 Quiet Toolchain Output (rc-28, s5; MF-6 `--quiet`+structured-on-failure, L03 tokenizer tax, L04 floor; log-level/"no news is good news" episteme; D2's MF-6 sibling on tool output, protects A4/B1 context-integrity). Each §11 cites pack ids only (no quotes); each wires one A.19 detection slot with a leading indicator (D1/D3/D4→s8, D2→s5; E1/E2/E3/E4→s6, E5→s5). RU twins `12-13-patterns-D-ru.md` + `12-14-patterns-E-ru.md` produced via two parity-controlled subagents against the frozen EN files; orchestrator independently re-verified (D: 6 `##` / 56 `###` / 4 `:End` / 36 table rows; E: 7 `##` / 70 `###` / 5 `:End` / 45 table rows — all EN≡RU), heading ids + `:End` sentinels + L-/ME-/MF-/`FPF-Spec.md:` ids verbatim, prose translated to engineering Russian, twin-pointers swapped, `## См. также` normalised to the frozen house style. Orchestrator-only ledger bookkeeping (no subagent touched PROGRESS.md). **S5 complete — all four files ✅. Next start point: S6 — `12-15-patterns-F.md` (F1–F2) + `12-20-local-practice-edition.md` (+`-ru`), the Layer-F process patterns plus the Local Practice edition with E.4.PFR relation/dependency records; refs E.8, E.4.PFR, E.5.3, digest §6, `03-current-config-map`.**
- **2026-06-28 — S6 (Layer F + Local Practice edition).** Authored `12-15-patterns-F.md` (EN) by hand against the frozen S3–S5 house style: intro + a shared `## F:0` Layer-F **design contract** (inherits C:0, specialised to the process/git-hygiene surface — Layer F is wholly deterministic, every gate an MF-1 hook) + the **2 Layer-F Design patterns F1–F2**, each to the full `E.8` thirteen-section template (FPF kind = Design / process). Coverage: F1 Bounded Branch Freshness (rc-29, S-025, s6 verification-fidelity *(nearest, retained from frozen 12-02)*; MF-1 freshness gate before integration claim, echoes L15 advisory-ceiling + L16 harness-gate; continuous-integration / trunk-based episteme — the branch's integration-readiness is a *claim* backed by an observed freshness check), F2 Deterministic Commit Hygiene (rc-30, S-026, s1 instruction-adherence; MF-1 `PreToolUse(git commit)` trailer-strip, echoes L15 + G.2-F2 instruction-adherence ceiling + ME-4 [L20] prompt-level "don't" insufficient; commit-hook / DCO episteme — the Co-Authored-By ban must *hold* mechanically, not rely on adherence). Each §11 cites pack ids only (no quotes); each wires one A.19 detection slot with a leading indicator (F1→s6, F2→s1). Then authored `12-20-local-practice-edition.md` (EN) by hand — the **Layer-2 Local Practice edition** mapping this user's `dot_claude/` realisation onto all 30 Layer-1 patterns via `E.4.PFR`: §0 Edition declaration (LAQF-Local v0.1, status build-with-gaps), §1 `FrameworkEditionDependencyRecord` (Local → Domain LAQF → FPF Core, `E.5.3` upward-only/acyclic, lag admissible), §2 six realisation sub-tables §2.A–§2.F (LAQF | Domain pattern | Local realisation | Family | Status), §3 six `PatternFrameworkRelationRecord` LR1–LR6 (LR1 b2-handoff realised, LR2 d4-lanes realised, LR3 c5-hooks partial, LR4 f2-trailer-gap, LR5 f1-freshness-gap, LR6 e4-order-gap), §4 `FrameworkPackageManifest`, §5 `G.11` currentness/refresh T4 (T4a–T4d + gap backlog), §6 `E.5.3` conformance check (4 questions). Grounded in `03-current-config-map.md`: tally ✅ 2 realised (B2, D4) / ◐ 19 partial / ⬜ 9 gap (B3, C1, C2, C3, C4, C7, E2, E4, F1) — the 9 gaps concretise `compatibilityBoundary: Local may lag Domain` and double as the improvement backlog (lag, not contradiction → E.5.3-conformant). RU twins `12-15-patterns-F-ru.md` + `12-20-local-practice-edition-ru.md` produced via two parity-controlled subagents against the frozen EN files; orchestrator independently re-verified (F: 4 `##` / 28 `###` / 2 `:End` / 22 table rows; 20: 8 `##` / 6 `###` / 0 `:End` / 51 table rows — all EN≡RU), heading/pattern/relation ids + L-/ME-/MF-/G.2-/`FPF-Spec.md:` ids + fenced-record field keys verbatim, prose translated to engineering Russian, twin-pointers swapped, `## См. также` normalised. Orchestrator-only ledger bookkeeping (no subagent touched PROGRESS.md). **S6 complete — all four files ✅. All 30 patterns + both editions now authored. Next start point: S7 — Integrate + QA: author `README.md` index; wire `seminar_timeline.md` + `00-MoC.md` as iteration 3.**
- **2026-06-28 — S7 (Integrate + QA). BUILD COMPLETE.** Authored `README.md` — the framework's **first-entry carrier** (`E.4.DPF` step 10) and home of the quality cycle (step 8) + admission note (step 9). Nine sections: §1 cold-reader entry table; §2 file map (all 10 units, EN · RU links, purpose, session); §3 the 30 patterns at a glance (six layers, ID · ratified title · RC · A.19 detection characteristic — titles re-extracted from the frozen pattern files, confirmed identical to §6 roster); §4 the eight measurement characteristics; §5 Layer-2 status (✅2 / ◐19 / ⬜9, gaps = E.5.3-conformant lag); §6 **`E.21` PatternQualityEvaluation** over the Layer-1 edition as pattern-of-concern — E.22 floorEvaluation frame + PrecisionRestorationProfile (overallEffect boundedLocal) + all **19 RequiredPatternQualityCoordinates** scored with adjacent-value ShortRationales (honest floors: 14×4, 5×3; **no 5 claimed** — every coordinate has a named limit), PatternQualityStatus=sufficientlyExpressedForDeclaredUse, explicit StopCondition; §7 **`E.19` admission run** consuming that E.21 — PCP-BASE 9-check triage (all pass), risk profiles PCP-PRAG/SOTA/BRIDGE/TERM/REFRESH, Delta-Class Δ-0 vs Core (writes nothing into Core, impact radius none), decision **admit-for-landing as local monolith v0.1 build-with-gaps** (the 9 Layer-2 gaps are lag, not blockers), plus the E.19:4.1 project-side-reuse boundary ("pattern review passed ≠ agent fixed"); §8 provenance + G.11 refresh route + seminar context. README authored in English as a hub/index (matching the English-only house style of `00-MoC.md` and `seminar_timeline.md`), linking both EN and RU twins per unit — no `-ru` twin per the §8 ledger. Then wired **iteration 3** into `seminar_timeline.md` (new table row 3 + refreshed "Next moves": iteration 1's pending attention-budget ledger is now pattern LAQF.B3; remaining = realise 9 Layer-2 gaps, field-calibrate bands, build catalogue WorkPlan DAG) and into `00-MoC.md` (its stale seminar table stopped at iteration 1 — added rows 2 and 3 and dropped row 1's obsolete forward-reference, matching the file's `FPF_Seminar/` link prefix). All artefacts British English; no Co-Authored-By trailers. **S7 complete — all three files ✅. The LAQF DPF build is COMPLETE: 21 framework files (10 units × EN/RU + spine) + README + 2 seminar wirings, across sessions S0–S7.**
