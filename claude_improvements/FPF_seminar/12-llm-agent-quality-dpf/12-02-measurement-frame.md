---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, measurement-frame, a19-charspace, c16-mmchr]
seminar-iteration: 3
created: 2026-06-28
status: measurement-frame
method: FPF A.19 (CharacteristicSpace) · C.16 (MM-CHR / U.DHCMethod) · A.17 (Characteristic) · A.18 (CSLC) · consumes G.2 pack LAQF.sota.iter3.palette
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-02-measurement-frame-ru]]"
---

# LAQF — measurement frame (A.19 CharacteristicSpace + C.16 operational overlay)

This is the declared `CharacteristicSpace` LAQF measures against (`A.19`, `FPF-Spec.md:24417`). It mints the eight measurement characteristics the spine forward-references ([[12-00-spine]] §5, relation R2) by consuming the G.2 pack's §3 `OperatorAndObjectInventory` and §4.2 `Γ_epist` records **by id** — never re-paraphrasing the evidence (`G.2:4.2` handoff contract, `FPF-Spec.md:87904`). Each characteristic gets one `U.DHCMethod` card (one Characteristic, one Scale, declared polarity, evidence stub — `C.16`, `FPF-Spec.md:42826`); green/amber/red **bands are a separately-named CAL overlay**, not baked into the bare methods, because thresholds and acceptance bands are out of scope for the `U.DHCMethod` template (`C.16:5.3.1` R-MT-3 keeps only polarity + target at the template, `FPF-Spec.md:42945`; `A19-CS-5` forbids hidden normalisations inside the space, `FPF-Spec.md:24544`). The frame hands each characteristic to its pattern's detection slot in S3–S6 (§5).

## §0 Scope / entityOfConcern (A.19:0, `FPF-Spec.md:24428`)

| Slot | Declaration |
|---|---|
| **entityOfConcern** | `⟨GroundingHolon = an LLM coding agent in a session, ReferencePlane = world⟩` — agent behaviour under a finite attention/context budget, not the model weights (inherited from [[12-01-source-pack]] §0). |
| **Bounded context** | `AION_AUTOPOIESEON` / `claude_improvements` / FPF-seminar:iter3 ([[12-00-spine]] §1). |
| **Consumed palette** | `SoTAPaletteDescription` **`LAQF.sota.iter3.palette`** ([[12-01-source-pack]] §8): §3 `OperatorAndObjectInventory` (8 candidate characteristics + 6 operator-family stubs), §4.2 `Γ_epist` **G.2-F1** (context cliff) + **G.2-F2** (instruction-adherence ceiling), `ClaimSheets` T1–T5, `MicroExamples` ME-1…ME-4, `MethodFamilyCards` MF-1…MF-6. |
| **Space object** | The A.19 EoC here is the **CharacteristicSpace itself** (`LAQF.charspace.iter3`, §1) — not a score table, dashboard, or evaluation result over it (`A.19:1` E.24.UK settlement, `FPF-Spec.md:24455`). |
| **Plane discipline** | All eight characteristics are single-entity (`U.EntityCharacteristic`, `A.17:4` R8, `FPF-Spec.md:24181`) of the agent-in-session holon; no relational slots. |

---

## §1 CharacteristicSpace declaration — A.19 (`FPF-Spec.md:24512`)

`U.CharacteristicSpace` **`LAQF.charspace.iter3`** = the Cartesian product of eight slot value sets (`A.19:5.1.1`, `FPF-Spec.md:24526`). Each slot binds **exactly one** Characteristic to **exactly one** Scale (`A19-CS-1`, `FPF-Spec.md:24536`), with declared polarity per `A.17:4` R6 (`FPF-Spec.md:24177`). The basis is the ordered slot list below (`A19-CS-2` named basis, `FPF-Spec.md:24538`).

```text
U.CharacteristicSpace  LAQF.charspace.iter3
  basis (ordered slots, A19-CS-2):
    s1 instruction-adherence   Scale: rate 0–1 (violations/session, read as 1−rate)  polarity: ↑-better
    s2 reconnaissance-depth    Scale: ratio ≥0 (reads-per-edit)                       polarity: ↑-better (diminishing)
    s3 context-integrity       Scale: % effective-fill 0–100                          polarity: target-is-best (low band)
    s4 sycophancy-rate         Scale: rate (modified-version events / 50 turns)       polarity: ↓-better
    s5 output-economy          Scale: count (tokens|lines / turn|stage)               polarity: ↓-better (floored)
    s6 verification-fidelity   Scale: rate 0–1 (claims-with-observed-event / claims)  polarity: ↑-better
    s7 attention-budget-load   Scale: count (instruction-stack lines; conflict pairs) polarity: ↓-better (ceiling)
    s8 scope-fidelity          Scale: ratio 0–1 (edit-target ∩ named-scope / edits)   polarity: ↑-better
  arity:            all slots U.EntityCharacteristic (bearer = agent-in-session), A.17:4 R8
  comparability:    same-template only (C.16 R-CMP-1, FPF-Spec.md:43007); cross-slot comparison undefined
  normalisation:    NONE inside the space (A19-CS-5, FPF-Spec.md:24544) — the eight are
                    NOT summed, averaged, or folded into a single LAQF score
  declared overlay: LAQF.cal.iter3 (§3) — a CAL band overlay; the ONLY declared overlay,
                    attached explicitly, not implicit (A.19:5.1.3, FPF-Spec.md:24552)
  missingness:      a slot with no observable event in a session reads not-applicable,
                    not zero (A19-CS-6 slot-meta completeness, FPF-Spec.md:24548)
```

**No single score.** There is no `ScoringMethod 𝒢` over the eight coordinates in this frame. Any future composite must be an explicit external `𝒢` on the coordinate vector, disclosed with bounded codomain and polarity-compatible monotonicity (`A.17:4.1` I7, `FPF-Spec.md:24193`; `C.16` R-G𝒢-1, `FPF-Spec.md:43012`) — it is deliberately not minted here.

---

## §2 Per-characteristic DHCMethod cards — C.16 (`FPF-Spec.md:42937`)

One `U.DHCMethod` per slot: one Characteristic, one Scale, declared polarity (R-MT-1/-3, `FPF-Spec.md:42941`), the measurement operator, and an `U.EvidenceStub` (R-EV-1 type-of-ground + identifier, `FPF-Spec.md:42991`). **Thresholds are absent by design** — they live in §3.

```text
U.DHCMethod  laqf.mm.s1.instruction-adherence
  characteristic: instruction-adherence       scale: rate 0–1        polarity: ↑-better
  operator:       1 − (stated-rule-violated events ÷ stated-rule-applicable events) per session
  evidenceStub:   hook logs (PreToolUse exit-2 fires), tool-call history, commit-trailer scans [L22 OTel]
  backing:        G.2-F2 (instruction-adherence ceiling); L15 (CLAUDE.md ≈70% advisory); L12 (IFScale 68%@500)

U.DHCMethod  laqf.mm.s2.reconnaissance-depth
  characteristic: reconnaissance-depth         scale: ratio ≥0       polarity: ↑-better (diminishing)
  operator:       count(Read|Grep|Glob calls) ÷ count(Edit|Write calls) per task
  evidenceStub:   tool-call history (read-class vs edit-class events) [L22]; Disclosure-block presence
  backing:        ME-1 [L05] (reads-per-edit 6.6→2.0); L02 (literal, reasoning-over-tool-calls)

U.DHCMethod  laqf.mm.s3.context-integrity
  characteristic: context-integrity            scale: % fill 0–100   polarity: target-is-best
  operator:       effective-fill % = tokens-in-window ÷ window-budget, tokenizer-adjusted (+~30% per L03)
  evidenceStub:   session token meter; post-compaction task-identity check (constraints retained?) [L22]
  backing:        G.2-F1 (operational cliff); ME-3 [L10] (MRCR 93→76%); L07, L08, L11 (50/60/75 cluster)
  target:         stay below the operational fill band (R-MT-3 names the target; band itself → §3)

U.DHCMethod  laqf.mm.s4.sycophancy-rate
  characteristic: sycophancy-rate              scale: rate           polarity: ↓-better
  operator:       count("modified version of what was asked" events) per 50 turns
  evidenceStub:   turn transcript; multi-file edits triggered by single-item feedback [L22]
  backing:        ME-2 [L06] (arguing loop, modified-version); L19 (RLHF sycophancy, over-correction)

U.DHCMethod  laqf.mm.s5.output-economy
  characteristic: output-economy               scale: count          polarity: ↓-better (floored)
  operator:       tokens/turn; lines/stage; tokens/Bash on passing runs
  evidenceStub:   emission length per turn; toolchain stdout volume on green runs [L22]
  backing:        L04 (≤25/≤100 brevity cap reverted after 3% eval drop — the FLOOR); L03 (tokenizer)

U.DHCMethod  laqf.mm.s6.verification-fidelity
  characteristic: verification-fidelity        scale: rate 0–1       polarity: ↑-better
  operator:       count(terminal claims backed by an observed tool event) ÷ count(terminal claims)
  evidenceStub:   claim ↔ tool-call-history join; citation anchors resolved to path/quote [L22]
  backing:        ME-4 [L20] (disobeyed direct commands → claim≠event); L16 (Plan-Mode gate)

U.DHCMethod  laqf.mm.s7.attention-budget-load
  characteristic: attention-budget-load        scale: count          polarity: ↓-better (ceiling)
  operator:       instruction-stack line count + conflicting-rule-pair count + always-on-skill token ratio
  evidenceStub:   measured stack (UAP+project+workspace CLAUDE.md); conflict register [L23]
  backing:        G.2-F2; L12 (IFScale 68%@500, earlier-instruction bias); L23 (509-line stack)
  target:         below the model's ~150-instruction effective attention (R-MT-3 target; band → §3)

U.DHCMethod  laqf.mm.s8.scope-fidelity
  characteristic: scope-fidelity               scale: ratio 0–1      polarity: ↑-better
  operator:       count(edits whose target ∈ user-named scope) ÷ count(edits); inverse: out-of-lane calls
  evidenceStub:   edit-target paths vs named-scope set; per-agent tool/scope lane logs [L22]
  backing:        L02 (literal, no one-to-another generalisation); L18 (subagent scope lanes)
```

Each card states its applicability frame (the agent-in-session holon, R-MT-4, `FPF-Spec.md:42947`) and a time stance of *as-observed-per-session* or *as-aggregated-over-window* (R-ME-4, `FPF-Spec.md:42967`). No card carries a green/amber/red boundary — that is the CAL overlay's job (§3).

---

## §3 CAL calibration overlay — the bands (`LAQF.cal.iter3`)

A **separately-named, explicitly-declared** overlay over `LAQF.charspace.iter3`. It attaches a green/amber/red band + a leading indicator to each slot. Declared here, not in §1's space and not in §2's methods, per `A19-CS-5` (`FPF-Spec.md:24544`) and `C.16` R-CMP-2 (transformed/threshold comparability is **cited, not defined** at the method, `FPF-Spec.md:43010`). Every band cites its backing pack id. Bands anchored to a single interpolated number are marked **[interp]** — they are calibration choices, not citable SLAs, consistent with the source pack's honest treatment of the cliff (G.2-F1 `residualLoss`).

```text
CALOverlay  LAQF.cal.iter3   attachesTo: LAQF.charspace.iter3 (§1)   status: calibration, not SLA
```

| Slot | Green | Amber | Red | Backing id |
|---|---|---|---|---|
| s1 instruction-adherence | ≥0.90 (≤1 violation/10 applicable) | 0.70–0.90 | <0.70 | G.2-F2; L15 (≈70% advisory ceiling = amber/red boundary); L12 |
| s2 reconnaissance-depth | ≥3.0 reads-per-edit | 2.0–3.0 | <2.0 | ME-1 [L05] (2.0 = Laurenzo floor = red boundary; ≥3.0 target) |
| s3 context-integrity | <50% effective-fill | 50–75% | >75% | G.2-F1; L11 (50 early / 60 clear / 75–77 autocompact). ~55% rotate point = **[interp]**, not a hard line |
| s4 sycophancy-rate | 0 modified-version / 50 turns | 1–2 / 50 turns | ≥3 / 50 turns | ME-2 [L06]; L19. Band thresholds **[interp]** (no controlled session-rate exists) |
| s5 output-economy | task-necessary content only | mild padding | graphomania | L04 (**floor**: do NOT clamp below task-necessary — ≤25/≤100 caused a 3% eval drop). No hard upper number |
| s6 verification-fidelity | ≥0.95 claims-with-event | 0.80–0.95 | <0.80 | ME-4 [L20]; L16. Band thresholds **[interp]** off the "prompt-level don't is not a forbid" finding |
| s7 attention-budget-load | ≤~150 stack lines, 0 conflict pairs | 150–509 lines | >509 lines | G.2-F2 (~150 attention); L23 (509-line measured baseline = red boundary); L12 |
| s8 scope-fidelity | ≥0.95 in-scope edits | 0.80–0.95 | <0.80 | L02; L18. Band thresholds **[interp]** off the literal-scope finding |

**Floor discipline (s5).** `output-economy` is `↓-better` but **floored**: the green band is "task-necessary content", not "minimal tokens". L04 is the explicit floor — Anthropic reverted ≤25/≤100-word caps after a 3% eval drop. Over-clamping is a red-equivalent failure on the *other* side; the overlay does not set a hard low number (`R-MT-3` declines tolerance/fall-off semantics, `FPF-Spec.md:42945`).

**Interpolation honesty.** s3's ~55% rotate point, and the s4/s6/s8 band thresholds, are calibration interpolations over the cited evidence, not controlled measurements. They re-band on refresh (§6). G.2-F1 itself records that no controlled study fixes a single % for the cliff.

---

## §4 Leading vs lagging indicators

For each slot: the cheap **leading** signal observable mid-session (what the Layer-2 Local Practice edition wires to hooks/telemetry, L22), versus the **lagging** outcome that confirms it.

| Slot | Leading (mid-session, cheap) | Lagging (outcome) |
|---|---|---|
| s1 instruction-adherence | PreToolUse hook near-miss count; trailer-scan hits | stated-rule-violated events surfacing in review |
| s2 reconnaissance-depth | live reads-per-edit ratio; Disclosure-block present | premature-action / rework events (ME-1 cheapest-action default) |
| s3 context-integrity | effective-fill % (tokenizer-adjusted) | post-compaction task-identity loss; constraint drop (B2) |
| s4 sycophancy-rate | per-turn "modified-version" flag | multi-turn arguing loop (3–5 turns, ME-2) |
| s5 output-economy | tokens/turn, lines/stage running tally | reader-reported graphomania / under-delivery |
| s6 verification-fidelity | claim-emitted-without-prior-tool-event flag | false "build/test passed" reaching the user (E1) |
| s7 attention-budget-load | instruction-stack line count; conflict-pair register | adherence drift as stack grows (G.2-F2 plateau) |
| s8 scope-fidelity | edit-target ∉ named-scope flag; out-of-lane call | scope-creep / role-boundary violation (D4) |

The leading column is the operational payload: it is computable from tool-call history, hook logs, and OTel events ([L22]) **without** waiting for the lagging outcome. This is the §5 detection axis each S3–S6 pattern's §11 slot consumes.

---

## §5 Pattern ↔ characteristic index

Each characteristic is the **primary detection axis** for the patterns below (pulled from [[12-00-spine]] §5 roster and [[_inputs/rc-digest]] §7). This is the handoff each S3–S6 pattern's §11/detection slot consumes (spine relation R2, [[12-00-spine]] §4.3).

| Slot | Characteristic | Primary detection axis for (LAQF patterns) |
|---|---|---|
| s1 | instruction-adherence | C5, C6, C7, F2 |
| s2 | reconnaissance-depth | A5, A6, A7, C4 |
| s3 | context-integrity | A4, B1, B2 |
| s4 | sycophancy-rate | A1, C3 |
| s5 | output-economy | A2, A3, B4, D2, E5 |
| s6 | verification-fidelity | E1, E2, E3, E4, F1 |
| s7 | attention-budget-load | B3, C1, C2 |
| s8 | scope-fidelity | A8, D1, D3, D4 |

All 30 patterns (A1–F2) are covered; each wires to ≥1 characteristic (frozen authoring convention, [[12-00-spine]] §5). Where the spine marked a "*(nearest)*" axis (C6 → s1, F1 → s6), that nearest-fit is retained pending per-pattern authoring.

---

## §6 Conformance & refresh

**A.19 / C.16 / A.17 / A.18 conformance.**

1. **One characteristic, one scale per slot** — `A19-CS-1` (`FPF-Spec.md:24536`), C.16 R-MT-1 (`FPF-Spec.md:42941`): all eight cards (§2) bind exactly one Characteristic to one Scale.
2. **Polarity declared at the template** — `A.17:4` R6 (`FPF-Spec.md:24177`), C.16 R-MT-3 (`FPF-Spec.md:42945`): every slot declares ↑/↓/target (§1, §2).
3. **No implicit normalisation across the eight** — `A19-CS-5` (`FPF-Spec.md:24544`): no single LAQF score; cross-slot comparison undefined (C.16 R-CMP-1, `FPF-Spec.md:43007`).
4. **Bands as a declared overlay, not baked in** — `LAQF.cal.iter3` (§3) is the only declared overlay (`A.19:5.1.3`, `FPF-Spec.md:24552`); thresholds are kept out of the bare methods (C.16 R-MT-3 declines tolerance/fall-off, R-CMP-2 cites transformed comparability, `FPF-Spec.md:43010`).
5. **Evidence stub per method** — C.16 R-EV-1 (`FPF-Spec.md:42991`): each card names a type-of-ground + identifier (hook logs, tool-call history, OTel events [L22]).
6. **By-id consumption** — all backing cites pack components by L-id / ME-id / Γ_epist id, never paraphrase (`G.2:4.2`, `FPF-Spec.md:87904`).

**Required pins.** `CharacteristicSpaceId = LAQF.charspace.iter3`; `CALOverlayId = LAQF.cal.iter3`; consumed `SoTAPaletteDescriptionId = LAQF.sota.iter3.palette`; `GammaEpistSynthId = {G.2-F1, G.2-F2}`.

**Refresh route (delegates to spine §6 / G.11, `FPF-Spec.md:91923`).** Re-band when a SoTA anchor is superseded. The frame does not own its own refresh vocabulary — it names the currentness object and delegates to the spine `RefreshPlan@Context` `LAQF.refresh.v0` ([[12-00-spine]] §6), per `G.11:0.3` (DPF-seed artifacts name the currentness object directly, `FPF-Spec.md:91952`):

- **spine T1 (model generation)** → re-test polarities and re-measure all eight bands (a 5.x generation may shift the cliff and the attention ceiling).
- **spine T2 (SoTA decay)** → an anchor superseded (IFScale, MRCR v2, reads-per-edit, tokenizer, brevity-cap, 509-line baseline) → re-harvest via G.2 → [[12-01-source-pack]], then re-band the affected slot(s) in §3.
- **spine T3 (Core bump)** → re-grep the `FPF-Spec.md:<line>` pins for A.17–A.19 / C.16; re-check `A19-CS-5` conformance.

`G.11` records the scoped re-band action; it does **not** decide whether the frame improved — that is E.21/E.23 at S7 (`FPF-Spec.md:91952`).

---

## See also

- [[12-02-measurement-frame-ru]] — Russian twin
- [[12-01-source-pack]] — G.2 SoTA pack; consumed §3 inventory + §4.2 Γ_epist (palette `LAQF.sota.iter3.palette`)
- [[12-00-spine]] — keystone; §5 pattern roster, §4.3 relation R2, §6 refresh route
- [[_inputs/rc-digest]] — §7 eight characteristics, §8 SoTA anchors
- [[PROGRESS]] — build ledger (§7 session DAG, §8 inventory, §9 log)
- `FPF-Spec.md:24417` A.19 CharacteristicSpace · `:24129` A.17 Characteristic · `:24265` A.18 CSLC · `:42826` C.16 MM-CHR · `:87746` G.2 · `:91923` G.11
