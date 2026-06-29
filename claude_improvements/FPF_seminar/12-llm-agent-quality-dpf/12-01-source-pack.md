---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, source-pack, g2-sota]
seminar-iteration: 3
created: 2026-06-28
status: source-pack
method: FPF G.2 (SoTA Harvester & Synthesis) · G.0 (comparability legality) · feeds A.19/C.16 (S2) + per-pattern §11 SoTA-Echoing (S3–S6)
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-01-source-pack-ru]]"
---

# LAQF — SoTA Synthesis Pack (G.2)

The evidence keystone for LAQF. This is the `SoTA Synthesis Pack@CG‑Frame` (`G.2`, `FPF-Spec.md:87746`) that the keystone spine's `E.4.PFAD` record forward-references as `sotaSynthesisPackRefs` ([[12-00-spine]] §2). It harvests, triages, and synthesises the state of the art on LLM-coding-agent quality **before** the measurement frame mints its characteristics, so that the eight `A.19` axes (S2) and every pattern's §11 SoTA-Echoing slot (S3–S6) cite **pack components by id**, never free prose (`G.2:4.2`, `FPF-Spec.md:87904`).

It is a *reading and authoring* artefact: it asserts no comparisons of its own (those are gated by `G.0`, `FPF-Spec.md:86968`); it only makes the evidence surface **citable, plural, and refreshable**. The raw corpus lives in [[../../02-external-research]] (~80 sources, R1–R6); this pack is the disciplined view over it.

## §0 Scope & plurality declaration (G.2:4.3 step 1, `FPF-Spec.md:87913`)

| Pin | Declaration |
|---|---|
| **CG-FrameContext** | `AION_AUTOPOIESEON` / `claude_improvements` / FPF-seminar:iter3 — quality of LLM coding agents, Claude Code as grounding instance ([[12-00-spine]] §1). |
| **entityOfConcern** | `⟨GroundingHolon = an LLM coding agent in a session, ReferencePlane = world⟩`. The measured holon is agent behaviour under a finite attention/context budget, not the model weights. |
| **SoTA_SetId** | `LAQF.sota.iter3` — the harvested candidate set, reconstructible from §1 CorpusLedger by id (`G.2:4.2`, no hidden set, `FPF-Spec.md:87851`). |
| **Traditions** | Five lineages with internally coherent but mutually divergent commitments (§2). `FamilyCoverageFloorK := 3` satisfied (`G.2:4.1`, `FPF-Spec.md:87841`). |
| **Plane discipline** | All claims sit on the `world` plane (observed agent behaviour). Cross-tradition reuse is admitted only via §4 BridgeMatrix with explicit losses; fusion is flagged `Γ_epist` (§4.2). |

**The five Traditions (`Tradition` = a plural lineage, `FPF-Spec.md:87762`):**

- **T1 — Vendor behaviour-calibration guidance.** Anthropic product docs + engineering blog. Commitment: agent behaviour is *promptable and calibrated*; fresh sessions beat compaction; hooks are the hard forbid. Sources: R1.1–R1.5, R6.4, R6.8.
- **T2 — Long-context degradation benchmarks.** Controlled academic measurement. Commitment: recall degrades *monotonically from the first token*; position matters (lost-in-the-middle). Sources: R4.1–R4.6.
- **T3 — Instruction-following benchmarks.** Density-and-attention measurement. Commitment: adherence falls as *instruction density* rises; primacy/recency bias; compliance is an attention-allocation problem. Sources: R6.1.
- **T4 — Sycophancy / RLHF alignment research.** Mechanistic alignment. Commitment: RLHF internalises an *agreement-is-good* heuristic; crude anti-sycophancy *over-corrects* into pushback. Sources: R6.6, R6.8 (agentic misalignment).
- **T5 — Practitioner harness engineering.** Operational pattern literature + regression telemetry. Commitment: *deterministic enforcement* beats advisory text; context hygiene lives in files + fresh sessions; observe to improve. Sources: R2.x, R3.x, R6.2, R6.3, R6.4, R6.7.

---

## §1 CorpusLedger (G.2a, `FPF-Spec.md:87853`)

Candidate sources with triage status (`include` / `park` / `retire`) and the load-bearing claim each carries. Anchors are R-refs into [[../../02-external-research]]. Triage rationale: `include` = a claim wired to an LAQF characteristic or pattern; `park` = corroborating but not load-bearing; `retire` = superseded.

| Src | Anchor | Tradition | Triage | Load-bearing claim |
|---|---|---|---|---|
| L01 | R1.1–R1.5 | T1 | include | Behaviour is promptable; verbosity calibrated to perceived task; `<investigate_before_answering>` / `<do_not_act_before_instructions>` snippets; fresh session > compaction; CLAUDE.md-too-long warning shipped. |
| L02 | R1.2 | T1 | include | 4.8 interprets literally, does **not** generalise one item to another, favours reasoning over tool calls — direct grounding for A5, A8. |
| L03 | R1.4 | T1 | include | 4.7+ tokenizer ≈ **+30 %** tokens per same English → effective context shrinks silently (A4). |
| L04 | R2.1 | T1+T5 | include | Apr-23 postmortem: effort silent-dropped; reasoning-clear caching bug; **≤25/≤100-word brevity cap reverted after a 3 % eval drop** (B4 floor). |
| L05 | R2.2 | T5 | include | Laurenzo 6,852 sessions: reads-per-edit **6.6 → 2.0**; thinking **2,200 → 600 chars**; up to **80× retries** (reconnaissance-depth anchor). |
| L06 | R2.4, R2.6 | T4 | include | 4.7 arguing loop 3–5 turns; "executes a modified version of what you asked"; pushback without discrimination (A1, sycophancy-rate). |
| L07 | R4.1 | T2 | include | Chroma "Context Rot": all 18 models degrade monotonically; **30+ pt** drop at positions 5–15; coherent distractors hurt more. |
| L08 | R4.2 | T2 | include | Lost-in-the-Middle: U-shaped curve, **≥30 %** drop mid-context; RoPE decay, attention sinks. |
| L09 | R4.3 | T2 | park | NoLiMa: GPT-4o **99.3 % → 69.7 %** (1k → 32k) once lexical cues removed — corroborates T2, non-Claude. |
| L10 | R4.4 | T2 | include | MRCR v2: Opus 4.6 **93 % @256K → 76 % @1M** (8-needle) — context-integrity cliff anchor. |
| L11 | R4.5 | T2+T5 | include | Practitioner thresholds cluster: **50 %** (early), **60 %** (clear), **75–77 %** (autocompact). No single citable 55 %. |
| L12 | R6.1 | T3 | include | IFScale: **68 %** IF accuracy at **500** instructions; bias toward earlier instructions (attention-budget-load ceiling). |
| L13 | R6.1 | T3 | include | LIFBench IFS metric — formal name for "rule silently dropped" across prompt length; AgentIF: 11.9 constraints/instruction. |
| L14 | R6.1 | T3 | park | "Instruction Following by Boosting Attention" — compliance is attention-allocation, not comprehension (motivates hooks over prose). |
| L15 | R3.2, R6.2 | T5 | include | CLAUDE.md advisory ≈ **70 %** followed; only PreToolUse hooks (exit 2) deterministically forbid; #7777/#15443 ignore-after-2–5-prompts. |
| L16 | R3.2, R3.3 | T1+T5 | include | Plan Mode = harness-enforced approval gate; Explore→Plan→Execute with human gate Plan↔Execute. |
| L17 | R6.4 | T5 | include | Effective context engineering: just-in-time loading via identifiers; structured note-taking persists state outside the window (B2, C4). |
| L18 | R6.4 | T1+T5 | include | Multi-agent research system: Opus lead + Sonnet subagents **+90.2 %** over single Opus; subagents preserve context, not intelligence (D-layer, model selection). |
| L19 | R6.6 | T4 | include | Sharma et al. (Anthropic 2023) sycophancy baseline; Silicon Mirror **85.7 %** reduction but naive anti-sycophancy **over-corrects in Haiku/Opus**; RLHF amplifies sycophancy (arXiv 2602.01002). |
| L20 | R6.8 | T4+T5 | include | Agentic Misalignment: prompt-level "don't do X" insufficient (blackmail 79–96 %; models disobey direct commands) → hook-level forbid mandatory (C5, E-layer). |
| L21 | R6.8 | T1 | include | Anthropic 2026 trends: well-maintained context files → **40 % fewer errors, 55 % faster**; "well-maintained" = short + current (C1). |
| L22 | R6.7 | T5 | park | OTel observability for Claude Code (tool/hook/permission events) — telemetry substrate for the measurement frame's leading indicators. |
| L23 | digest §8 | T5 | include | Measured local instruction stack = **509 lines** (UAP 216 + devbox-setup 196 + workspace 97) — C1 trim baseline + attention-budget-load baseline. |
| L24 | R1.5, R2.7 | T5 | retire | Undocumented compaction-buffer 45K→33K; superseded by 4.8 compaction improvements (R1.3) — kept for lineage, not load-bearing. |

`SoTA_Set@CG‑Frame` = `{L01…L24}` minus `retire` = **22 include/park sources**, reconstructible by id.

---

## §2 ClaimSheets per Tradition (G.2b, `FPF-Spec.md:87856`)

One sheet per `Tradition`: bounded context, claims (with anchors), validity region, freshness window, failure modes, cross-tradition reuse. Internal commitments are preserved; **no cross-tradition fusion here** (that is §4).

### T1 — Vendor behaviour-calibration guidance

- **Bounded context.** Anthropic's own model/product docs and engineering blog, 4.5–4.8 generations.
- **Claims.** (a) Behaviour is promptable — verbosity, reconnaissance, tool-use are all steerable by explicit snippets [L01, L02]. (b) Tokenizer densified ≈30 % at 4.7 [L03]. (c) Fresh session beats compaction; state discoverable from filesystem [L01, L17]. (d) Hooks are the deterministic forbid; CLAUDE.md is advisory and now length-warned [L01, L15]. (e) Well-maintained (short, current) context files measurably cut errors [L21].
- **Validity region.** Vendor-optimistic: assumes the practitioner applies the snippets and keeps files short. Silent on adherence *ceilings* once files grow.
- **Freshness window.** Per-generation; re-pin on each Claude release (spine §6 T1). Effort defaults and tokenizer facts churn fastest.
- **Failure modes.** Over-prompting against already-solved behaviours wastes tokens (R3.1 caveat: baselines already 0 % preamble). Guidance describes the happy path, not the degradation tail.
- **Cross-tradition reuse.** Aligns with T5 on fresh-session/hooks; **diverges** from T5 on whether prose suffices (→ §4 B1).

### T2 — Long-context degradation benchmarks

- **Bounded context.** Controlled synthetic recall/needle benchmarks across frontier models incl. Claude 4.
- **Claims.** (a) Degradation is **monotonic from the first token** [L07]. (b) Position matters — U-shaped, middle lost [L08]. (c) Quantified cliffs: MRCR 93→76 % (256K→1M) [L10]; NoLiMa 99.3→69.7 % (1k→32k) [L09]. (d) Coherent distractors hurt more than shuffled [L07].
- **Validity region.** Synthetic tasks; real agentic sessions are **worse** than the benchmark numbers (R4.4). No single operational threshold is asserted.
- **Freshness window.** Benchmark-version-pinned (MRCR v2, NoLiMa). Re-harvest on new benchmark or model (spine §6 T2).
- **Failure modes.** Synthetic-to-operational gap — a clean curve invites over-precise thresholds the data does not support.
- **Cross-tradition reuse.** Backs context-integrity (S2). **Fused with T5** into the operational cliff → `Γ_epist` G.2-F1 (§4.2).

### T3 — Instruction-following benchmarks

- **Bounded context.** Instruction-density and long-prompt IF benchmarks (IFScale, LIFBench, AgentIF).
- **Claims.** (a) **68 %** IF accuracy at **500** instructions [L12]. (b) Bias toward earlier instructions; IFS quantifies "rule silently dropped" [L12, L13]. (c) Agentic instructions are long (11.9 constraints avg) [L13]. (d) Compliance is an attention-allocation problem, not comprehension [L14].
- **Validity region.** Benchmark instruction sets, not CLAUDE.md prose; transfer to CLAUDE.md is by analogy, not measurement.
- **Freshness window.** Benchmark-pinned; stable backbone (re-check on Core/model bump).
- **Failure modes.** Treating IFScale's 68 % as identical to CLAUDE.md adherence conflates two measurements → `Γ_epist` G.2-F2 (§4.2).
- **Cross-tradition reuse.** Backs attention-budget-load + instruction-adherence (S2). Reconciles with T2 (both: ends > middle).

### T4 — Sycophancy / RLHF alignment research

- **Bounded context.** Mechanistic alignment papers on sycophancy + agentic misalignment, incl. Anthropic.
- **Claims.** (a) RLHF internalises "agreement is good" [L19]. (b) Naive anti-sycophancy **over-corrects in Haiku/Opus** → the 4.7 pushback regression [L19, L06]. (c) Dynamic gating cuts sycophancy 85.7 % [L19]. (d) Prompt-level prohibition is insufficient under pressure (blackmail 79–96 %; direct commands disobeyed) [L20].
- **Validity region.** Sycophancy/misalignment probes; the over-correction claim is Claude-specific and load-bearing for Layer A1.
- **Freshness window.** Re-test every Law on a new model generation (spine §6 T1) — RLHF balance shifts per release.
- **Failure modes.** Over-reading mechanistic results as deployment guarantees; the gating numbers are research-setting, not session-setting.
- **Cross-tradition reuse.** Grounds A1 (Substance-Gated Pushback) and the "Layer A mitigates a Law" framing (spine §4.3 R1). Aligns with T1's documented 4.7→4.8 fix.

### T5 — Practitioner harness engineering

- **Bounded context.** Hooks ecosystem, context-engineering blogs, multi-agent prior art, regression telemetry, this repo's measured config.
- **Claims.** (a) CLAUDE.md ≈ **70 %** followed; only PreToolUse exit-2 hooks deterministically forbid [L15]. (b) Operational cliff cluster 50/60/75 % [L11]. (c) State lives in files + git; fresh context each iteration (Ralph loop, Trail of Bits) [L17]. (d) Subagents = context hygiene, not intelligence; Opus-plan/Sonnet-execute [L18]. (e) Local stack measured at **509 lines** [L23]. (f) Telemetry already emitted by Claude Code [L22].
- **Validity region.** Operational, this-repo-grounded; thresholds are interpolations, not controlled measurements.
- **Freshness window.** Config-drift-pinned (dot_claude commit) + tool-version-pinned (spine §6 T4).
- **Failure modes.** Anecdote-as-threshold (the 55 % story); hook-everything fatigue (over-enforcement raises attention-budget-load).
- **Cross-tradition reuse.** Primary source for Layers C–F. **Diverges** from T1 on prose sufficiency (§4 B1); **fuses** with T2 on the cliff (§4.2 G.2-F1).

---

## §3 OperatorAndObjectInventory (G.2c, `FPF-Spec.md:87863`)

Candidate CHR characteristics and operator stubs for downstream authoring — **stubs only**, no legality or thresholds asserted here (that is S2's `A.19`/`C.16` work). Each of the eight characteristics maps to its backing anchor(s) and provisional polarity. These are harvested from the RCs (digest §7), not invented.

| # | Candidate characteristic (→ A.19 slot, S2) | Polarity | Backing anchor(s) | Candidate operator / band stub (→ C.16, S2) |
|---|---|---|---|---|
| 1 | instruction-adherence | higher | L15 (≈70 % advisory), L12 (68 %@500) | rate: stated-rule-violated events / session; band off the ≈70 % advisory ceiling |
| 2 | reconnaissance-depth | higher (diminishing) | L05 (6.6→2.0), L02 | ratio: reads-per-edit; target ≥3.0 vs Laurenzo 2.0 floor |
| 3 | context-integrity | target (below cliff) | L07, L08, L10, L11 | effective-fill % vs practitioner cliff; band at 50/60/75 |
| 4 | sycophancy-rate | lower | L06, L19 | rate: "modified version of what was asked" / 50 turns |
| 5 | output-economy | lower (floored) | L04 (3 % cap-reversion floor), L03 | tokens/turn, lines/stage; floor = task-necessary content |
| 6 | verification-fidelity | higher | L20, L16 | claim-without-evidence rate; terminal assertion ↔ observed event |
| 7 | attention-budget-load | lower (ceiling) | L12, L23 (509 lines) | instruction-stack lines; conflicting-pair count; ceiling vs ~150-instruction attention |
| 8 | scope-fidelity | higher | L02, L18 | edit-target overlap with named scope; out-of-lane call count |

**Candidate CAL operator families (stubs, → C.16 DHCMethod in S2):** rate-per-window (chars 1,4,6), ratio (chars 2,8), fill-percentage-vs-threshold (char 3), count-vs-ceiling (char 7), token/line economy with floor (char 5). Each becomes one `U.DHCMethod` (one characteristic, one scale, declared polarity, evidence stub) in [[12-02-measurement-frame]].

---

## §4 BridgeMatrix (G.2d, `FPF-Spec.md:87866`)

Alignment / divergence across `Tradition × Tradition` with **explicit losses**. Rows asserting fusion or substitution carry a `Γ_epist` synthesis record (§4.2, `G.2:4.5.1`, `FPF-Spec.md:87967`) — no silent fusion.

### §4.1 Alignment / divergence rows

| Bridge | Pair | Relation | Explicit loss |
|---|---|---|---|
| B1 | T1 ↔ T5 | **partial conflict** — both endorse hooks + fresh sessions; diverge on whether prose suffices. T1: behaviour promptable; T5: advisory plateaus ≈70 %, only hooks forbid. | Vendor optimism drops the degradation tail; practitioner enforcement drops the "snippets often enough" case. Reconciled by C5 (deterministic *over* advisory, not *instead of*). |
| B2 | T2 ↔ T3 | **alignment** — both: prompt ends outrank the middle. T2 recency/U-shape; T3 primacy + density. | Neither alone gives "both ends beat the middle, and density compounds it"; only the conjunction does. No fusion needed — parallel divergent claims. |
| B3 | T4 ↔ T1 | **alignment** — T4 explains *why* (RLHF over-correction), T1 documents *what* (4.7 arguing loop, 4.8 fix). | T4's gating percentages are research-setting; importing them as session rates would over-claim. Kept as mechanism, not metric. |
| B4 | T2 ↔ T5 | **fusion asserted** → see G.2-F1. Benchmark monotonic curve fused with practitioner operational thresholds into "the cliff". | Loss recorded in the Γ_epist record. |
| B5 | T3 ↔ T5 | **fusion asserted** → see G.2-F2. IFScale 68 %@500 fused with CLAUDE.md ≈70 % advisory ceiling into one "instruction-adherence ceiling". | Loss recorded in the Γ_epist record. |
| B6 | T1 ↔ T4/T5 | **alignment** — fresh-session-over-compaction (T1) ↔ Ralph loop / Trail of Bits state-in-files (T5); hook-mandatory (T4 agentic misalignment) ↔ T5 hooks. | None material; mutually reinforcing on the world plane. |

### §4.2 Γ_epist synthesis records (G.2-F, `FPF-Spec.md:87932`)

Two fusions are asserted; each binds a provenance union + explicit object-alignment ref + the residual loss. Penalties (uncertainty) stay attached to the fused claim, not laundered away.

```text
GammaEpistSynth  G.2-F1  (the operational context cliff)
  provenanceUnion:   L07 (Chroma), L08 (Lost-in-Middle), L10 (MRCR v2), L11 (practitioner 50/60/75)
  objectAlignment:   T2 "monotonic recall decay, synthetic" ⊕ T5 "operational compact-now threshold"
  fusedClaim:        agents should rotate/compact below an operational fill band (≈50–60 %),
                     well before the ~75 % autocompact, because real sessions degrade worse than MRCR.
  residualLoss:      no controlled study fixes a single % (esp. "55 %"); the band is an interpolation,
                     not a citable threshold. Marked target-is-best, not a hard SLA (spine §4.3 R2).
  governsCharacteristic: context-integrity (S2)
  refreshTrigger:    new long-context benchmark or model generation (spine §6 T1/T2)

GammaEpistSynth  G.2-F2  (the instruction-adherence ceiling)
  provenanceUnion:   L12 (IFScale 68 %@500), L15 (CLAUDE.md ≈70 % advisory), L23 (509-line stack)
  objectAlignment:   T3 "benchmark IF accuracy vs density" ⊕ T5 "CLAUDE.md prose adherence rate"
  fusedClaim:        advisory instruction adherence plateaus near ~70 % and falls as the stack grows
                     past the model's ~150-instruction attention; deterministic hooks bypass the plateau.
  residualLoss:      IFScale measures discrete benchmark instructions, not prose CLAUDE.md rules;
                     the ~70 % equivalence is an analogy across two measurement bases, not one metric.
  governsCharacteristic: instruction-adherence + attention-budget-load (S2); motivates C1, C5
  refreshTrigger:    Core/model bump; instruction-stack line-count change (spine §6 T3/T4)
```

---

## §5 MicroExamples (G.2e, `FPF-Spec.md:87870`)

Worked micro-groundings for load-bearing claims, each declaring context + `entityOfConcern` (`world` plane).

- **ME-1 (reconnaissance-depth).** Laurenzo's 6,852-session corpus [L05]: reads-per-edit fell 6.6→2.0 across generations; "when thinking is shallow, the model defaults to the cheapest action: edit without reading." Grounds A5/A7 detection — reads-per-edit is the leading indicator.
- **ME-2 (sycophancy-rate).** The arguing loop [L06]: user gives a clear instruction → pushback + caveats → "executes a modified version of what you asked" → re-argues on correction, 3–5 turns. Grounds A1; the per-50-turn "modified version" count is the detection signal.
- **ME-3 (context-integrity).** MRCR v2 [L10]: 93 %@256K → 76 %@1M on a *controlled* 8-needle test; Anthropic notes real sessions are worse. Grounds the G.2-F1 cliff and B1 (Rotate Before The Cliff) — fill-% vs band is the indicator.
- **ME-4 (verification-fidelity).** Agentic Misalignment [L20]: models "disobeyed direct commands" under pressure (blackmail 79–96 %). Grounds C5/E1 — a prompt-level "don't" is not a forbid; only an observed-event check (hook) is. Detection: claim-without-observed-event rate.

---

## §6 MethodFamilyCards (G.2j, `FPF-Spec.md:87886`)

Candidate method families — a shared signature with plural implementations, each with validity region, cost, and known failure modes. These feed the **Solution** sections of S3–S6 patterns (a pattern picks a family + implementation).

| MF | Family (signature) | Implementations | Validity region | Cost / failure mode |
|---|---|---|---|---|
| MF-1 | **Deterministic forbid** (block the action, not the intent) | PreToolUse hook exit-2; Stop/SubagentStop quality gate; permission deny | When a rule must hold 100 % (commit hygiene, secrets, scope) | Cost: maintenance + latency (<500 ms). Fails if matcher is wrong (e.g. `multiEdit` vs `MultiEdit`); over-use raises attention-budget-load. Backs C5, C7, E1, E2, F2. |
| MF-2 | **Advisory prompt** (state the rule in context) | CLAUDE.md rule; skill; system-reminder framing | Soft preferences, judgement calls, where 70 % is acceptable | Cost: tokens + attention budget. Plateaus ≈70 % [L15]; drops as stack grows [G.2-F2]. Backs A-layer framing, C3. |
| MF-3 | **Context rotation** (fresh window + file handoff) | `/clear` + progress file; Ralph loop; subagent dispatch; manual compact <60 % | Long-horizon work past the fill band [G.2-F1] | Cost: re-establish context. Fails if handoff under-specifies (B2 derailment). Backs B1, B2, D-layer. |
| MF-4 | **State externalisation** (persist outside the window) | progress spine; `[USER]`/`[DRAFT]` facts scaffold; just-in-time identifier loading [L17] | When working memory would otherwise be the model's own draft [L19] | Cost: authoring discipline. Fails if the file goes stale. Backs A6, B2, C4. |
| MF-5 | **Role decomposition** (split context across agents) | Opus-plan/Sonnet-execute; per-agent tool/scope lanes [L18] | Multi-stage pipelines; context-heavy sub-tasks | Cost: handoff fidelity, dispatch overhead. Over-spawn (4.6) / under-spawn (4.8) per generation. Backs D3, D4, model selection. |
| MF-6 | **Output shaping** (constrain emission form) | answer-budget; delta-only; `<answer>` tag; `--quiet` + JSON-on-failure | Verbosity / graphomania / toolchain flood | Cost: under-clamp risk (3 % eval drop at ≤25/≤100 [L04]). Floor at task-necessary content. Backs A2, A3, B4, D2, E5. |

---

## §7 PRISMA Flow Record (G.2h, `FPF-Spec.md:87879`)

Screening trail (notation-independent; name is historical).

- **Identified.** ~80 sources in [[../../02-external-research]] (R1–R6).
- **Inclusion criterion.** Carries a claim wired to an LAQF characteristic (§3) or pattern ([[12-00-spine]] §5), with a checkable anchor.
- **Exclusion criteria.** Duplicate coverage of an already-included claim; superseded by a later generation; no load-bearing wiring.
- **Screened → ledgered.** 24 sources entered §1 CorpusLedger as distinct load-bearing entries (L01–L24).
- **Triage outcome.** include = 19; park = 4 (L09, L14, L22 corroborating; — ); retire = 1 (L24, superseded by 4.8). `SoTA_Set` = 22.
- **Gate (`FamilyCoverageFloorK = 3`).** 5 traditions ≥ 3 → **pass**, no repair iteration needed (`G.2:4.3` step 8, `FPF-Spec.md:87938`).
- **Repairs.** none (gate passed first iteration).

---

## §8 SoTAPaletteDescription — consumable surface (`FPF-Spec.md:87896`)

The one view downstream patterns cite, so they never scrape free prose. Binds the pack ids:

```text
SoTAPaletteDescription  LAQF.sota.iter3.palette
  SoTA_Set:                {L01…L24} \ {L24} = 22 sources (§1)
  ClaimSheets:             T1, T2, T3, T4, T5 (§2)
  OperatorAndObjectInventory: 8 candidate characteristics + 6 operator-family stubs (§3)
  BridgeMatrix:            B1–B6 (§4.1) + Γ_epist G.2-F1, G.2-F2 (§4.2)
  MicroExamples:           ME-1…ME-4 (§5)
  MethodFamilyCards:       MF-1…MF-6 (§6)
  entityOfConcernMap:      every claim → ⟨agent-in-session, world plane⟩ (§0)
  handOff:
    → G.3 (CHR authoring) = [[12-02-measurement-frame]]: §3 inventory + Γ_epist polarity/band stubs
    → per-pattern §11 SoTA-Echoing (S3–S6): cite ClaimSheet + MicroExample + MethodFamily by id
    → naming/UTS: none new (LAQF ratified in spine §3; F.17 not invoked)
```

**Handoff contract.** A downstream author cites e.g. "MF-1 + ME-4 [L20]" or "characteristic 3, band per G.2-F1" — an id, never a paraphrase (`G.2:4.2` normative intent, `FPF-Spec.md:87904`).

---

## §9 Conformance & refresh (G.2 + G.11)

**G.2 conformance.** Plurality preserved (5 ClaimSheets, no premature fusion); evidence-addressable (every claim → R-ref anchor); actionable (§3 inventory + §6 families + §8 palette are id-cited handoffs); refreshable (pins below). Fusion is gated — both asserted fusions carry Γ_epist records with explicit loss (`G.2:4.3` step 6, `FPF-Spec.md:87932`).

**Required pins (for RSCR / refresh).** `SoTA_SetId = LAQF.sota.iter3`; `SoTAPaletteDescriptionId = LAQF.sota.iter3.palette`; `GammaEpistSynthId = {G.2-F1, G.2-F2}`; FamilyCoverageFloorK = 3.

**Refresh route (delegates to spine §6 G.11).** T2 *SoTA source decay* is the governing trigger — when an anchor is superseded (IFScale, MRCR v2, reads-per-edit, tokenizer, brevity-cap, the 509-line baseline), re-harvest via `G.2` and update the affected ClaimSheet + any dependent Γ_epist record. `G.2` defines what a conforming re-harvest produces; orchestration is `G.11` ([[12-00-spine]] §6 T2), not here.

## See also

- [[12-01-source-pack-ru]] — Russian twin
- [[12-00-spine]] — keystone (`sotaSynthesisPackRefs` forward-ref, §2)
- [[12-02-measurement-frame]] — consumes §3 inventory + Γ_epist stubs (S2)
- [[_inputs/rc-digest]] §8 — SoTA anchors digest
- [[../../02-external-research]] — raw corpus (R1–R6)
- [[PROGRESS]] — build ledger (§7 session DAG, §8 inventory, §9 log)
- `FPF-Spec.md:87746` G.2 · `:86968` G.0 · `:24417` A.19 · `:42826` C.16 · `:91923` G.11
