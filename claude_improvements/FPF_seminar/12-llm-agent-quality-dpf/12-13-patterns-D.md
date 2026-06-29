---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, patterns, layer-d, e8-patterns]
seminar-iteration: 3
created: 2026-06-28
status: patterns-layer-d
method: FPF E.8 (authoring conventions) · 11-fpf-diagnostic D2 (Design-space / Work quadrant) · consumes 12-01 palette LAQF.sota.iter3.palette + 12-02 detection axes
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-13-patterns-D-ru]]"
---

# LAQF — Layer D patterns (workflow topology): D1–D4

The four **Layer-D** patterns of LAQF. Each addresses a property of the multi-stage *pipeline* the user runs agents through — the shape of the workflow itself: how phases hand off, how each stage emits, how dispatch is scheduled, how roles are bounded. In FPF terms each is a **Design** cause ([[../11-fpf-diagnostic]] D2 design-space): not a model-internal Law to mitigate (Layer A), nor someone else's harness boundary to adapt around (Layer B), but *the user's own pipeline topology* — transformable outright by direct Work.

These patterns reuse the house style frozen in [[12-10-patterns-A]] (the full `E.8` thirteen-section template, `FPF-Spec.md:65272`). Each cites the SoTA pack by id ([[12-01-source-pack]] §8 palette `LAQF.sota.iter3.palette`) and wires its detection slot to one `A.19` characteristic ([[12-02-measurement-frame]] §5). They assert no new evidence and re-paraphrase no source — an id, never a quote (`G.2:4.2`, `FPF-Spec.md:87904`).

## D:0 - The Layer-D design contract (read once, applies to D1–D4)

Stated here once so each Solution need not repeat it (`E.8:0.3` anti-repetition, `FPF-Spec.md:65234`). Layer D shares the Design quadrant with Layer C, so this contract **inherits the Layer-C design contract** ([[12-12-patterns-C]] C:0) rather than restating it, specialising it to workflow topology under the same [[../11-fpf-diagnostic]] D2 design-space ruling (D–F are all Design / direct-Work):

- **The cause is the user-owned pipeline — neither a Law nor a harness boundary.** Each D-pattern names something about the *shape* of the workflow (a phase boundary, a stage's emission, the dispatch schedule, a role's lane). Like Layer C, this surface is the user's to rewrite; unlike Layer C it is the *topology* between agents, not the config inside one.
- **Direct Work, no hedge** (inherited from C:0). A D-pattern's Solution *transforms* the topology: it adds the re-entry gate, collapses the duplicate emission, anchors dispatch to a roadmap, fences each role. There is no "mitigate-only" caveat — the pipeline can be made to hold.
- **Layer-1 states *what*; Layer-2 (S6) realises *how*** (inherited from C:0). This Domain edition states the property the workflow must satisfy; the Local Practice edition (the user's actual commands, agents, progress spine, hooks) is the realisation.
- **Prefer deterministic over advisory where a rule must hold** (inherited from C:0 → C5). A role lane that *must* hold (D4) belongs in a per-agent hook (`MF-1`), not in an agent prompt (`MF-2`); a workflow preference that is judgement stays advisory. C5 owns the classification; D-patterns inherit the preference and point to C5.
- **Detection is behavioural.** Each pattern's success is observed through one of the eight `A.19` characteristics ([[12-02-measurement-frame]] §1), read at the **leading** (mid-session) indicator, not only the lagging outcome (§4 of the frame). Layer D reads mostly scope-fidelity (s8) and output-economy (s5).

---

## LAQF.D1 - Re-Entry Across Phase Boundary

> **Type:** Principle pattern (P) — LAQF Layer-D
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see D:0)
> **FPF kind:** Design (workflow topology) — transform via Work (direct)
> **Detection characteristic:** scope-fidelity (`12-02` s8)
> **Source mechanism:** rc-20 (waterfall pipeline, no re-entry)

### LAQF.D1:0 - Use this when

Use this when a multi-stage pipeline runs spec → domain → plan → code in one forward pass, and a later stage (a proof-of-concept, a spike, the first real Read of the codebase) surfaces evidence that an earlier stage's assumption was wrong — and you must decide whether the pipeline can return to that stage or only ploughs forward.

**What goes wrong if missed.** The waterfall has no re-entry point: a POC invalidates a spec assumption, but the plan is already frozen and code proceeds on the falsified premise (rc-20; S-032, S-036). The downstream artefacts are internally consistent and externally wrong, and the divergence is discovered only at the end.

**What this buys.** A pipeline whose phase boundaries are re-entrant: when later evidence falsifies an earlier assumption, control returns to that phase and the dependent work is re-derived, not patched over. The plan is a revisited hypothesis, not a contract signed before the evidence existed.

**Not this pattern when.** The phases are genuinely independent and no later stage produces evidence about an earlier one. D1 is the *re-entry gate*; D3 (Roadmap-Anchored Dispatch) is the schedule the gate updates, and B2 (Authoritative Handoff Re-Entry) is the boundary-side re-establishment of identity after a context break — different cause.

### LAQF.D1:1 - Problem frame

The pipeline is laid out as a waterfall because each stage's output is the next stage's input, and that suggests a single forward pass. But the cheapest source of truth — actually building a slice — arrives *after* spec and plan, and routinely contradicts them. Vendor and practitioner guidance both put a human-gated loop between planning and execution precisely so the plan can be revised (L16). Without a re-entry boundary the pipeline cannot act on its own best evidence; it commits to assumptions it has already disproven. This is a Design cause (D:0): the topology is the user's to rewrite. The frame is to make each phase boundary re-entrant.

### LAQF.D1:2 - Problem

How can a multi-stage pipeline return to an earlier phase when a later phase produces evidence that falsifies that phase's assumption — so the workflow acts on its best evidence rather than on a premise frozen before the evidence existed?

### LAQF.D1:3 - Forces

| Force | Tension |
|---|---|
| Forward momentum vs correctness | A single forward pass feels like progress ↔ proceeding on a falsified premise. |
| Frozen plan vs revised plan | A signed contract is stable ↔ a hypothesis revised by evidence (L16). |
| Re-entry cost vs rework cost | Returning to an earlier phase ↔ discovering the divergence at the end. |
| Design-able | The pipeline topology is the user's; the boundary is made re-entrant, not adapted-around. |

### LAQF.D1:4 - Solution

Make each phase boundary **re-entrant against its own assumptions**. At the spec→domain, domain→plan, and plan→code boundaries, record the assumptions the downstream phase depends on; when a later phase produces evidence that falsifies one, return to the owning phase and re-derive the dependent work rather than patching forward. Treat the plan as a hypothesis re-tested after each POC (the Plan↔Execute human gate, L16), not a frozen artefact. This is the `MF-3` family ([[12-01-source-pack]] §6) applied to the pipeline: a controlled return, with the falsified assumption as the trigger. D3 supplies the roadmap the re-entry updates; D4 keeps the re-derivation inside role lanes. The transformation is direct: the topology gains the return edge a waterfall lacks.

- **Record the load-bearing assumptions.** Each phase boundary names what the downstream phase depends on from the upstream one.
- **Falsification triggers return.** Evidence contradicting a recorded assumption returns control to the owning phase, not a forward patch.
- **Plan is a hypothesis.** The plan is re-tested after each POC against the Plan↔Execute gate (L16), not signed once.

*Build the return edge a waterfall lacks: when a slice falsifies the plan, go back to the plan — do not code over it.*

### LAQF.D1:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A pipeline that can return to an earlier phase acts on its best evidence; a one-pass waterfall commits to assumptions it has already disproven.

**Show #1 (Claude Code session).** A spec assumes a third-party API supports batch writes; the plan and the agent dispatch are built on it. The first POC Read shows the API is single-write only. Under D1: the plan→code boundary detects the falsified assumption, returns to the plan phase, and the dependent design is re-derived for single-write before any production code is written. Without D1: the plan stays frozen, code is written against a batch API that does not exist, and the contradiction surfaces at integration (S-032).

**Show #2 (software-process episteme).** Boehm's spiral model replaced the waterfall precisely because each loop re-evaluates risk and revisits requirements against a built increment; a control loop with feedback is stable where an open loop drifts. D1 imports that feedback edge into the agent pipeline — the POC is the increment, the falsified assumption is the risk signal — and L16's Plan↔Execute gate is the human-checked return path.

### LAQF.D1:6 - Bias-Annotation

Lenses tested: **Arch**, **Tmp**. Scope: cross-phase pipeline topology.

- **Arch bias:** treats the pipeline as a graph that needs return edges, not only forward ones; risk is thrashing (re-entering on every minor surprise) — bounded by triggering return only on a *recorded load-bearing* assumption being falsified, not any new fact.
- **Tmp bias:** attends the ordering of evidence over time (the cheapest truth arrives late); risk is deferring all commitment — bounded by re-deriving only the dependent work, not restarting the pipeline.

### LAQF.D1:7 - Conformance Checklist

1. **CC-D1-1 (Assumptions recorded).** Each phase boundary names the upstream assumptions the downstream phase depends on.
2. **CC-D1-2 (Return on falsification).** Evidence falsifying a recorded assumption returns control to the owning phase; the dependent work is re-derived.
3. **CC-D1-3 (Plan as hypothesis).** The plan is re-tested after each POC against the Plan↔Execute gate (L16), not frozen on first signature.
4. **CC-D1-4 (Detection wired).** Reads scope-fidelity s8: leading = downstream edit proceeding on an assumption a POC has already falsified; lagging = end-of-pipeline divergence / rework (re-entry events, §7 char 8).

### LAQF.D1:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Freeze the plan after sign-off** | a later POC cannot correct it | treat the plan as a hypothesis re-tested per POC (L16) |
| **Patch forward over a falsified premise** | downstream stays internally consistent, externally wrong | return to the owning phase; re-derive the dependent work |
| **Re-enter on every minor surprise** | pipeline thrashes, never converges | trigger return only on a recorded load-bearing assumption |

### LAQF.D1:9 - Consequences

**Benefits.** The pipeline acts on its best evidence; falsified assumptions are corrected at the owning phase, not patched downstream; scope-fidelity (s8) holds because edits track the validated, not the frozen, scope; divergence is caught at the boundary instead of at integration.

**Trade-offs.** Recording assumptions and supporting return edges is topology overhead, and over-eager re-entry can thrash; bounded by triggering only on recorded load-bearing assumptions and re-deriving only the dependent work.

### LAQF.D1:10 - Rationale

rc-20 is a topology defect, not a model defect: the waterfall is an *open* control loop, and the agent's best evidence (a built slice) arrives after the phases that should consume it. The repair is a graph edge, not a prompt — which is why D1 is Design (D:0) and direct. Keeping the re-entry trigger tied to a *recorded* assumption keeps the pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) and distinguishes it from B2, which re-establishes identity after a *context* break rather than an *evidence* break.

### LAQF.D1:11 - SoTA-Echoing

- **Claim:** a human-checked gate between planning and execution lets the plan be revised against built evidence. **Practice:** Plan Mode as a harness-enforced approval gate; Explore→Plan→Execute with a Plan↔Execute gate. **Source:** L16 (T1+T5). **Alignment:** D1 makes that gate re-entrant on falsified assumptions, not one-directional. **Status:** adopt.
- **Claim:** subagent dispatch preserves context across stages but not correctness of the upstream premise. **Practice:** Opus-lead/Sonnet-subagent decomposition; subagents preserve context, not intelligence. **Source:** L18 (T1+T5). **Alignment:** D1 supplies the correctness edge the decomposition lacks — return when the premise is falsified. **Status:** adapt (dispatch is D3; D1 is the return edge).

### LAQF.D1:12 - Relations

- **Design cause (D:0):** the waterfall topology via [[../11-fpf-diagnostic]] D2 — transformed by adding re-entry edges; MUST NOT read as "any new fact restarts the pipeline".
- **Measurement (R2):** scope-fidelity s8 ([[12-02-measurement-frame]] §2 card `laqf.mm.s8`; re-entry-event component, §7 char 8).
- **Method family:** `MF-3` (context rotation / controlled return) applied at the phase boundary.
- **Coordinates with:** D3 (the roadmap the re-entry updates); D4 (keeps re-derivation in role lanes); B2 (the boundary-side re-entry after a *context* break, not an evidence break).

### LAQF.D1:End

---

## LAQF.D2 - Atomic Single-Form Emission

> **Type:** Principle pattern (P) — LAQF Layer-D
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see D:0)
> **FPF kind:** Design (workflow topology) — transform via Work (direct)
> **Detection characteristic:** output-economy (`12-02` s5)
> **Source mechanism:** rc-21 (monolithic + duplicate stage outputs)

### LAQF.D2:0 - Use this when

Use this when each pipeline stage emits a large document *and* a parallel machine-readable shadow (a giant Markdown plus a JSON copy of the same content), or a single monolithic artefact far larger than the next stage consumes — and you are deciding what each stage should actually produce.

**What goes wrong if missed.** Every stage emits one giant artefact plus a JSON shadow of the same content — pipeline-level graphomania (rc-21; S-033, S-034). The two forms drift as one is edited and the other is not, double the maintenance, and flood the next stage's context with content it never reads.

**What this buys.** Each stage emits one artefact, in one authoritative form, sized to what the next stage consumes. If a machine-readable form is needed it is *generated* from the single source, never co-authored as a second hand-maintained copy.

**Not this pattern when.** A stage genuinely produces two distinct artefacts for two distinct consumers (not two copies of one). D2 collapses *duplicate* and *oversized* emission; it does not forbid legitimately separate outputs. This is the pipeline-scale instance of A2 (delta over whole-artefact) and B4 (self-imposed output budget) — same `MF-6` family, stage granularity.

### LAQF.D2:1 - Problem frame

The pipeline was built so each stage hands a complete record to the next, and "complete" drifted into "everything, twice": a human-readable monolith and a JSON shadow, each stage. But the next stage attends only the slice it consumes (the same effective-attention ceiling as everywhere, G.2-F2), and the duplicate form is pure drift risk. Anthropic's own brevity experiment shows the *opposite* failure is also real — over-clamping output cost a 3% eval drop (L04) — so the target is task-necessary content in one form, not minimal tokens. This is a Design cause (D:0): the emission shape is the user's to rewrite. The frame is one stage, one artefact, one form.

### LAQF.D2:2 - Problem

How can each pipeline stage hand the next stage exactly what it needs, in a single authoritative form, without emitting a duplicate shadow copy or a monolith larger than the consumer reads — while still not over-clamping below task-necessary content?

### LAQF.D2:3 - Forces

| Force | Tension |
|---|---|
| Completeness vs economy | A full record per stage ↔ the next stage reads only a slice (G.2-F2). |
| One form vs shadow copy | A single authoritative artefact ↔ a parallel JSON that drifts. |
| Trim vs floor | Cutting duplicate/oversized output ↔ the 3% drop from over-clamping (L04). |
| Design-able | The emission shape is the user's pipeline; it is rewritten, not adapted-around. |

### LAQF.D2:4 - Solution

Emit **one artefact per stage, in one authoritative form**, sized to the consumer. Pick the single form the next stage actually reads; if a machine-readable view is required, generate it from that source rather than hand-authoring a second copy. Size the artefact to what the downstream stage consumes — the pipeline-scale application of A2/B4's economy — and floor it at task-necessary content so the cut does not cross L04's over-clamp line. This is `MF-6` output shaping ([[12-01-source-pack]] §6) at stage granularity. C5 decides whether the single-form rule is worth a deterministic output-shape check or stays advisory. The transformation is direct: the duplicate shadow and the monolith are collapsed into one right-sized artefact.

- **One authoritative form.** Each stage emits a single form; a second view is generated, not co-authored.
- **Sized to the consumer.** The artefact carries what the next stage reads, not an exhaustive record.
- **Floored, not minimised.** The cut stops at task-necessary content (L04 floor), never below.

*One stage, one artefact, one form — generate the machine view, never hand-maintain a second copy.*

### LAQF.D2:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A stage that emits one right-sized form cannot drift against itself and does not flood the next stage; a stage that emits a monolith plus a JSON shadow does both.

**Show #1 (Claude Code session).** A planning stage emits a 1,200-line plan plus a `plan.json` mirror of it. Under D2: the stage emits the plan in one form; the small structured index the dispatcher needs is generated from it, so the two cannot disagree and the next stage reads a right-sized artefact. Without D2: a later edit updates the Markdown but not the JSON, the dispatcher acts on the stale shadow, and both forms bloat the downstream window (S-033, S-034).

**Show #2 (build-system episteme).** A reproducible build never hand-maintains a generated artefact beside its source — the object file is *derived* from the source, so they cannot diverge; checking both into version control is the classic drift bug. D2 is the single-source-of-truth discipline applied to pipeline stages: author one form, derive the rest, and L04 is the reminder that the derivation must not strip content the consumer genuinely needs.

### LAQF.D2:6 - Bias-Annotation

Lenses tested: **Arch**, **Eco**. Scope: per-stage emission shape.

- **Arch bias:** favours a single source with derived views over two hand-maintained copies; risk is treating two genuinely distinct artefacts as duplicates — bounded by collapsing only same-content shadows, not separate consumers' outputs.
- **Eco bias:** attends the token cost the emission imposes on every downstream window; risk is over-clamping below task-necessary content — bounded by the L04 floor.

### LAQF.D2:7 - Conformance Checklist

1. **CC-D2-1 (Single form).** Each stage emits one authoritative form; any machine-readable view is generated from it, not co-authored.
2. **CC-D2-2 (Sized to consumer).** The artefact carries what the next stage reads, not an exhaustive monolith.
3. **CC-D2-3 (Floored).** The cut stops at task-necessary content (L04 floor); over-clamping is a failure on the other side.
4. **CC-D2-4 (Detection wired).** Reads output-economy s5: leading = lines/stage and presence of a same-content shadow copy; lagging = downstream-window flood / shadow-drift defects.

### LAQF.D2:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Emit Markdown + a JSON shadow** | the two forms drift silently (S-034) | one authoritative form; generate the machine view |
| **Hand the next stage everything** | floods the consumer's attention budget (G.2-F2) | size the artefact to what the consumer reads |
| **Over-clamp the stage output** | strips content the consumer needs (3% drop, L04) | floor at task-necessary content |

### LAQF.D2:9 - Consequences

**Benefits.** Stage outputs stop drifting against their own shadows; the downstream window is not flooded; output-economy (s5) returns toward the green band at pipeline scale; the maintenance cost of double-authoring disappears.

**Trade-offs.** Generating a machine view from the source is a small amount of tooling, and judging "task-necessary" size is itself a call; bounded by collapsing only same-content shadows and holding the L04 floor.

### LAQF.D2:10 - Rationale

rc-21 is A2/B4's economy failure relocated from the single turn to the pipeline stage: where A2 emits a delta not a whole artefact and B4 caps a turn, D2 emits one right-sized form not a monolith-plus-shadow per stage. Keeping it a distinct pattern preserves each `EntityOfConcern` (`E.8:0.3`): A2/B4 own conversational output, D2 owns inter-stage artefacts. Routing the machine view through *generation* is what makes the single-form rule hold without losing the structured consumer.

### LAQF.D2:11 - SoTA-Echoing

- **Claim:** constraining emission form controls verbosity and flood. **Practice:** answer-budget, delta-only, `--quiet`+JSON-on-failure as output-shaping moves. **Source:** `MF-6` ([[12-01-source-pack]] §6). **Alignment:** D2 applies output-shaping at stage granularity — one form, sized to the consumer. **Status:** adopt.
- **Claim:** over-clamping output degrades quality. **Practice:** Anthropic reverted ≤25/≤100-word caps after a 3% eval drop. **Source:** L04 (T1+T5). **Alignment:** D2 floors the cut at task-necessary content rather than minimising tokens. **Status:** adopt.

### LAQF.D2:12 - Relations

- **Design cause (D:0):** monolithic + duplicate emission via [[../11-fpf-diagnostic]] D2 — transformed by collapsing to one right-sized form; MUST NOT read as forbidding two genuinely distinct artefacts.
- **Measurement (R2):** output-economy s5 ([[12-02-measurement-frame]] §2 card `laqf.mm.s5`; floored per L04).
- **Method family:** `MF-6` (output shaping) at stage granularity.
- **Coordinates with:** A2 (delta over whole-artefact, turn scale); B4 (self-imposed output budget, turn scale); E5 (Quiet Toolchain Output — the same `MF-6` family on tool output); C5 (whether the single-form rule earns a deterministic check).

### LAQF.D2:End

---

## LAQF.D3 - Roadmap-Anchored Dispatch

> **Type:** Principle pattern (P) — LAQF Layer-D
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see D:0)
> **FPF kind:** Design (workflow topology) — transform via Work (direct)
> **Detection characteristic:** scope-fidelity (`12-02` s8)
> **Source mechanism:** rc-22 (manual dispatch, no roadmap)

### LAQF.D3:0 - Use this when

Use this when the user manually invokes every pipeline stage in sequence, holds the plan-of-record in their own head, and there is no durable roadmap or milestone tracking — so independent stages run serially and nothing but the user knows what is done and what is next.

**What goes wrong if missed.** The user is the scheduler: each stage is hand-invoked, independent stages that could run in parallel run one at a time, and there is no roadmap, so milestone tracking lives only in the user's memory (rc-22; S-035, S-039). Progress is invisible across a `/clear`, and the multi-agent speed-up from parallel dispatch is left on the table.

**What this buys.** A durable roadmap — a milestone DAG with stages, dependencies, and status — that anchors dispatch: independent stages dispatch in parallel, the roadmap (not the user) tracks done-and-next, and progress survives context resets.

**Not this pattern when.** The workflow is a single linear stage with no parallelism and no cross-session horizon. D3 anchors *multi-stage* dispatch; B2 (handoff re-entry) re-establishes a single agent's identity, and D1 (re-entry) is the return edge the roadmap records.

### LAQF.D3:1 - Problem frame

The pipeline grew stage by stage, each added as a command the user runs, so dispatch became a manual ritual and the plan-of-record never left the user's head. Two costs follow. First, independent stages that a lead-plus-subagents topology would run in parallel (L18 reports a +90.2% gain for that decomposition) instead run serially. Second, with no durable roadmap the milestone state evaporates at the next `/clear` — the same volatility the progress-spine discipline (`MF-4` state externalisation) exists to cure. This is a Design cause (D:0): the dispatch topology is the user's to rewrite. The frame is to anchor dispatch to a durable roadmap.

### LAQF.D3:2 - Problem

How can pipeline dispatch be driven by a durable roadmap — parallelising independent stages and tracking milestone status outside the user's memory — rather than by the user hand-invoking each stage in series?

### LAQF.D3:3 - Forces

| Force | Tension |
|---|---|
| Manual vs anchored dispatch | The user invokes each stage ↔ a roadmap drives dispatch. |
| Serial vs parallel | Independent stages run one at a time ↔ parallel decomposition (+90.2%, L18). |
| In-head vs durable plan | Milestone state in the user's memory ↔ a roadmap that survives `/clear` (`MF-4`). |
| Design-able | The dispatch topology is the user's; it is rewritten, not adapted-around. |

### LAQF.D3:4 - Solution

Anchor dispatch to a **durable milestone roadmap**. Externalise the plan-of-record as a DAG of stages with dependencies and status (the progress-spine `MF-4` move, [[12-01-source-pack]] §6); dispatch independent stages in parallel rather than serially (the lead-plus-subagents decomposition, L18); and track done-and-next on the roadmap, not in the user's head, so the state survives a context reset. The roadmap is the scope-of-record: a dispatch that follows it stays in planned scope, and an off-roadmap dispatch is a visible scope miss. D1 records its re-entry edges on this roadmap; D4 keeps each dispatched agent in its lane. The transformation is direct: the user stops being the scheduler.

- **Roadmap as plan-of-record.** A durable milestone DAG holds stages, dependencies, status (`MF-4`).
- **Parallel where independent.** Independent stages dispatch concurrently, not in series (L18).
- **Roadmap tracks state.** Done-and-next lives on the roadmap and survives `/clear`, not in memory.

*Let a durable roadmap drive dispatch — parallelise the independent stages and track milestones outside your own memory.*

### LAQF.D3:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A roadmap-anchored pipeline dispatches independent stages in parallel and remembers its own state; a hand-invoked pipeline serialises everything and forgets at the next reset.

**Show #1 (Claude Code session).** A feature needs API design, a database schema, and a UI spec — three stages with no mutual dependency. Under D3: the roadmap marks them independent and dispatches all three in parallel, then converges; the milestone file records each as done, so a `/clear` mid-build resumes exactly where it stopped. Without D3: the user runs them one after another and, after a compaction, cannot tell which finished (S-035, S-039).

**Show #2 (build-orchestration episteme).** `make` and Bazel do not ask the developer to invoke each compile in order — they read a dependency DAG, run independent targets in parallel, and skip what is already built. D3 is that build-graph discipline applied to an agent pipeline: the roadmap is the DAG, parallel stages are independent targets, and L18's +90.2% is the parallel-dispatch dividend the manual ritual forgoes.

### LAQF.D3:6 - Bias-Annotation

Lenses tested: **Arch**, **Gov**. Scope: pipeline dispatch scheduling.

- **Arch bias:** treats dispatch as a dependency graph executed against a durable plan; risk is over-parallelising stages that share hidden state — bounded by dispatching in parallel only stages the roadmap marks independent.
- **Gov bias:** the roadmap is an accountability artefact (what is planned, what is done, what is next); shared discipline with D1's re-entry record and the progress spine.

### LAQF.D3:7 - Conformance Checklist

1. **CC-D3-1 (Durable roadmap).** A milestone DAG holds stages, dependencies, and status outside the conversation window (`MF-4`).
2. **CC-D3-2 (Parallel where independent).** Stages the roadmap marks independent are dispatched concurrently, not serially.
3. **CC-D3-3 (Roadmap tracks state).** Done-and-next lives on the roadmap and survives a `/clear`, not only in the user's memory.
4. **CC-D3-4 (Detection wired).** Reads scope-fidelity s8: leading = stage dispatched off-roadmap, or independent stages dispatched serially; lagging = lost milestone state after a reset (§7 char 8).

### LAQF.D3:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **User hand-invokes every stage** | serialises independent work; state lives in memory | anchor dispatch to a durable roadmap (`MF-4`) |
| **No milestone tracking** | progress evaporates at the next `/clear` | record done-and-next on the roadmap |
| **Parallelise everything** | stages with hidden shared state collide | parallelise only roadmap-marked independent stages |

### LAQF.D3:9 - Consequences

**Benefits.** Independent stages run in parallel and capture the L18 dividend; milestone state survives context resets; the user stops being the scheduler; scope-fidelity (s8) holds because dispatch tracks the planned roadmap.

**Trade-offs.** Authoring and maintaining the roadmap is up-front discipline, and a stale roadmap mis-dispatches; bounded by treating the roadmap as the live plan-of-record (the progress-spine `MF-4` move) and parallelising only marked-independent stages.

### LAQF.D3:10 - Rationale

rc-22 couples two distinct failures — no parallelism and no durable tracking — and a single anchor fixes both: the roadmap is simultaneously the dispatch DAG (which enables parallelism) and the externalised state (which survives `/clear`). Keeping D3 to "anchor dispatch to a roadmap" rather than splitting it preserves the single move (`E.8` maturity rule, `FPF-Spec.md:65222`) because the two symptoms share one cause — the absent plan-of-record. D4 then governs *what each dispatched agent may do*, which is a separate concern.

### LAQF.D3:11 - SoTA-Echoing

- **Claim:** decomposing into a lead plus parallel subagents outperforms a single agent. **Practice:** Opus-lead + Sonnet-subagents +90.2% over single Opus; subagents preserve context. **Source:** L18 (T1+T5). **Alignment:** D3 parallelises roadmap-independent stages to capture that gain. **Status:** adapt (the gain is the dispatch dividend; D3 adds the durable roadmap L18 does not specify).
- **Claim:** state must be externalised to survive the context window. **Practice:** just-in-time identifier loading; structured note-taking persists state outside the window. **Source:** L17 (T5). **Alignment:** D3's roadmap is the externalised milestone state. **Status:** adopt.

### LAQF.D3:12 - Relations

- **Design cause (D:0):** manual, untracked dispatch via [[../11-fpf-diagnostic]] D2 — transformed by anchoring to a durable roadmap; MUST NOT read as parallelising stages with hidden shared state.
- **Measurement (R2):** scope-fidelity s8 ([[12-02-measurement-frame]] §2 card `laqf.mm.s8`).
- **Method family:** `MF-5` (role decomposition — parallel dispatch) + `MF-4` (state externalisation — the roadmap).
- **Coordinates with:** D1 (records its re-entry edges on the roadmap); D4 (keeps each dispatched agent in its lane); B2 (single-agent re-entry after a context break).

### LAQF.D3:End

---

## LAQF.D4 - Enforced Role Lanes

> **Type:** Principle pattern (P) — LAQF Layer-D
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see D:0)
> **FPF kind:** Design (workflow topology) — transform via Work (direct)
> **Detection characteristic:** scope-fidelity (`12-02` s8)
> **Source mechanism:** rc-23 (role-boundary violations)

### LAQF.D4:0 - Use this when

Use this when specialised agents have defined roles but nothing constrains them to those roles — a TPM agent declares "this is frontend-only" (a scope decision it does not own), or reads source code it has no business reading — and you need each agent confined to its lane.

**What goes wrong if missed.** Roles are described in prose but not enforced, so an agent decides outside its scope: the TPM makes an architecture call, reads code, or declares constraints that belong to another role (rc-23; S-037, S-038). A prompt-level "you are the TPM, stay in scope" is advisory and, like any prompt-level instruction, is disobeyed exactly when it matters (ME-4 [L20]).

**What this buys.** A per-agent tool/scope lane enforced by a hook: each agent's allowable tools and file paths are an allowlist, and a call outside the lane is blocked — so an agent physically cannot act outside its role.

**Not this pattern when.** The agent is a generalist with no defined role to enforce. D4 fences *specialised* agents; C7 (Enforced Skill Invocation) gates a mandatory skill, and C6 (Whole-Path Permission Coverage) governs the human-facing allowlist — D4 governs the per-agent one.

### LAQF.D4:1 - Problem frame

The pipeline assigns roles — TPM, architect, engineer, reviewer — to get the context-decomposition benefit of specialisation (L18: subagents preserve context). But the role lives only in the agent's prompt, and a prompt-level boundary is not a forbid: agentic-misalignment work shows models disobey direct commands under the right pressure (ME-4 [L20]), so an agent steps outside its lane and makes a call it does not own. This is a Design cause (D:0): the lane is the user's to enforce. The frame is to make each agent's tool/scope lane a deterministic gate, not a prompt.

### LAQF.D4:2 - Problem

How can each specialised agent be confined to its role's tools and file scope — so it cannot make decisions, read sources, or touch files outside its lane — when a prompt-level role description does not deterministically constrain behaviour?

### LAQF.D4:3 - Forces

| Force | Tension |
|---|---|
| Enforced vs prompt-level lane | A per-agent tool/scope hook ↔ a role description disobeyed under pressure (ME-4). |
| Specialisation vs overreach | The context benefit of roles (L18) ↔ an agent deciding outside its scope. |
| Lane vs flexibility | A deterministic boundary ↔ a brittle block on a legitimate cross-role need. |
| Design-able | The role lane is the user's pipeline; it is gated, not adapted-around. |

### LAQF.D4:4 - Solution

Give each specialised agent a **deterministic tool/scope lane**. Define per role an allowlist of tools and file paths, and enforce it with a hook so a call outside the lane is blocked (`MF-1` deterministic forbid) — the TPM cannot invoke a code Read, the reviewer cannot Write source, an agent cannot declare a constraint another role owns. This is a specific `MF-1` instance of the C5 ruling, the per-agent analogue of C7's skill gate and C6's permission coverage. Pair it with the role decomposition itself (`MF-5`, L18) so the lanes match the context split. Reserve enforcement for genuine role boundaries; a legitimate cross-role need is a lane revision, not a bypass. The transformation is direct: the role moves from prompt description to enforced gate.

- **Per-agent allowlist.** Each role's tools and file paths are an explicit allowlist.
- **Block out-of-lane calls.** A hook blocks any tool or path outside the agent's lane (`MF-1`).
- **Lanes match the split.** The enforced lanes mirror the `MF-5` role decomposition (L18).

*Make each agent's role a gated lane, not a prompt line — an advisory "stay in scope" is crossed exactly when scope matters.*

### LAQF.D4:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** An agent behind a tool/scope hook cannot leave its lane; an agent told its role in prose leaves it whenever the turn's pressure outweighs the instruction.

**Show #1 (Claude Code session).** A TPM agent is meant to gather requirements, not make architecture calls or read source. Under D4: a hook scopes the TPM to docs/spec tools and blocks a code Read or an architecture-deciding Write — the TPM cannot declare "frontend-only" because that tool/path is not in its lane. Without D4: under a tight prompt the TPM reads the codebase and declares scope it does not own (S-037, S-038), and the advisory role line held only until it didn't.

**Show #2 (access-control episteme).** Least-privilege and separation-of-duties do not *ask* a role to stay in scope — they *deny* it the capability outside its scope: the clerk who books a payment cannot also approve it, because the permission is absent, not because a policy memo requested restraint. D4 is RBAC for agent roles, and ME-4 [L20] is the evidence that, for an LLM, the policy memo alone is overridden under pressure.

### LAQF.D4:6 - Bias-Annotation

Lenses tested: **Gov**, **Arch**. Scope: per-agent role enforcement.

- **Gov bias:** the per-agent allowlist and the block log are accountability controls (this agent provably stayed in its lane); shared audit trail with C5/C6/C7.
- **Arch bias:** treats roles as capability boundaries in the topology, not prose; risk is over-fencing a legitimate cross-role need — bounded by revising the lane explicitly rather than leaving a bypass.

### LAQF.D4:7 - Conformance Checklist

1. **CC-D4-1 (Per-agent lane).** Each specialised agent has an explicit tool/path allowlist for its role.
2. **CC-D4-2 (Out-of-lane blocked).** A hook blocks any tool call or file touch outside the agent's lane (`MF-1`).
3. **CC-D4-3 (Lanes match the split).** The enforced lanes mirror the role decomposition (`MF-5`, L18); a cross-role need is a lane revision, not a bypass.
4. **CC-D4-4 (Detection wired).** Reads scope-fidelity s8: leading = out-of-lane tool call / file touch blocked; lagging = role-boundary violation surfacing in review (§7 char 8).

### LAQF.D4:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Describe the role in the prompt only** | a prompt-level boundary is not a forbid (ME-4) | enforce a per-agent tool/scope hook (`MF-1`) |
| **One allowlist for all agents** | erases the role distinction the lanes exist for | scope the allowlist per role |
| **Bypass the lane for a one-off need** | re-opens the boundary silently | revise the lane explicitly; do not bypass |

### LAQF.D4:9 - Consequences

**Benefits.** Agents stay in their roles; out-of-lane decisions and reads are blocked before they happen; scope-fidelity (s8) on role boundaries reaches the green band; the specialisation benefit of decomposition (L18) is preserved because each lane holds.

**Trade-offs.** Per-agent lanes are hooks to author and maintain, and an over-tight lane blocks a legitimate cross-role action; bounded by enforcing genuine role boundaries and handling cross-role needs as explicit lane revisions.

### LAQF.D4:10 - Rationale

rc-23 is the per-agent `MF-1` instance of the C5 meta-pattern, alongside C6 (human permissions), C7 (skill invocation), E1 (verification) and F2 (commit hygiene): the same "advisory does not forbid; gate it" move, scoped to an agent's role. D4 owns one placement — the per-agent tool/scope lane — leaving C5 to own the deterministic-vs-advisory classification and D3 to own dispatch. This split keeps each pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) and makes the lane reusable across every role in the pipeline.

### LAQF.D4:11 - SoTA-Echoing

- **Claim:** a prompt-level instruction does not deterministically constrain an agent. **Practice:** agentic-misalignment — models disobey direct commands; only hook-level forbids prevent. **Source:** ME-4 [L20]. **Alignment:** D4's per-agent tool/scope hook is exactly the deterministic lane the prompt cannot supply. **Status:** adopt.
- **Claim:** role decomposition across agents preserves context and improves outcomes. **Practice:** Opus-lead + Sonnet-subagents; subagents preserve context, not intelligence. **Source:** L18 (T1+T5). **Alignment:** D4 enforces the lanes that make the decomposition hold rather than leak. **Status:** adopt.

### LAQF.D4:12 - Relations

- **Design cause (D:0):** unenforced role boundaries via [[../11-fpf-diagnostic]] D2 — transformed by a per-agent tool/scope gate; MUST NOT read as fencing a generalist with no defined role.
- **Measurement (R2):** scope-fidelity s8 ([[12-02-measurement-frame]] §2 card `laqf.mm.s8`).
- **Method family:** `MF-1` (deterministic forbid) + `MF-5` (role decomposition, L18).
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); C6 (human-facing permission coverage); C7 (mandatory-skill gate); D3 (dispatches the agents D4 confines).

### LAQF.D4:End

---

## See also

- [[12-13-patterns-D-ru]] — Russian twin
- [[12-10-patterns-A]] — frozen house-style exemplar (the 13-section template D1–D4 reuse)
- [[12-12-patterns-C]] — Layer-C (Design) patterns; D:0 inherits the C:0 design contract; C5 owns the deterministic/advisory classification D4 instantiates
- [[12-14-patterns-E]] — Layer-E (verification) patterns; E5 shares D2's `MF-6` output-shaping family
- [[12-00-spine]] — keystone: §5 roster (Design kind + detection), §4.3 relation records, §4.1 edition direction
- [[12-01-source-pack]] — G.2 pack; §8 palette `LAQF.sota.iter3.palette` cited by every §11 (L-/ME-/MF-/Γ_epist ids)
- [[12-02-measurement-frame]] — detection axes (§5 pattern↔characteristic; §2 DHCMethod cards; §3 CAL bands; §4 leading/lagging)
- [[_inputs/rc-digest]] — §4 Layer-D mechanisms (rc-20…rc-23)
- [[../11-fpf-diagnostic]] — D2 design-space ruling (the basis for the D:0 design contract)
- `FPF-Spec.md:65183` E.8 authoring conventions · `:65272` canonical template · `:24417` A.19 · `:42826` C.16 · `:87746` G.2
