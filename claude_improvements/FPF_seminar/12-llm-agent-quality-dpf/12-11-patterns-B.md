---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, patterns, layer-b, e8-patterns]
seminar-iteration: 3
created: 2026-06-28
status: patterns-layer-b
method: FPF E.8 (authoring conventions) · 11-fpf-diagnostic D2 (Boundary quadrant) · consumes 12-01 palette LAQF.sota.iter3.palette + 12-02 detection axes
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-11-patterns-B-ru]]"
---

# LAQF — Layer B patterns (harness boundary): B1–B4

The four **Layer-B** patterns of LAQF. Each addresses a property of the Claude Code **harness** — the runtime environment around the model: long-context decay, compaction, the attention budget the system prompt and instruction stack compete for, and the absence of a platform brevity cap. In FPF terms each is a **Boundary** ([[../11-fpf-diagnostic]] D2): not a model-internal Law to mitigate (Layer A), nor user-owned config to transform directly (Layer C), but *someone else's design surface* — adapt within it now, propose upstream where the boundary itself is wrong.

These patterns reuse the house style frozen in [[12-10-patterns-A]] (the full `E.8` thirteen-section template, `FPF-Spec.md:65272`). Each cites the SoTA pack by id ([[12-01-source-pack]] §8 palette `LAQF.sota.iter3.palette`) and wires its detection slot to one `A.19` characteristic ([[12-02-measurement-frame]] §5). They assert no new evidence and re-paraphrase no source — an id, never a quote (`G.2:4.2`, `FPF-Spec.md:87904`).

## B:0 - The Layer-B boundary contract (read once, applies to B1–B4)

Stated here once so each Solution need not repeat it (`E.8:0.3` anti-repetition, `FPF-Spec.md:65234`). It is the Boundary analogue of the Layer-A mitigation contract ([[12-10-patterns-A]] A:0), governed by the [[../11-fpf-diagnostic]] D2 Boundary ruling:

- **The cause is a harness boundary, not a Law and not your config.** Each B-pattern names a Claude Code runtime property (the context-rot curve, compaction summarisation, the ~150-instruction attention window, the missing brevity governor). It is fixed *for this user* the way a Law is — but unlike a Law it is *someone's* design surface and can move upstream.
- **Two response modes: adapt now, propose upstream.** The pattern delivers the adaptation the user controls today (rotate early, externalise a handoff, ledger the budget, self-impose a cap). Where the boundary itself is the defect, it also names the upstream proposal (an Anthropic-side change) — recorded, never waited on.
- **Blocked stronger reading.** No B-pattern Solution may be read as "the harness now does this automatically." The boundary persists; the adaptation lives agent-side and (durably) in Layer-2 config. The upstream proposal is a hope, not a dependency.
- **Detection is behavioural.** Each pattern's success is observed through one of the eight `A.19` characteristics ([[12-02-measurement-frame]] §1), read at the **leading** (mid-session) indicator, not only the lagging outcome (§4 of the frame).

---

## LAQF.B1 - Rotate Before The Cliff

> **Type:** Principle pattern (P) — LAQF Layer-B
> **Status:** Build (v0.1)
> **Normativity:** Normative (boundary-adaptation; see B:0)
> **FPF kind:** Boundary (harness) — adapt; propose upstream
> **Detection characteristic:** context-integrity (`12-02` s3)
> **Source mechanism:** rc-09 (long-context soft cliff)

### LAQF.B1:0 - Use this when

Use this pattern when deciding whether to keep working in the current context window or rotate to a fresh one — as effective fill approaches the operational band, and well before the harness's own autocompact line fires.

**What goes wrong if missed.** Recall and constraint-holding decay monotonically; the practitioner cliff (~50–60% fill) precedes the ~75–80% autocompact (rc-09; L11). Working past the cliff degrades the session silently — the agent keeps producing, but on a thinning grasp of its own context.

**What this buys.** Rotation becomes a deliberate act fired at the band: a fresh window seeded by an authoritative handoff, taken *before* the cliff rather than dumped on the agent at autocompact.

**Not this pattern when.** The window is comfortably empty — rotation overhead is wasted. A4 (Effective-Fill Accounting) is the measurement sibling that *triggers* B1; B2 (Authoritative Handoff Re-Entry) governs what survives the rotation.

### LAQF.B1:1 - Problem frame

A coding agent is allowed by the harness to run all the way to the ~75% autocompact line. But recall degrades from the first token (L07, Chroma context-rot), follows a U-shaped position curve (L08), and real agentic sessions degrade *worse* than the controlled MRCR numbers (ME-3 [L10]). The harness's compact-at-75% default is therefore too late. This is a Boundary (B:0): the autocompact threshold is the platform's design choice, not the user's. The frame is to rotate on the user's schedule, not the harness's.

### LAQF.B1:2 - Problem

How can the agent rotate the context window at the operational fill band — before the degradation cliff — when the harness only forces a compaction much later, at a point where coherence has already thinned?

### LAQF.B1:3 - Forces

| Force | Tension |
|---|---|
| Rotate-early vs work-on | Coherence preserved ↔ the cost of re-establishing context. |
| Operational band vs autocompact line | ~50–60% practitioner cliff ↔ ~75% platform default. |
| Deliberate rotation vs forced compaction | A clean handoff ↔ a lossy summary dumped at the ceiling. |
| Boundary-bound | The autocompact line is the harness's; rotation is moved earlier agent-side. |

### LAQF.B1:4 - Solution

Rotate at the **operational band, not the ceiling**. Use the `MF-3` context-rotation family ([[12-01-source-pack]] §6): when effective fill (measured by A4) reaches the ~50–60% band (G.2-F1), write an authoritative handoff (B2 owns its quality) and start a fresh window — rather than working on toward the ~75% autocompact. The adaptation does not move the harness line; it makes the agent rotate before that line matters.

- **Band, not ceiling.** Trigger on the ~50–60% operational band (G.2-F1), not the ~75% autocompact (L11).
- **Handoff first.** Never rotate without an authoritative handoff doc in place (B2); a bare `/clear` loses the task.
- **Upstream proposal.** The durable fix to the boundary is a configurable/earlier compact threshold and an earlier fill warning — recorded as an Anthropic-side ask, not waited on.

*Rotate on your schedule, not the autocompact's — the clean cut beats the forced summary.*

### LAQF.B1:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A window rotated deliberately at the band carries its task forward; a window compacted by force at the ceiling carries a lossy summary.

**Show #1 (Claude Code session).** The agent is mid-refactor at ~55% effective fill and could keep going to autocompact. Under B1: it writes the progress handoff, `/clear`s, and resumes in a fresh window with full grasp — exactly the rotation this build's own `PROGRESS.md` enacts at each session boundary. Without B1: it works on to ~75%, the harness compacts, and the post-compact window has dropped two of the frozen decisions.

**Show #2 (benchmark episteme).** MRCR v2 shows recall falling 93%→76% as context grows 256K→1M on a *controlled* needle test (ME-3 [L10]); Anthropic notes real sessions are worse. The cliff is real and earlier than the hard limit — B1 keeps the agent on the safe side of it by rotating at the band.

### LAQF.B1:6 - Bias-Annotation

Lenses tested: **Arch**, **Prag**. Scope: long-horizon sessions approaching the fill band.

- **Arch bias:** treats the window as a managed resource rotated on a budget; risk is over-rotation — bounded by acting only at the band, not earlier.
- **Prag bias:** the band is an interpolation (~50–60%, [interp]), not a metered SLA; honest that the trigger is a calibration choice (G.2-F1 `residualLoss`).

### LAQF.B1:7 - Conformance Checklist

1. **CC-B1-1 (Band trigger).** Rotation fires at the ~50–60% operational band, not at the ~75% autocompact line.
2. **CC-B1-2 (Handoff present).** No rotation without an authoritative handoff doc (B2) in place.
3. **CC-B1-3 (Upstream recorded).** The boundary defect (compact-too-late) is recorded as an upstream proposal, not silently absorbed.
4. **CC-B1-4 (Detection wired).** Reads context-integrity s3: leading = effective-fill % (tokenizer-adjusted); lagging = post-compaction task-identity loss ([[12-02-measurement-frame]] §4).

### LAQF.B1:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Ride to autocompact** | the cliff precedes the ceiling (G.2-F1) | rotate at the operational band |
| **Bare `/clear`** | loses task identity (B2 derailment) | write the handoff before rotating |
| **Rotate too early on every task** | wastes re-establishment cost | trigger only at the band, via A4 |

### LAQF.B1:9 - Consequences

**Benefits.** Coherence held across long work; fewer silent slides into the degradation tail; context-integrity (s3) kept in band; the rotation is a clean cut, not a forced summary.

**Trade-offs.** Each rotation costs context re-establishment (paid to B2); the band is interpolated, not metered. Bounded by triggering only at the band and by an authoritative handoff that makes re-entry cheap.

### LAQF.B1:10 - Rationale

rc-09 is a Boundary, not a Law: the degradation is partly the model (Layer A, owned by A4's accounting) but the *compact-at-75% trigger* is the harness's. B1 owns the **action** (rotate) against that trigger; A4 owns the **measurement** that fires it; B2 owns the **handoff** that survives it. Splitting the three keeps each pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`).

### LAQF.B1:11 - SoTA-Echoing

- **Claim:** recall degrades before the hard limit and worse in real sessions. **Practice:** MRCR 93→76% (256K→1M); "real sessions worse"; practitioner cliff 50/60/75. **Source:** ME-3 [L10], L07, L08, L11, G.2-F1. **Alignment:** B1 rotates at the band the fused evidence marks, not at the ceiling. **Status:** adapt (band is [interp], not an SLA).
- **Claim:** a fresh window beats a compacted one. **Practice:** vendor + practitioner agreement that fresh sessions outperform compaction; rotation via `/clear` + file handoff. **Source:** L01, L17, MF-3. **Alignment:** B1's deliberate rotation is exactly the fresh-over-compacted move. **Status:** adopt.

### LAQF.B1:12 - Relations

- **Boundary (B:0):** harness autocompact threshold via [[../11-fpf-diagnostic]] D2 — adapt by rotating earlier; MUST NOT read as the harness rotating for you.
- **Measurement (R2):** context-integrity s3 ([[12-02-measurement-frame]] §2 card `laqf.mm.s3`); band per Γ_epist G.2-F1.
- **Method family:** `MF-3` (context rotation).
- **Coordinates with:** A4 (measures the fill that triggers B1); B2 (the handoff that survives the rotation); B3 (a rotated window also resets the attention load); D1/D3 (pipeline-scale re-entry).

### LAQF.B1:End

---

## LAQF.B2 - Authoritative Handoff Re-Entry

> **Type:** Principle pattern (P) — LAQF Layer-B
> **Status:** Build (v0.1)
> **Normativity:** Normative (boundary-adaptation; see B:0)
> **FPF kind:** Boundary (harness) — adapt; propose upstream
> **Detection characteristic:** context-integrity (`12-02` s3)
> **Source mechanism:** rc-10 (compaction derailment)

### LAQF.B2:0 - Use this when

Use this when a window is about to rotate or compact, or a fresh session is starting from a prior one, and the new window must resume with task identity, frozen decisions, and where-we-stopped intact — rather than restarting the work.

**What goes wrong if missed.** Post-compaction the agent loses task identity: it restarts work already done, drops constraints it was holding, or re-litigates frozen decisions (rc-10; S-001/013). The harness's own compaction summary is exactly where this identity is lost.

**What this buys.** A single authoritative handoff artefact re-establishes the task on re-entry, so the fresh window *resumes* — reads where it stopped and continues — instead of guessing from a lossy summary.

**Not this pattern when.** A short single-window task with no rotation. B1 decides *when* to rotate; B2 governs *what must survive* it.

### LAQF.B2:1 - Problem frame

When the harness compacts (or the user `/clear`s), it replaces the live context with a summary. That summary is lossy precisely on task identity: the model "remembers" it was doing something but not the constraints, the decisions, or the exact resume point. Vendor and practitioner evidence both say a fresh session seeded from files beats a compacted one (L01, L17). This is a Boundary (B:0): the compaction is the harness's, and its fidelity cannot be trusted. The frame is to externalise an authoritative handoff the fresh window reads first.

### LAQF.B2:2 - Problem

How can a fresh or post-compaction window resume the task with full identity — constraints, decisions, resume point — when the harness's compaction summary drops exactly that information?

### LAQF.B2:3 - Forces

| Force | Tension |
|---|---|
| Authoritative doc vs harness summary | A maintained handoff ↔ the lossy autocompact digest. |
| Externalise vs trust memory | A file outside the window ↔ the compacted echo (links A6). |
| Completeness vs brevity | Enough to resume ↔ short enough to read first (links B4). |
| Boundary-bound | The harness compaction is fixed; an external handoff is added beside it. |

### LAQF.B2:4 - Solution

Externalise an **authoritative handoff** the fresh window reads *first*. Use `MF-4` (state externalisation) over `MF-3` (rotation): a single durable file carrying restated task, frozen decisions, where-we-stopped, and the explicit next start point — the source of truth on re-entry, overriding the compaction summary. Facts in it are origin-anchored (A6), so the new window cites the doc, not a drifted echo. This build's `PROGRESS.md` is the working exemplar: §0 "how to resume", §2 frozen decisions, §8 state ledger, §9 next start point.

- **One authoritative doc.** A maintained handoff file, not the harness summary, is the source of truth on re-entry.
- **Read it first.** The re-entry protocol is "read the handoff before doing anything" (PROGRESS.md §0).
- **Resume point explicit.** The doc names the next start point, so the fresh window continues rather than re-derives.

*Hand off in writing; the next window should read, not reconstruct.*

### LAQF.B2:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A window that re-reads an authoritative handoff resumes; a window that trusts the compaction summary restarts.

**Show #1 (Claude Code session).** This very build: `/clear` fires, the fresh window reads `PROGRESS.md` §0→§9, finds "next start point: S4", the frozen decisions, and the file ledger — and resumes S4 without re-deriving the scope. Without B2: the post-compact window sees "we were building some patterns", picks a plausible-but-wrong file, and re-litigates settled decisions.

**Show #2 (clinical-handover episteme).** ICU shift handover runs on the chart and a structured SBAR note, not the outgoing nurse's memory; the incoming nurse reads the record and continues care. B2 imports the handover discipline: the record carries identity across the shift change, which L17 calls "structured note-taking that persists state outside the window".

### LAQF.B2:6 - Bias-Annotation

Lenses tested: **Arch**, **Gov**. Scope: rotation / re-entry boundaries.

- **Arch bias:** favours an explicit external artefact over implicit recall; risk is doc staleness — bounded by updating it at the rotation moment (MF-4 failure mode).
- **Gov bias:** the handoff is an accountability record (what was decided, where we stopped); shared discipline with D1/D3 pipeline re-entry.

### LAQF.B2:7 - Conformance Checklist

1. **CC-B2-1 (Authoritative doc).** A maintained handoff file — not the harness summary — is the source of truth on re-entry.
2. **CC-B2-2 (Read-first protocol).** The re-entry sequence reads the handoff before acting.
3. **CC-B2-3 (Resume point).** The doc names an explicit next start point and the frozen decisions.
4. **CC-B2-4 (Detection wired).** Reads context-integrity s3: leading = effective-fill % approaching the band (rotation imminent); lagging = post-compaction task-identity / constraint drop.

### LAQF.B2:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Trust the autocompact summary** | identity is exactly what it drops (rc-10) | maintain an authoritative handoff doc |
| **Stale handoff** | the doc lies about the resume point | update it at the rotation moment (MF-4) |
| **Handoff too long to read** | the fresh window skims and re-derives | keep it short + current (links B4, C1) |

### LAQF.B2:9 - Consequences

**Benefits.** Post-compaction restarts and constraint drops fall; long work survives rotation; context-integrity (s3) preserved across the boundary; the resume cost B1 incurs is paid cheaply.

**Trade-offs.** Maintaining the handoff is authoring overhead, and a stale doc is worse than none; bounded by updating it at rotation and keeping it short. Re-supplies the anchors A6 needs after compaction.

### LAQF.B2:10 - Rationale

rc-10 is the re-entry face of the context Boundary: B1 acts on *when* to rotate, B2 on *what survives*. Externalising the handoff is the `MF-4` move that A6 (anchor facts) and C4 (the tagged-facts scaffold) build on; making the doc authoritative — overriding the harness summary — is what converts a rotation from a restart into a resume.

### LAQF.B2:11 - SoTA-Echoing

- **Claim:** a fresh session seeded from files beats compaction. **Practice:** vendor guidance that state is discoverable from the filesystem; fresh-session-over-compaction. **Source:** L01 (T1). **Alignment:** B2's authoritative handoff is the seed that makes the fresh session win. **Status:** adopt.
- **Claim:** state belongs outside the window. **Practice:** structured note-taking / just-in-time identifier loading persists state. **Source:** L17 (effective context engineering); MF-4. **Alignment:** the handoff doc is exactly externalised state, read first on re-entry. **Status:** adopt.

### LAQF.B2:12 - Relations

- **Boundary (B:0):** harness compaction fidelity via [[../11-fpf-diagnostic]] D2 — adapt with an external handoff; MUST NOT read as the harness preserving identity for you.
- **Measurement (R2):** context-integrity s3 ([[12-02-measurement-frame]] §2 card `laqf.mm.s3`).
- **Method family:** `MF-4` (state externalisation) over `MF-3` (rotation).
- **Coordinates with:** B1 (decides when to rotate; B2 supplies what survives); A6 (origin-anchored facts the handoff carries); A4 (the fill trigger); D1/D3 (re-entry at workflow scale).

### LAQF.B2:End

---

## LAQF.B3 - Attention-Budget Ledger

> **Type:** Principle pattern (P) — LAQF Layer-B
> **Status:** Build (v0.1)
> **Normativity:** Normative (boundary-adaptation; see B:0)
> **FPF kind:** Boundary (harness) — adapt; propose upstream
> **Detection characteristic:** attention-budget-load (`12-02` s7)
> **Source mechanism:** rc-11 (CLAUDE.md attention budget)

### LAQF.B3:0 - Use this when

Use this when assessing whether the active instruction stack — system prompt + the CLAUDE.md layers + always-on skills — fits within the model's effective attention, before relying on any one rule to actually hold.

**What goes wrong if missed.** The model attends roughly 150 instructions effectively; the system prompt already consumes ~50; a 509-line user stack overflows that budget and rules are silently dropped (rc-11; L12, L23, G.2-F2). The agent appears to ignore a CLAUDE.md rule it never had attention left to read.

**What this buys.** An explicit ledger of what occupies the attention budget — stack lines, conflicting pairs, always-on-skill token ratio — so the user knows which rules are load-bearing versus over the cliff and at risk of silent drop.

**Not this pattern when.** The stack is comfortably under budget. B3 is the *accounting* (boundary-side); C1 (Instruction-Stack Within Budget) is the *design action* that trims, and C2 (Single-Owner Rule Resolution) clears the conflicts the ledger surfaces.

### LAQF.B3:1 - Problem frame

Every turn, the harness loads the system prompt plus the full CLAUDE.md stack (UAP + project + workspace) and any always-on skills. The model follows instructions with a bias toward the earliest and attends only a bounded number well (IFScale: 68% at 500 instructions, earlier-instruction bias, L12). Past ~150 effective instructions, rules later in the stack are at drop risk (G.2-F2). This is a Boundary (B:0): the harness offers no attention meter and no per-rule priority. The frame is to keep the ledger the harness does not.

### LAQF.B3:2 - Problem

How can the user know which instructions are actually within the model's effective attention — and which are over the cliff and silently dropping — when the harness loads the whole stack every turn but surfaces no budget?

### LAQF.B3:3 - Forces

| Force | Tension |
|---|---|
| Coverage vs attention | More rules stated ↔ each extra rule dilutes the budget. |
| Visible stack vs effective attention | 509 displayed lines ↔ ~150 effectively attended. |
| Ledger cost vs payoff | Tracking the budget ↔ only matters as the stack grows. |
| Boundary-bound | The harness gives no meter; the ledger is kept agent/user-side. |

### LAQF.B3:4 - Solution

Keep an **attention-budget ledger**. Count the live load — instruction-stack lines, conflicting-rule pairs, always-on-skill token ratio — and compare against the ~150-instruction effective attention (G.2-F2), not the raw file size. This is the s7 analogue of A4's s3 context accounting: B3 owns the *measurement*; the *actions* are C1 (trim) and C2 (resolve). The adaptation cannot raise the model's attention ceiling; it stops the overflow from being invisible.

- **Ledger the load.** Track stack lines + conflict pairs + always-on token ratio.
- **Budget, not file size.** Compare against the ~150 effective-attention ceiling (G.2-F2), not the displayed line count.
- **Hand off to C1 / C2.** When the ledger shows overflow, trimming is C1's job and conflict-clearing is C2's; B3's output is the signal.
- **Upstream proposal.** The durable fix is harness-surfaced rule priority / an attention meter — recorded as an Anthropic-side ask.

*Count what the model can actually attend to — the stack is longer than the budget.*

### LAQF.B3:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** Effective attention is the budget, not the file length; ledger against the budget.

**Show #1 (Claude Code session).** The stack measures 509 lines (UAP 216 + devbox-setup 196 + workspace 97, L23). Under B3 the ledger flags it at ~3.4× the ~150 effective-attention ceiling, marks the rules below line ~150 as drop-risk, and counts the known conflict pairs — handing C1 a concrete trim target. Without B3: the user adds a 510th rule and wonders why an earlier one stopped firing.

**Show #2 (cognitive-load episteme).** Working memory holds ~7±2 items; a checklist longer than capacity is not executed in full — items past the limit are skipped silently. The instruction stack past the attention budget behaves the same way; B3 is the inventory that keeps the list inside capacity.

### LAQF.B3:6 - Bias-Annotation

Lenses tested: **Arch**, **Gov**. Scope: instruction-stack sizing.

- **Arch bias:** treats attention as a budgeted resource with a ceiling; risk is over-conservatism (trimming useful rules) — bounded by handing the decision to C1, not cutting blindly.
- **Gov bias:** the ledger is an accountability artefact (which rules are load-bearing, which are at risk); the conflict-pair count is auditable (shared with C2).

### LAQF.B3:7 - Conformance Checklist

1. **CC-B3-1 (Ledger kept).** Stack lines, conflict pairs, and always-on token ratio are tracked.
2. **CC-B3-2 (Budget comparison).** The comparison point is the ~150 effective-attention ceiling, not the raw line count.
3. **CC-B3-3 (Hand-off).** Overflow triggers C1 (trim) / C2 (resolve) rather than being absorbed.
4. **CC-B3-4 (Detection wired).** Reads attention-budget-load s7: leading = instruction-stack line count + conflict-pair register; lagging = adherence drift as the stack grows (G.2-F2 plateau).

### LAQF.B3:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **File-length optimism** | 509 displayed ≠ 150 attended (L12) | ledger against the effective-attention budget |
| **Add-another-rule** | each rule dilutes the budget, drops an older one | check the ledger before adding; trim first (C1) |
| **Ignore conflicts** | each conflicting pair is an attention tax (G.2-F2) | count them; resolve via C2 |

### LAQF.B3:9 - Consequences

**Benefits.** The user sees which rules are load-bearing and which are at drop risk; adherence drift gets a measurable cause; context-integrity and instruction-adherence both benefit downstream; C1/C2 get concrete targets.

**Trade-offs.** Maintaining the ledger is overhead, and the ~150 ceiling is an interpolation, not a metered value; bounded by tracking only as the stack grows and delegating the cut to C1.

### LAQF.B3:10 - Rationale

rc-11 is the attention twin of rc-04: where A4 accounts for *context* fill (s3), B3 accounts for *attention* load (s7). Both are accounting patterns that own a measurement and delegate the action — A4 to B1, B3 to C1/C2. Keeping B3 as the boundary-side meter (the harness offers none) separates it cleanly from the design-side trim (C1), preserving each pattern's single `EntityOfConcern` (`E.8:0.3`).

### LAQF.B3:11 - SoTA-Echoing

- **Claim:** instruction adherence falls with density and biases toward earlier instructions. **Practice:** IFScale 68% IF accuracy at 500 instructions; LIFBench quantifies "rule silently dropped". **Source:** L12, L13 (T3); G.2-F2. **Alignment:** B3's ledger reads exactly this load against the ~150 effective ceiling. **Status:** adopt.
- **Claim:** the local instruction stack is 509 lines. **Practice:** measured UAP 216 + devbox-setup 196 + workspace 97. **Source:** L23 (T5). **Alignment:** B3 uses this as the baseline the ledger tracks. **Status:** adopt.

### LAQF.B3:12 - Relations

- **Boundary (B:0):** the harness attention budget via [[../11-fpf-diagnostic]] D2 — adapt by ledgering; MUST NOT read as the harness prioritising rules for you.
- **Measurement (R2):** attention-budget-load s7 ([[12-02-measurement-frame]] §2 card `laqf.mm.s7`); ceiling per Γ_epist G.2-F2.
- **Method family:** accounting pattern (the s7 analogue of A4); feeds the `MF-1`/`MF-2` choice at C5.
- **Coordinates with:** C1 (trims the overflow B3 measures); C2 (resolves the conflict pairs B3 counts); A4 (the context-budget twin); B1 (rotation resets the load).

### LAQF.B3:End

---

## LAQF.B4 - Self-Imposed Output Budget

> **Type:** Principle pattern (P) — LAQF Layer-B
> **Status:** Build (v0.1)
> **Normativity:** Normative (boundary-adaptation; see B:0)
> **FPF kind:** Boundary (harness) — adapt; no viable upstream
> **Detection characteristic:** output-economy (`12-02` s5)
> **Source mechanism:** rc-12 (no platform brevity cap)

### LAQF.B4:0 - Use this when

Use this when composing any turn or pipeline stage, given that the platform enforces no turn-level brevity cap — the agent either imposes its own budget or defaults to over-production.

**What goes wrong if missed.** There is no harness brevity governor. Anthropic tried hard caps (≤25 / ≤100 words) and reverted them after a 3% eval drop (rc-12; L04), so neither a floor nor a ceiling exists at the platform. Left unbudgeted, output bloats toward the model's verbosity gradient (the Layer-A A2/A3 Laws).

**What this buys.** The agent supplies the missing governor from its own side: a soft per-turn/per-stage budget proportional to the task, held above the L04 floor — the brevity control the platform declines to enforce.

**Not this pattern when.** The task genuinely needs depth (a design rationale, a multi-step proof). B4 budgets *unwarranted* length, not warranted detail — the L04 floor still binds.

### LAQF.B4:1 - Problem frame

The Layer-A Laws A2 (whole-artefact gradient) and A3 (complexity→length calibration) push output up; the natural counterweight would be a platform brevity cap. But the platform has *no* such governor: the one experiment with hard caps cost 3% on evals and was reverted (L04). This is a Boundary (B:0): there will be no platform brevity enforcement, and the evidence says re-imposing a hard cap is the wrong move. The frame is to self-impose a soft budget that does not repeat the over-clamp mistake.

### LAQF.B4:2 - Problem

How can the agent supply the turn-level brevity control the platform refuses to enforce — a budget that curbs bloat without re-introducing the over-clamp that cost 3% on evals?

### LAQF.B4:3 - Forces

| Force | Tension |
|---|---|
| Self-budget vs no governor | The agent caps itself ↔ the platform caps nothing. |
| Floor vs over-clamp | Curb bloat ↔ never re-impose the ≤25/≤100 mistake (L04). |
| Soft budget vs hard cap | Proportional to the task ↔ a fixed word limit that drops content. |
| Boundary-bound | The platform will not cap; the budget is self-imposed. |

### LAQF.B4:4 - Solution

Self-impose a **soft output budget** the platform will not. Use the `MF-6` output-shaping family ([[12-01-source-pack]] §6) from the harness-boundary angle: set a per-turn / per-stage budget proportional to the task, and hold it above the L04 floor — never re-introduce a hard ≤25/≤100-word cap. Where A2 (delta) and A3 (answer-first) mitigate the *model's* gradient, B4 supplies the *platform's* missing brevity governor, the same `MF-6` family applied at the boundary. There is no viable upstream proposal here — the platform-cap path is closed by the L04 evidence.

- **Self-impose the governor.** A soft per-turn/per-stage budget; the platform supplies none.
- **Floor (L04).** Never clamp below task-necessary content — the ≤25/≤100 reversion is the standing warning.
- **Soft, not hard.** Budget proportional to the task, not a fixed word limit that silently drops content.

*Be your own editor — the platform will not cut for you, and a hard cap cuts too much.*

### LAQF.B4:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** With no platform governor, brevity is a self-imposed discipline — a budget, not a hard limit.

**Show #1 (Claude Code session).** A pipeline stage is about to emit a giant Markdown document plus a JSON shadow of the same content. Under B4: the stage holds a per-stage budget — one artefact, sized to what the next stage needs — and stays above the floor. Without B4: nothing caps it, the verbosity gradient wins, and the stage floods the next window (links D2, E5).

**Show #2 (editorial episteme).** A word count is a writer's self-imposed discipline, not an externally enforced gate; a good editor budgets the piece and cuts padding, but never pads up to a minimum. B4 imports editorial budgeting against a platform that ships no word count at all — and against the L04 lesson that a blunt minimum/maximum hurts quality.

### LAQF.B4:6 - Bias-Annotation

Lenses tested: **Prag**, **Did**. Scope: turn / stage composition.

- **Prag bias:** optimises reader and downstream-window cost; risk is under-clamping a turn that needed depth — bounded by the L04 floor.
- **Did bias:** "set a soft budget, honour the floor" is a single teachable move; the floor is the part most often forgotten, so it is stated explicitly.

### LAQF.B4:7 - Conformance Checklist

1. **CC-B4-1 (Self-budget set).** A soft per-turn/per-stage budget is set, proportional to the task.
2. **CC-B4-2 (No hard cap).** No fixed ≤N-word cap is imposed (the L04 reversion).
3. **CC-B4-3 (Floor honoured).** The budget never clamps below task-necessary content.
4. **CC-B4-4 (Detection wired).** Reads output-economy s5: leading = tokens/turn, lines/stage tally; lagging = reader-reported graphomania *or* under-delivery.

### LAQF.B4:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **No budget at all** | the verbosity gradient (A2/A3) wins unchecked | self-impose a soft per-turn budget |
| **Re-impose a hard cap** | repeats the L04 3% eval drop | budget proportionally; honour the floor |
| **Pad to a minimum** | over-clamp on the *other* side | size to the answer, never inflate |

### LAQF.B4:9 - Consequences

**Benefits.** Turns and stages stay sized to the task; the verbosity Laws get a counterweight the platform never supplies; output-economy (s5) improves without losing fidelity; downstream windows stay clean (links D2, E5).

**Trade-offs.** A self-imposed budget can mis-size and under-serve a deep turn; bounded by the L04 floor and by treating depth as available-on-demand. No upstream relief is coming — the platform-cap path is closed.

### LAQF.B4:10 - Rationale

rc-12 is the boundary counterpart of the Layer-A verbosity Laws: A2/A3 mitigate the model's gradient, B4 supplies the platform's missing governor. All three read s5, but B4 is the layer where the *absence of platform enforcement* is the cause — which is why its Solution is "self-impose" rather than "mitigate" or "configure", and why, uniquely among the B-patterns, it records no viable upstream proposal.

### LAQF.B4:11 - SoTA-Echoing

- **Claim:** hard brevity caps over-clamp and cost accuracy. **Practice:** Anthropic reverted ≤25/≤100-word caps after a 3% eval drop. **Source:** L04 (Apr-23 postmortem), MF-6. **Alignment:** B4 self-budgets proportionally rather than imposing a hard cap, staying above the L04 floor. **Status:** adapt (floor, not cap; no upstream cap worth proposing).
- **Claim:** tokenizer densification shrinks effective budget. **Practice:** ~30% denser per same English at 4.7+. **Source:** L03. **Alignment:** every unbudgeted paragraph costs ~30% more than it appears (links A4). **Status:** adopt (as cost pressure on the budget).

### LAQF.B4:12 - Relations

- **Boundary (B:0):** the platform's absent brevity governor via [[../11-fpf-diagnostic]] D2 — adapt by self-imposing; MUST NOT read as the platform enforcing brevity. No viable upstream (L04 closes the cap path).
- **Measurement (R2):** output-economy s5 ([[12-02-measurement-frame]] §2 card `laqf.mm.s5`).
- **Method family:** `MF-6` (output shaping), from the harness-boundary angle.
- **Coordinates with:** A2 / A3 (the Law-side s5 siblings B4 counterweights); D2 (Atomic Single-Form Emission — the pipeline-scale analogue); E5 (Quiet Toolchain Output — the toolchain-side s5 sibling).

### LAQF.B4:End

---

## See also

- [[12-11-patterns-B-ru]] — Russian twin
- [[12-10-patterns-A]] — frozen house-style exemplar (A:0 contract; the 13-section template B1–B4 reuse)
- [[12-00-spine]] — keystone: §5 roster (Boundary kind + detection), §4.3 relation records, §4.1 edition direction
- [[12-01-source-pack]] — G.2 pack; §8 palette `LAQF.sota.iter3.palette` cited by every §11 (L-/ME-/MF-/Γ_epist ids)
- [[12-02-measurement-frame]] — detection axes (§5 pattern↔characteristic; §2 DHCMethod cards; §3 CAL bands; §4 leading/lagging)
- [[_inputs/rc-digest]] — §2 Layer-B mechanisms (rc-09…rc-12)
- [[../11-fpf-diagnostic]] — D2 Boundary ruling (the basis for the B:0 boundary contract)
- `FPF-Spec.md:65183` E.8 authoring conventions · `:65272` canonical template · `:24417` A.19 · `:42826` C.16 · `:87746` G.2
