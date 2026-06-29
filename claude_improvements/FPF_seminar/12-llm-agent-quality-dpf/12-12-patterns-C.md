---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, patterns, layer-c, e8-patterns]
seminar-iteration: 3
created: 2026-06-28
status: patterns-layer-c
method: FPF E.8 (authoring conventions) · 11-fpf-diagnostic D2 (Design-space / Work quadrant) · consumes 12-01 palette LAQF.sota.iter3.palette + 12-02 detection axes
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-12-patterns-C-ru]]"
---

# LAQF — Layer C patterns (user configuration): C1–C7

The seven **Layer-C** patterns of LAQF. Each addresses a property of the user's own Claude Code **configuration** — the `dot_claude` surface: the CLAUDE.md instruction stack, the skills, the agents, the hooks, the permission settings. In FPF terms each is a **Design** cause ([[../11-fpf-diagnostic]] D2 design-space): not a model-internal Law to mitigate (Layer A), nor someone else's harness boundary to adapt around (Layer B), but *the user's own surface* — transformable outright by direct Work.

These patterns reuse the house style frozen in [[12-10-patterns-A]] (the full `E.8` thirteen-section template, `FPF-Spec.md:65272`). Each cites the SoTA pack by id ([[12-01-source-pack]] §8 palette `LAQF.sota.iter3.palette`) and wires its detection slot to one `A.19` characteristic ([[12-02-measurement-frame]] §5). They assert no new evidence and re-paraphrase no source — an id, never a quote (`G.2:4.2`, `FPF-Spec.md:87904`).

## C:0 - The Layer-C design contract (read once, applies to C1–C7)

Stated here once so each Solution need not repeat it (`E.8:0.3` anti-repetition, `FPF-Spec.md:65234`). It is the Design analogue of the Layer-A mitigation contract ([[12-10-patterns-A]] A:0) and the Layer-B boundary contract ([[12-11-patterns-B]] B:0), governed by the [[../11-fpf-diagnostic]] D2 design-space ruling:

- **The cause is user-owned config — neither a Law nor a harness boundary.** Each C-pattern names something inside the user's `dot_claude` surface (the CLAUDE.md stack, a skill, an agent, a hook, a settings allowlist). Unlike a Law (mitigate) or a boundary (adapt), this surface is the user's to rewrite.
- **Direct Work, no hedge.** A C-pattern's Solution *transforms* the cause: it trims the stack, resolves the conflict, authors the missing skill, converts the advisory into a deterministic gate. There is no "mitigate-only" or "adapt-around" caveat — the config can be made to hold.
- **Layer-1 states *what*; Layer-2 (S6) realises *how*.** This Domain edition states the property the config must satisfy. The Local Practice edition (the user's actual CLAUDE.md / skill / hook, authored at S6) is the realisation. A C-pattern is verified by the property, not by one particular file.
- **Prefer deterministic over advisory where a rule must hold.** Advisory prose plateaus around the adherence ceiling (L15 ≈70%); a rule that *must* hold belongs in a hook (`MF-1`), not in prose (`MF-2`). C5 owns the full classification; every other C-pattern inherits this preference and points to C5 rather than restating it.
- **Detection is behavioural.** Each pattern's success is observed through one of the eight `A.19` characteristics ([[12-02-measurement-frame]] §1), read at the **leading** (mid-session) indicator, not only the lagging outcome (§4 of the frame).

---

## LAQF.C1 - Instruction-Stack Within Budget

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** attention-budget-load (`12-02` s7)
> **Source mechanism:** rc-13 (CLAUDE.md bloat)

### LAQF.C1:0 - Use this when

Use this when authoring or auditing the CLAUDE.md stack (UAP + project + workspace layers) and any always-on skills — deciding what stays resident every turn versus what moves to on-demand loading, so the resident stack fits the model's effective attention.

**What goes wrong if missed.** The resident stack grows to 509 lines — 2.5×–5× over Anthropic's guidance budget (rc-13; L23) — and overflows the ~150-instruction effective attention window (G.2-F2). Rules past the budget are not enforced because the model never attends them; adding more text makes adherence *worse*, not better.

**What this buys.** A resident stack trimmed to what must hold every turn, with conditional rules moved to skills loaded just-in-time (L17). The model attends the whole resident stack, and a well-maintained context measurably improves outcomes (L21).

**Not this pattern when.** The stack is already inside budget. C1 is the *trim action*; B3 (Attention-Budget Ledger) is the boundary-side *measurement* that triggers it, and C2 (Single-Owner Rule Resolution) clears the conflicts trimming surfaces.

### LAQF.C1:1 - Problem frame

Every turn the harness loads the full CLAUDE.md stack plus always-on skills into the system prompt. The user keeps adding rules because each *feels* like more control, but the model attends only ~150 instructions well (G.2-F2; L12). At 509 resident lines the stack is 3.4× that budget (L23), so the marginal rule does not add control — it pushes an older rule over the cliff. This is a Design cause (C:0): the stack is the user's to rewrite. The frame is to make the resident stack fit the budget and load the rest on demand.

### LAQF.C1:2 - Problem

How can the user keep every must-hold rule effective when the resident instruction stack exceeds the model's effective attention — so that adding the next rule does not silently drop an earlier one?

### LAQF.C1:3 - Forces

| Force | Tension |
|---|---|
| Coverage vs attention | More resident rules ↔ each dilutes the ~150-instruction budget. |
| Always-on vs on-demand | A rule resident every turn ↔ a rule loaded only when relevant (L17). |
| Trim cost vs adherence | Editing the stack down ↔ the adherence gained when it fits. |
| Design-able | The stack is the user's config; it is rewritten, not adapted-around. |

### LAQF.C1:4 - Solution

Trim the **resident stack to the attention budget** and move the rest just-in-time. Keep in CLAUDE.md only the rules that must hold on *every* turn; relocate conditional and domain-specific rules to skills loaded on trigger (`MF-4` state externalisation via L17 just-in-time loading). Compare the trimmed resident count against the ~150-instruction effective attention (G.2-F2), not the raw file size. B3 supplies the count that fires C1; C2 resolves the conflicts the trim exposes; C5 decides which survivors become deterministic hooks. The transformation is direct: the config is rewritten so the resident stack fits.

- **Resident = must-hold-every-turn.** Only always-applicable rules stay in CLAUDE.md.
- **Conditional ⟶ on-demand.** Domain/task-specific rules move to skills loaded just-in-time (L17).
- **Budget, not file size.** Trim against the ~150 effective-attention ceiling (G.2-F2), using B3's count.

*Keep resident only what must hold every turn; load the rest when it is needed.*

### LAQF.C1:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A short resident stack the model fully attends beats a long one whose tail is never read.

**Show #1 (Claude Code session).** The stack is 509 lines (UAP 216 + devbox-setup 196 + workspace 97, L23). Under C1: the Go-formatting rule, the worktree-layout detail, and the per-language conventions move into on-demand skills; the resident stack drops toward the ~150 budget and every resident rule is attended. Without C1: a 510th rule is added, an early rule silently stops firing, and the user concludes "Claude ignores CLAUDE.md".

**Show #2 (interface-design episteme).** A cockpit puts the always-needed instruments in the primary scan and the rest one reach away; cramming everything into the primary view degrades the scan for all of it. C1 is the same triage applied to the instruction stack — resident is the primary scan, skills are the reachable panel — and L21 quantifies the payoff: a well-maintained context yields 40% fewer errors and 55% faster work.

### LAQF.C1:6 - Bias-Annotation

Lenses tested: **Arch**, **Gov**. Scope: instruction-stack authoring.

- **Arch bias:** treats the resident stack as a budgeted surface with a ceiling; risk is over-trimming a genuinely always-on rule into a skill that fails to load — bounded by keeping must-hold-every-turn rules resident.
- **Gov bias:** the resident/on-demand split is an auditable decision (why is this rule resident?); shared discipline with C2's single-owner register.

### LAQF.C1:7 - Conformance Checklist

1. **CC-C1-1 (Resident is must-hold).** The resident stack contains only rules that apply on every turn.
2. **CC-C1-2 (Conditional moved).** Domain/task-specific rules are loaded just-in-time as skills, not resident.
3. **CC-C1-3 (Budget compared).** The trim target is the ~150 effective-attention ceiling (via B3), not raw line count.
4. **CC-C1-4 (Detection wired).** Reads attention-budget-load s7: leading = resident-stack line count; lagging = adherence drift as the stack grows (G.2-F2 plateau).

### LAQF.C1:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Pile everything into CLAUDE.md** | overflows the ~150 budget (G.2-F2) | keep resident = must-hold; move the rest to skills |
| **Add-a-rule-to-fix-adherence** | the new rule pushes an old one off the cliff | trim first (B3 count), then add |
| **Trim by deletion, not relocation** | loses a rule that was genuinely needed sometimes | relocate to an on-demand skill (L17) |

### LAQF.C1:9 - Consequences

**Benefits.** Every resident rule is actually attended; adherence stops degrading as the config grows; attention-budget-load (s7) returns toward the green band; the maintained-context dividend (L21) is realised.

**Trade-offs.** Splitting the stack into resident + on-demand skills is authoring overhead, and a mis-tagged conditional rule may fail to load when needed; bounded by keeping must-hold-every-turn rules resident and by C2's single-owner discipline.

### LAQF.C1:10 - Rationale

rc-13 is the design-side twin of the rc-11 boundary: B3 measures the attention load (the harness offers no meter), C1 acts on it (the config is the user's to cut). Splitting measurement from action keeps each pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`); routing the cut through L17's just-in-time loading is what lets coverage survive the trim rather than being deleted.

### LAQF.C1:11 - SoTA-Echoing

- **Claim:** instruction adherence is bounded by an effective-attention ceiling. **Practice:** ~150-instruction effective window; IFScale 68% at 500. **Source:** G.2-F2, L12 (T3). **Alignment:** C1 trims the resident stack toward that ceiling rather than past it. **Status:** adopt.
- **Claim:** a well-maintained context improves outcomes; state belongs outside the resident window. **Practice:** 40% fewer errors / 55% faster with maintained context; just-in-time identifier loading. **Source:** L21, L17 (T5). **Alignment:** C1's resident/on-demand split is exactly the maintenance move. **Status:** adopt.

### LAQF.C1:12 - Relations

- **Design cause (C:0):** the CLAUDE.md stack via [[../11-fpf-diagnostic]] D2 — transformed by trimming; MUST NOT read as "more text means more control".
- **Measurement (R2):** attention-budget-load s7 ([[12-02-measurement-frame]] §2 card `laqf.mm.s7`); ceiling per Γ_epist G.2-F2.
- **Method family:** `MF-4` (state externalisation — conditional rules to on-demand skills, L17).
- **Coordinates with:** B3 (measures the overflow that triggers C1); C2 (resolves conflicts the trim surfaces); C5 (which survivors become deterministic hooks).

### LAQF.C1:End

---

## LAQF.C2 - Single-Owner Rule Resolution

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** attention-budget-load (`12-02` s7)
> **Source mechanism:** rc-14 (inter-asset rule conflicts)

### LAQF.C2:0 - Use this when

Use this when the same rule appears in more than one config asset, or two assets give conflicting instructions (one-question vs batched-questions; subagent-acts vs main-approval; "disclosure block" vs "no preamble") — and you must decide where the rule lives and which side of the conflict wins.

**What goes wrong if missed.** A rule duplicated across assets drifts as one copy is edited and the other is not; a live conflict (rc-14; S-007/008/009/026) forces the model to arbitrate at runtime, and each conflicting pair is an attention tax that degrades adherence (G.2-F2). The user cannot tell which copy is authoritative.

**What this buys.** Each rule has exactly one owning asset; cross-references point to the owner instead of copying it; conflicts are resolved once, at authoring time, not re-arbitrated every turn.

**Not this pattern when.** The config has no duplication or conflict. C2 is the *resolution action*; B3 *counts* the conflict pairs that trigger it, and C1 supplies the resident/on-demand structure C2 assigns ownership within.

### LAQF.C2:1 - Problem frame

The config accreted over time: the same discipline got written into the UAP, a project CLAUDE.md, and a skill; two rules authored months apart now contradict. The model must reconcile them at runtime, and benchmarks show multi-instruction following degrades with conflicting and dense instructions (L13). Every duplicate is a drift risk; every conflict is an attention tax (G.2-F2). This is a Design cause (C:0): the assets are the user's to refactor. The frame is to give each rule one owner and resolve conflicts at authoring time.

### LAQF.C2:2 - Problem

How can the config present each rule once, from a single authoritative owner, with conflicts resolved ahead of time — so the model never has to arbitrate duplicated or contradictory instructions mid-session?

### LAQF.C2:3 - Forces

| Force | Tension |
|---|---|
| Duplication vs single source | A rule copied for convenience ↔ copies drift apart. |
| Local override vs global rule | A project-specific exception ↔ the workspace default. |
| Resolve-now vs arbitrate-later | One authoring-time decision ↔ a per-turn attention tax (G.2-F2). |
| Design-able | The assets are the user's config; ownership is assigned, not inferred. |

### LAQF.C2:4 - Solution

Give every rule **one owning asset** and resolve conflicts at authoring time. Assign each rule a single home (the most general asset where it always applies); everywhere else, cross-reference the owner — never copy the text. Where two assets conflict, decide the winner once and edit the loser to defer or be removed, recording the resolution. B3 counts the conflict pairs that trigger C2; C1 supplies the resident/on-demand layering ownership is assigned within; C5 turns a must-hold resolved rule into a deterministic gate. The transformation is direct: the config is refactored so each rule speaks once.

- **One owner per rule.** The rule's text lives in exactly one asset; the rest cross-reference it.
- **Cross-reference, never duplicate.** A second mention points to the owner; it does not restate the rule.
- **Resolve conflicts at authoring time.** Pick the winner once; edit the loser; record the decision — do not leave the model to arbitrate.

*One rule, one owner — reference it everywhere else, and settle conflicts before the session, not during it.*

### LAQF.C2:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A rule with one owner cannot drift against itself; a conflict resolved at authoring time is not re-fought every turn.

**Show #1 (Claude Code session).** The UAP says "batch all questions into one `AskUserQuestion`"; an older skill still says "ask one question at a time". Under C2: the batched-questions rule is owned by the UAP, the skill is edited to defer to it (or the stale line removed), and the conflict pair drops out of B3's register. Without C2: the model meets both rules each turn, picks one unpredictably, and adherence on questioning becomes noise (S-007).

**Show #2 (data-modelling episteme).** Database normalisation removes update anomalies: a fact lives in one table, referenced by key elsewhere, so it cannot be updated in one place and stale in another. C2 is third-normal-form for the instruction stack — a rule lives in one asset, referenced by pointer elsewhere — and L13's conflict-degradation finding is the cost of the un-normalised form.

### LAQF.C2:6 - Bias-Annotation

Lenses tested: **Arch**, **Gov**. Scope: cross-asset rule authoring.

- **Arch bias:** favours a normalised single-owner structure over convenient duplication; risk is over-indirection (a chain of cross-references hard to follow) — bounded by owning each rule at its most general always-applicable asset.
- **Gov bias:** the owner map and the conflict-resolution log are accountability artefacts (which asset owns this rule, why this side won); shared register with B3.

### LAQF.C2:7 - Conformance Checklist

1. **CC-C2-1 (Single owner).** Each rule's text lives in exactly one asset; other mentions cross-reference it.
2. **CC-C2-2 (No duplication).** No rule is copied verbatim across assets.
3. **CC-C2-3 (Conflicts resolved).** Each known conflict pair has a recorded winner and an edited loser.
4. **CC-C2-4 (Detection wired).** Reads attention-budget-load s7: leading = conflicting-rule-pair count (B3 register); lagging = adherence drift / unpredictable arbitration as the config grows (G.2-F2).

### LAQF.C2:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Copy the rule for convenience** | copies drift apart silently | one owner; cross-reference elsewhere |
| **Leave the conflict for the model** | per-turn attention tax + unpredictable choice (L13) | resolve once at authoring time |
| **Resolve by adding a third rule** | grows the stack, adds a new pair | edit the loser; do not stack arbitration prose |

### LAQF.C2:9 - Consequences

**Benefits.** Rules stop drifting against themselves; the model never arbitrates mid-session; the conflict-pair count (an s7 component) falls; adherence on the affected rules becomes predictable.

**Trade-offs.** Refactoring to single-owner is up-front work and deep cross-reference chains can be hard to trace; bounded by owning each rule at its most general always-applicable asset and keeping the owner map auditable.

### LAQF.C2:10 - Rationale

rc-14 is the conflict face of the attention boundary: where C1 cuts the stack's *length*, C2 cuts its *contradiction* and *duplication* — both s7 loads. Keeping them as two patterns preserves each `EntityOfConcern` (`E.8:0.3`): C1 owns "fits the budget", C2 owns "speaks once, without conflict". B3 measures both; C5 decides which resolved rule earns a hook.

### LAQF.C2:11 - SoTA-Echoing

- **Claim:** following degrades with conflicting and dense instructions. **Practice:** LIFBench / AgentIF quantify multi-instruction and conflict degradation. **Source:** L13 (T3); G.2-F2. **Alignment:** C2 removes the conflicts and duplication that drive the degradation. **Status:** adopt.
- **Claim:** a well-maintained context improves outcomes. **Practice:** 40% fewer errors / 55% faster with maintained context. **Source:** L21 (T5). **Alignment:** single-owner normalisation is part of that maintenance. **Status:** adopt.

### LAQF.C2:12 - Relations

- **Design cause (C:0):** inter-asset conflicts via [[../11-fpf-diagnostic]] D2 — transformed by normalising ownership; MUST NOT read as the model reliably arbitrating conflicts.
- **Measurement (R2):** attention-budget-load s7 ([[12-02-measurement-frame]] §2 card `laqf.mm.s7`, conflict-pair component).
- **Method family:** authoring-time normalisation; feeds the `MF-1`/`MF-2` choice at C5.
- **Coordinates with:** B3 (counts the conflict pairs that trigger C2); C1 (the resident/on-demand layering ownership is assigned within); C5 (turns a resolved must-hold rule into a hook).

### LAQF.C2:End

---

## LAQF.C3 - Encoded Engineering Posture

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** sycophancy-rate (`12-02` s4)
> **Source mechanism:** rc-15 (no encoded engineering attitude)

### LAQF.C3:0 - Use this when

Use this when the agent needs a consistent engineering *stance* — challenge a false dichotomy, demand evidence over assertion, prefer a change that solves two problems at once, treat a claimed result as a hypothesis until observed — and that stance is currently left to the model's mood rather than encoded anywhere.

**What goes wrong if missed.** With no asset encoding the posture, the stance is whatever the RLHF balance produces that turn: sometimes a useful challenge, sometimes reflexive pushback (L19), sometimes sycophantic agreement. The behaviour is inconsistent because nothing makes it a stable disposition (rc-15; S-017–S-022/024).

**What this buys.** A skill that encodes the engineering posture as explicit, literal instructions (L02) the model follows consistently — Fisher's maxim (the data decide), anti-false-dichotomy, shadow-mode / consider-but-confirm, kill-two-birds — so the stance is a setting, not a coin-flip.

**Not this pattern when.** The behaviour wanted is a hard gate (must-run-before-commit), not a disposition. That is C5/C7 territory; C3 encodes *judgement stance*, which is inherently advisory (`MF-2`).

### LAQF.C3:1 - Problem frame

The user wants the agent to think like a particular kind of engineer — evidence-driven, sceptical of false binaries, biased toward changes that pay off twice. Across sessions that stance appears and disappears, because the model's default is the RLHF disposition, which over-corrects between sycophancy and reflexive pushback (L19). The model interprets explicit instructions literally and does not generalise an unstated stance (L02). This is a Design cause (C:0): the posture can be authored into a skill. The frame is to encode the stance instead of hoping for it.

### LAQF.C3:2 - Problem

How can a consistent engineering posture be installed as a stable disposition the agent applies across sessions, when nothing currently encodes it and the model's default oscillates between sycophancy and reflexive pushback?

### LAQF.C3:3 - Forces

| Force | Tension |
|---|---|
| Encoded stance vs model mood | An authored posture ↔ the per-turn RLHF disposition (L19). |
| Advisory vs gate | A judgement stance is advisory ↔ a must-hold rule is a hook (C5). |
| Explicit vs implicit | Literal encoded instructions (L02) ↔ hoping the model infers the stance. |
| Design-able | The posture is the user's to author into a skill. |

### LAQF.C3:4 - Solution

Author a **skill that encodes the engineering posture** as explicit, literal instructions. Capture the stance as named, followable rules — Fisher's maxim (let the evidence decide; kinship with A1's substance gate and E3's counter-evidence audit), reject false dichotomies, shadow-mode / consider-but-confirm before acting, prefer the change that solves two problems at once — and rely on the model's literalness (L02) to follow them. This is the `MF-2` advisory family ([[12-01-source-pack]] §6): a disposition, not a gate. C3 *installs* the stance that A1 *gates* (substance-bearing dissent) and A3 *shapes* (answer-first). The transformation is direct: the posture goes from unencoded to authored.

- **Encode, don't hope.** The stance lives in a skill as explicit, literal rules (L02), not in the model's mood.
- **Name the moves.** Fisher's maxim, anti-false-dichotomy, shadow-mode/CBC, kill-two-birds — each a followable instruction.
- **Advisory by nature.** A judgement stance is `MF-2`; where a rule must *hold*, route it to C5, not into this skill.

*Encode the stance you want as explicit rules — do not leave the engineering posture to the model's mood.*

### LAQF.C3:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A posture encoded as explicit rules is applied consistently; a posture left implicit is whatever the RLHF balance emits that turn.

**Show #1 (Claude Code session).** User: "should we cache or denormalise?" Without C3: the model picks one and defends it, or hedges sycophantically. Under C3: the encoded posture fires — "false dichotomy: you can do both, or neither may be the bottleneck; what does the profile show?" (Fisher's maxim + anti-false-dichotomy), turning a forced binary into an evidence question. The stance is the same next session because it is encoded, not improvised.

**Show #2 (professional-formation episteme).** A residency programme installs a diagnostic posture — "treat the presenting complaint as a hypothesis, order the test, let the result decide" — so it survives individual mood and fatigue. C3 imports that formation discipline into config: the engineering stance is trained-in via an asset, not re-derived each session, against a model whose L19 default oscillates.

### LAQF.C3:6 - Bias-Annotation

Lenses tested: **Did**, **Gov**. Scope: judgement turns (design choices, claims, trade-offs).

- **Did bias:** the posture is authored as named, teachable moves (Fisher's maxim, kill-two-birds) precisely so it is followable and reviewable; risk is a skill too abstract to act on — bounded by phrasing each rule as a concrete instruction.
- **Gov bias:** an encoded posture is auditable (which stance rule fired, was it applied); pairs with A1's evidence-gate as the accountability layer.

### LAQF.C3:7 - Conformance Checklist

1. **CC-C3-1 (Stance encoded).** The engineering posture lives in a skill as explicit, literal rules, not implicit expectation.
2. **CC-C3-2 (Moves named).** Fisher's maxim, anti-false-dichotomy, shadow-mode/CBC, kill-two-birds are each a followable instruction.
3. **CC-C3-3 (Advisory scope).** Must-hold rules are routed to C5 (hooks), not encoded as advisory stance here.
4. **CC-C3-4 (Detection wired).** Reads sycophancy-rate s4: leading = per-turn false-dichotomy / unevidenced-agreement flag; lagging = inconsistent stance across sessions (L19 oscillation).

### LAQF.C3:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Hope the model has the stance** | the L19 default oscillates | encode it as explicit rules in a skill |
| **Encode it as vague aspiration** | not literally followable (L02) | phrase each move as a concrete instruction |
| **Try to hook a judgement stance** | judgement is not a deterministic gate | keep stance advisory (MF-2); route gates to C5 |

### LAQF.C3:9 - Consequences

**Benefits.** The engineering posture becomes consistent across sessions; false dichotomies and unevidenced agreement drop; sycophancy-rate (s4) improves on judgement turns; A1's gate and E3's audit gain a stance to operate within.

**Trade-offs.** An advisory skill is bounded by the adherence ceiling (L15 ≈70%) — it raises the floor but does not guarantee the stance; a must-hold sub-rule still needs C5. Bounded by reserving C3 for genuine judgement and routing gates to deterministic enforcement.

### LAQF.C3:10 - Rationale

rc-15 is the config-side complement of rc-01: A1 mitigates the *reflex* (gate substance-free dissent), C3 installs the *stance* the reflex distorts (evidence-driven, anti-binary). Both read s4. Keeping them distinct preserves each `EntityOfConcern` (`E.8:0.3`): A1 is a Law-mitigation at the moment of dissent, C3 is a design-transformation that authors the disposition.

### LAQF.C3:11 - SoTA-Echoing

- **Claim:** the RLHF disposition oscillates between sycophancy and over-correction. **Practice:** sycophancy + reflexive pushback both documented; dynamic gating cut sycophancy 85.7% in research. **Source:** L19 (T4). **Alignment:** C3 encodes a stable stance rather than relying on the oscillating default. **Status:** adapt (research gating ≠ session rate; encoded as disposition, not metric).
- **Claim:** the model interprets explicit instructions literally and does not generalise an unstated stance. **Practice:** vendor guidance on literal instruction-following. **Source:** L02 (T1). **Alignment:** C3 relies on literalness — an explicitly encoded posture is followed. **Status:** adopt.

### LAQF.C3:12 - Relations

- **Design cause (C:0):** the missing posture skill via [[../11-fpf-diagnostic]] D2 — transformed by authoring it; MUST NOT read as a hard gate (advisory by nature).
- **Measurement (R2):** sycophancy-rate s4 ([[12-02-measurement-frame]] §2 card `laqf.mm.s4`).
- **Method family:** `MF-2` (advisory) — an encoded disposition.
- **Coordinates with:** A1 (gates substance-free dissent; C3 installs the evidence stance behind it); A3 (answer-first shaping); E3 (Counter-Evidence Audit shares Fisher's maxim).

### LAQF.C3:End

---

## LAQF.C4 - Tagged Facts Scaffold

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** reconnaissance-depth (`12-02` s2)
> **Source mechanism:** rc-16 (no facts-list scaffold)

### LAQF.C4:0 - Use this when

Use this when authoring the disclosure / restatement template the agent uses to record what it knows — requirements, values, decisions — so each fact carries its provenance instead of being a free-form paraphrase the model rolls on its own.

**What goes wrong if missed.** With no prescribed scaffold, the model invents its own restatement format and mixes user-stated facts, file-read facts, and its own drafts into one undifferentiated paraphrase (rc-16; S-014/015). Provenance is lost, so drift (a `[USER]` value silently replaced by a `[DRAFT]` guess) is undetectable.

**What this buys.** A prescribed facts scaffold that tags every fact with its origin — `[USER]` stated, `[DRAFT]` agent-produced-unconfirmed, `[FILE path:line]` read — so the model anchors to provenance and drift is visible at a glance.

**Not this pattern when.** The interaction is a one-shot exempt task with no facts to carry. C4 is the *config that prescribes the scaffold*; A6 is the *Law-mitigation* that uses it (anchor facts to origin), and A5/A7 produce the reads and disclosures it tags.

### LAQF.C4:1 - Problem frame

The agent restates facts constantly, but with no scaffold it formats each restatement ad hoc and loses the distinction between what the user said, what a file contains, and what the agent itself drafted. Because the model has no persistent working memory (the rc-06 Law behind A6), its own untagged paraphrase becomes the de-facto source. Vendor guidance is that structured note-taking persists state outside the window (L17). This is a Design cause (C:0): the template is the user's to author. The frame is to prescribe a provenance-tagged scaffold.

### LAQF.C4:2 - Problem

How can the config make every restated fact carry its origin — user, file, or agent draft — so the model anchors to provenance rather than to its own paraphrase, and drift becomes detectable?

### LAQF.C4:3 - Forces

| Force | Tension |
|---|---|
| Tagged vs free-form | A provenance-tagged scaffold ↔ ad-hoc paraphrase that loses origin. |
| Discipline vs overhead | Tagging every fact ↔ tagging only load-bearing ones. |
| Externalised vs recalled | A scaffold outside the window (L17) ↔ the model's drifting memory. |
| Design-able | The disclosure template is the user's config to prescribe. |

### LAQF.C4:4 - Solution

Prescribe a **provenance-tagged facts scaffold** in the disclosure/restatement template. Require each load-bearing fact to carry an origin tag — `[USER]` (stated by the user), `[DRAFT]` (agent-produced, unconfirmed), `[FILE path:line]` (read from source) — as a fixed section the agent fills before acting ([[_inputs/rc-digest]] §3). This is the `MF-4` state-externalisation move: the scaffold persists facts outside the model's memory with their provenance attached (L17). C4 is the Layer-2 realisation of A6 (anchor to origin); A5 produces the `[FILE path:line]` reads and A7 the disclosure it lives in. The transformation is direct: the template goes from free-form to provenance-tagged.

- **Tag every load-bearing fact.** `[USER]` / `[DRAFT]` / `[FILE path:line]` — origin attached at the moment of restatement.
- **Fixed scaffold section.** The disclosure template carries a facts list the agent fills before acting (not ad-hoc prose).
- **Drift is visible.** A fact that was `[USER]` must not become `[DRAFT]` silently; the tag makes the swap detectable.

*Tag every fact with where it came from — user, file, or draft — so the scaffold, not the model's memory, is the source.*

### LAQF.C4:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A fact carrying its origin can be checked against that origin; an untagged paraphrase can only be trusted or not.

**Show #1 (Claude Code session).** Disclosure under C4: `[USER] timeout = 30s` · `[FILE client.go:22] Redis already wired` · `[DRAFT] assume 5m TTL — confirm`. Twenty turns later the agent reuses `[USER] timeout = 30s` and cites the tag, not a drifted recollection. Without C4: the facts blur into one paraphrase, `30s` quietly becomes `60s`, and nothing flags the swap (S-014).

**Show #2 (journalism episteme).** A reporter's notes attribute every line — on-record, background, the reporter's own inference — so the desk can check the chain before print. C4 is attribution discipline for the agent's working notes: every fact attributed to user, file, or draft, which L17 calls structured note-taking that persists state outside the window.

### LAQF.C4:6 - Bias-Annotation

Lenses tested: **Onto/Epist**, **Arch**. Scope: fact restatement within a session.

- **Onto/Epist bias:** "a fact's authority is its origin, not its repetition" — the scaffold enforces the provenance chain (shared with A5/A6).
- **Arch bias:** favours an explicit external scaffold over implicit recall; risk is tagging overhead — bounded by tagging only load-bearing facts.

### LAQF.C4:7 - Conformance Checklist

1. **CC-C4-1 (Scaffold prescribed).** The disclosure template carries a fixed provenance-tagged facts section.
2. **CC-C4-2 (Origins tagged).** Load-bearing facts carry `[USER]` / `[DRAFT]` / `[FILE path:line]`.
3. **CC-C4-3 (Cite the tag).** Restatements reference the tagged fact, not a fresh paraphrase.
4. **CC-C4-4 (Detection wired).** Reads reconnaissance-depth s2: leading = `[USER]`/`[DRAFT]` ratio / scaffold presence; lagging = fabricated-fact / drift events.

### LAQF.C4:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Free-form restatement** | origins blur; drift undetectable (S-014) | prescribe the tagged scaffold |
| **Tag nothing / tag everything** | no signal / pure overhead | tag load-bearing facts only |
| **Re-paraphrase instead of citing the tag** | reintroduces the drift the scaffold prevents | cite the tagged fact, re-read on doubt (A5) |

### LAQF.C4:9 - Consequences

**Benefits.** Provenance is preserved; drift becomes visible and rare; reconnaissance-depth (s2) and downstream verification (E-layer) improve; A6's anchoring discipline gains a concrete realisation.

**Trade-offs.** Maintaining the scaffold is authoring overhead, and after compaction the tags must be re-supplied (B2); bounded by tagging only load-bearing facts and by re-reading the origin on doubt (A5).

### LAQF.C4:10 - Rationale

rc-16 is the config-side complement of rc-06: A6 mitigates the *no-working-memory Law* (anchor to origin), C4 *builds the scaffold* that anchoring needs. Both read s2. Keeping them distinct preserves each `EntityOfConcern` (`E.8:0.3`): A6 is the behaviour at restatement, C4 is the authored template that makes the behaviour cheap; it is the `MF-4` externalisation B2's handoff also relies on.

### LAQF.C4:11 - SoTA-Echoing

- **Claim:** state should live outside the window with structure. **Practice:** just-in-time identifier loading; structured note-taking persists state. **Source:** L17 (T5); MF-4. **Alignment:** the provenance-tagged scaffold is exactly externalised, structured state. **Status:** adopt.
- **Claim:** the model leans on its own generation absent an external anchor. **Practice:** sycophancy + no-working-memory amplify self-trust. **Source:** L19 (T4). **Alignment:** C4 redirects trust to the tagged origin. **Status:** adapt (mechanism, not metric).

### LAQF.C4:12 - Relations

- **Design cause (C:0):** the missing facts scaffold via [[../11-fpf-diagnostic]] D2 — transformed by prescribing it; MUST NOT read as giving the model working memory.
- **Measurement (R2):** reconnaissance-depth s2 ([[12-02-measurement-frame]] §2 card `laqf.mm.s2`).
- **Method family:** `MF-4` (state externalisation).
- **Coordinates with:** A6 (the Law-mitigation the scaffold realises); A5 (produces the `[FILE path:line]` reads); A7 (the disclosure block the scaffold lives in); B2 (re-supplies the tags after compaction).

### LAQF.C4:End

---

## LAQF.C5 - Deterministic Over Advisory

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** instruction-adherence (`12-02` s1)
> **Source mechanism:** rc-17 (advisory-only rules)

### LAQF.C5:0 - Use this when

Use this when deciding how a rule is enforced — for any discipline (brevity, reconnaissance, citation, commit hygiene) classify whether it *must* hold deterministically or is a judgement that should stay advisory, and place it on the matching surface.

**What goes wrong if missed.** Every rule is left as CLAUDE.md prose, but advisory instructions plateau around the adherence ceiling (L15 ≈70%); a prompt-level "don't" is not a forbid (ME-4 [L20]). A rule that must hold 100% of the time but lives only in prose fails ~30% of the time, silently (rc-17; S-003/005/008/011).

**What this buys.** Each rule sits on the surface that matches its nature: must-hold rules become deterministic hooks (`MF-1`) that fire every time; genuine judgement stays advisory (`MF-2`). Adherence on the hooked rules goes to 100%.

**Not this pattern when.** The rule is inherently a judgement (an engineering stance, a style preference) — hooking it would be brittle and wrong. C5 is the *classifier*; it deliberately does not hook everything.

### LAQF.C5:1 - Problem frame

The config encodes brevity, reconnaissance, citation, and hygiene rules as advisory prose. But advisory rules share the model's adherence ceiling — around 70% for CLAUDE.md guidance (L15) — and agentic-misalignment work shows a prompt-level instruction not to do something does not prevent it (ME-4 [L20]); only a deterministic gate (a hook) forbids. Past the attention budget the advisory is even weaker (G.2-F2). This is a Design cause (C:0): the enforcement surface is the user's to choose. The frame is to classify each rule and place it deterministically when it must hold.

### LAQF.C5:2 - Problem

How can the config make must-hold rules actually hold every time — when advisory prose plateaus at the adherence ceiling — without brittlely hooking rules that are genuinely matters of judgement?

### LAQF.C5:3 - Forces

| Force | Tension |
|---|---|
| Deterministic vs advisory | A hook that fires every time ↔ prose that plateaus ~70% (L15). |
| Must-hold vs judgement | A rule that must always hold ↔ a stance that needs discretion (C3). |
| Coverage vs brittleness | Hooking guarantees adherence ↔ over-hooking breaks on edge cases. |
| Design-able | The enforcement surface is the user's config to assign. |

### LAQF.C5:4 - Solution

**Classify by nature, then place on the matching surface.** For each rule decide: *must it hold deterministically?* → encode it as a hook (`MF-1` deterministic forbid: PreToolUse/PostToolUse/Stop); *is it a judgement?* → keep it advisory (`MF-2`, e.g. C3's posture). Do not hook everything — reserve `MF-1` for rules that genuinely must hold, where the adherence ceiling (L15) and the "prompt-level don't is not a forbid" finding (ME-4 [L20]) make advisory insufficient. C5 is the meta-pattern the deterministic C/E/F patterns instantiate: C7 (skill invocation), C6 (permission coverage), E1 (claim requires event), E2 (citation anchors), F2 (commit hygiene) are all `MF-1` placements C5 governs. The transformation is direct: the rule moves from prose to the surface its nature demands.

- **Classify first.** Must-hold-deterministically → hook; judgement → advisory. Decide explicitly per rule.
- **Hook the must-holds.** `MF-1` (PreToolUse/PostToolUse/Stop) for rules where ~70% (L15) is a failure.
- **Don't hook judgement.** A stance (C3) stays `MF-2`; hooking it is brittle and wrong.

*Put must-hold rules in hooks and judgement in advisories — a rule that has to hold cannot live in prose that holds 70% of the time.*

### LAQF.C5:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A rule that must hold belongs on a deterministic surface; prose enforces a tendency, a hook enforces a fact.

**Show #1 (Claude Code session).** "Never add Co-Authored-By trailers" lives only in CLAUDE.md. Under C5: it is classified must-hold and moved to a PreToolUse hook that strips the trailer from any `git commit` (F2 — an `MF-1` instance C5 governs); adherence on it goes to 100%. Without C5: it holds ~70% of the time (L15), and the trailer leaks on the turns the model does not attend the rule (S-026).

**Show #2 (safety-engineering episteme).** A safety-critical interlock is not a sign that says "please don't"; it is a physical gate that cannot be bypassed. Routine preferences stay as signage. C5 is the interlock-vs-signage decision for config: ME-4 [L20] is the evidence that, for an LLM, the sign alone ("don't") is not the interlock — the gate must be deterministic.

### LAQF.C5:6 - Bias-Annotation

Lenses tested: **Gov**, **Did**. Scope: per-rule enforcement-surface choice.

- **Gov bias:** the classify-and-place decision is an accountability record (which rules are hooked, which advisory, why); the hook log is the audit trail.
- **Did bias:** "must-hold → hook, judgement → advisory" is a single teachable classifier; the most common error (hook everything) is bounded by the explicit judgement carve-out.

### LAQF.C5:7 - Conformance Checklist

1. **CC-C5-1 (Classified).** Each rule is explicitly classified must-hold-deterministic vs judgement.
2. **CC-C5-2 (Must-holds hooked).** Must-hold rules are placed as `MF-1` hooks, not left as prose.
3. **CC-C5-3 (Judgement preserved).** Genuine judgement rules stay advisory; not everything is hooked.
4. **CC-C5-4 (Detection wired).** Reads instruction-adherence s1: leading = PreToolUse near-miss / hook-fire count; lagging = stated-rule-violated events surfacing in review.

### LAQF.C5:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Leave a must-hold rule as prose** | plateaus ~70% (L15); "don't" ≠ forbid (ME-4) | classify must-hold → hook (MF-1) |
| **Hook everything** | brittle gates on judgement calls | reserve hooks for genuine must-holds |
| **Assume the prompt-level "don't" suffices** | ME-4 [L20] shows it does not | place a deterministic gate |

### LAQF.C5:9 - Consequences

**Benefits.** Must-hold rules hit 100% adherence; the advisory ceiling stops being the limit on rules that cannot afford it; instruction-adherence (s1) rises into the green band; C6/C7/E1/E2/F2 inherit a principled enforcement surface.

**Trade-offs.** Hooks are code that must be maintained and can be brittle on edge cases; over-hooking degrades flexibility. Bounded by the judgement carve-out (keep stance advisory) and by hooking only rules where ~70% is a real failure.

### LAQF.C5:10 - Rationale

rc-17 is the meta-cause of the design-space enforcement gap: it is *why* C6, C7, E1, E2, and F2 exist as deterministic patterns rather than more advisory prose. C5 owns the classification; the others own their specific `MF-1` placements. Concentrating the deterministic-vs-advisory decision in one pattern keeps each downstream pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) and gives B3's conflict-resolved rules a clear next step.

### LAQF.C5:11 - SoTA-Echoing

- **Claim:** advisory rules plateau at an adherence ceiling. **Practice:** CLAUDE.md guidance ≈70% advisory adherence; IFScale 68% at 500. **Source:** L15, G.2-F2 (T3). **Alignment:** C5 moves must-hold rules off the advisory ceiling onto deterministic hooks. **Status:** adopt.
- **Claim:** a prompt-level "don't" is not a forbid. **Practice:** agentic-misalignment work shows direct commands disobeyed; only deterministic gates prevent. **Source:** ME-4 [L20]. **Alignment:** C5's must-hold → hook rule is exactly the deterministic-gate response. **Status:** adopt.

### LAQF.C5:12 - Relations

- **Design cause (C:0):** advisory-only enforcement via [[../11-fpf-diagnostic]] D2 — transformed by placing must-holds on `MF-1`; MUST NOT read as "hook everything".
- **Measurement (R2):** instruction-adherence s1 ([[12-02-measurement-frame]] §2 card `laqf.mm.s1`); ceiling per Γ_epist G.2-F2.
- **Method family:** the `MF-1` (deterministic) vs `MF-2` (advisory) classifier itself.
- **Coordinates with:** C7 / C6 / E1 / E2 / F2 (the `MF-1` placements C5 governs); C3 (the advisory stance C5 keeps `MF-2`); B3 (supplies conflict-resolved rules to classify).

### LAQF.C5:End

---

## LAQF.C6 - Whole-Path Permission Coverage

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** instruction-adherence (`12-02` s1, *nearest*)
> **Source mechanism:** rc-18 (permission allowlist drift)

### LAQF.C6:0 - Use this when

Use this when maintaining the permission allowlist (the auto-approve surface) — deciding which tool calls along a routine workflow are pre-approved, so the agent runs the whole expected path without an approval prompt at every step, while destructive operations stay gated.

**What goes wrong if missed.** The allowlist covers some steps of a routine path but not others, so the agent stalls for approval mid-flow — approval fatigue (rc-18; S-002/031) that trains the user to rubber-stamp prompts, eroding the value of the gate for the operations that *should* stop.

**What this buys.** The allowlist covers the *whole* routine path so it runs uninterrupted, with destructive operations deliberately left off it. Approval prompts become rare and meaningful again.

**Not this pattern when.** The operation is genuinely destructive or irreversible — those must stay off the allowlist (the global protocol's enumerated stop conditions). C6 widens coverage of the *safe* routine path, never the destructive one.

### LAQF.C6:1 - Problem frame

The auto-approve config covers part of a common workflow but misses steps, so a routine task is punctuated by approval prompts for operations the user always approves. Each needless prompt is friction that erodes attention to the prompts that matter; the user starts approving reflexively, which defeats the gate for genuinely risky calls. Telemetry can show where the prompts fire (L22). This is a Design cause (C:0): the allowlist is the user's to complete. The frame is to cover the whole safe path and keep destructive ops gated.

*Detection note:* the nearest-fit characteristic is instruction-adherence s1 (the allowlist is the deterministic rule surface), retained per [[12-02-measurement-frame]] §5; the operational signal is auto-approve coverage and prompt frequency.

### LAQF.C6:2 - Problem

How can the permission allowlist let a routine workflow run end-to-end without needless approval prompts — restoring the meaning of the prompts that remain — while keeping every destructive operation off the auto-approve surface?

### LAQF.C6:3 - Forces

| Force | Tension |
|---|---|
| Coverage vs safety | A path that runs uninterrupted ↔ destructive ops that must always stop. |
| Fewer prompts vs vigilance | Less approval fatigue ↔ keeping the gate meaningful (rc-18). |
| Whole-path vs per-step | Pre-approving the routine flow ↔ approving each step ad hoc. |
| Design-able | The allowlist is the user's config to complete. |

### LAQF.C6:4 - Solution

Cover the **whole routine path** in the allowlist; keep destructive operations off it. Enumerate the safe steps of each common workflow and pre-approve them as a set so the path runs uninterrupted (`MF-1` deterministic auto-approve, governed by C5); leave irreversible/destructive operations gated (the global stop conditions). Mine the transcript / telemetry (L22) for the operations that repeatedly trigger needless prompts, and add those safe ones to the allowlist. C6 is an `MF-1` placement under C5, paired with C7 (skill invocation) and D4 (role lanes) as the deterministic permission surface. The transformation is direct: the allowlist is completed to match the real safe path.

- **Cover the whole safe path.** Pre-approve the routine workflow as a set, not step-by-step.
- **Keep destructive ops gated.** Irreversible operations never go on the auto-approve surface.
- **Mine prompts to close gaps.** Use telemetry (L22) to find the safe operations that keep prompting and add them.

*Pre-approve the whole safe path so prompts are rare — and keep every destructive operation off the allowlist so the prompts that remain mean something.*

### LAQF.C6:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** An allowlist that covers the whole safe path makes the remaining prompts meaningful; a patchy one trains the user to rubber-stamp.

**Show #1 (Claude Code session).** A routine "edit, run tests, commit" flow prompts for the test run because only edit and commit are allowlisted. Under C6: the safe test command joins the allowlist (mined from the transcript via L22), the flow runs uninterrupted, and the next prompt — a `git push` — actually gets read. Without C6: the user approves the test prompt reflexively and approves the push the same way (S-002/031).

**Show #2 (alarm-fatigue episteme).** A monitor that alarms on every benign fluctuation trains staff to silence alarms, so the critical one is silenced too; the fix is to tune out the benign and keep the critical loud. C6 is alarm-tuning for permissions — pre-approve the benign whole path, keep the destructive alarm loud — and L22 telemetry is the tuning instrument.

### LAQF.C6:6 - Bias-Annotation

Lenses tested: **Gov**, **Prag**. Scope: permission-allowlist authoring.

- **Gov bias:** the safe/destructive split is a security-accountability boundary; the allowlist is auditable (what is auto-approved, what stays gated) — shared lane discipline with D4.
- **Prag bias:** optimises for uninterrupted routine flow; risk is widening coverage onto a borderline-risky op — bounded by the categorical destructive carve-out.

### LAQF.C6:7 - Conformance Checklist

1. **CC-C6-1 (Whole safe path).** Routine workflows are pre-approved as a set, not step-by-step.
2. **CC-C6-2 (Destructive gated).** Irreversible/destructive operations are kept off the allowlist.
3. **CC-C6-3 (Gap mining).** Needless-prompt operations are mined from telemetry (L22) and the safe ones added.
4. **CC-C6-4 (Detection wired).** Reads instruction-adherence s1 (*nearest*): leading = auto-approve coverage / prompt frequency; lagging = approval-fatigue rubber-stamping of risky calls.

### LAQF.C6:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Patchy coverage** | mid-flow prompts breed approval fatigue (rc-18) | cover the whole safe path as a set |
| **Allowlist a destructive op to stop prompts** | removes the gate that must stop | keep destructive ops categorically gated |
| **Guess the gaps** | misses the real friction points | mine the transcript/telemetry (L22) |

### LAQF.C6:9 - Consequences

**Benefits.** Routine flows run uninterrupted; approval prompts become rare and meaningful; the user's vigilance is preserved for genuinely risky calls; instruction-adherence (s1, nearest) on the permission surface improves.

**Trade-offs.** A widened allowlist is a larger trusted surface that must be audited, and a mis-classified op could be auto-approved; bounded by the categorical destructive carve-out and by telemetry-driven, not speculative, additions.

### LAQF.C6:10 - Rationale

rc-18 is an `MF-1` permission instance of the C5 meta-pattern: the allowlist is a deterministic gate, and the defect is *under-coverage of the safe path*, not over-coverage. Framing C6 as whole-path coverage (with destructive ops categorically excluded) keeps it a single move distinct from C7 (skill-invocation gate) and D4 (role lanes), each a different `MF-1` surface under C5 (`E.8:0.3`).

### LAQF.C6:11 - SoTA-Echoing

- **Claim:** deterministic gates, not advisory prose, enforce permission rules. **Practice:** CLAUDE.md advisory ≈70%; hooks/allowlist enforce deterministically. **Source:** L15 (T3). **Alignment:** C6 completes the deterministic auto-approve surface rather than relying on advisory judgement. **Status:** adopt.
- **Claim:** tool-call telemetry makes the friction observable. **Practice:** OpenTelemetry over tool-call history surfaces repeated prompts. **Source:** L22 (T5). **Alignment:** C6 mines telemetry to find the coverage gaps. **Status:** adopt.

### LAQF.C6:12 - Relations

- **Design cause (C:0):** permission allowlist drift via [[../11-fpf-diagnostic]] D2 — transformed by completing safe-path coverage; MUST NOT read as auto-approving destructive operations.
- **Measurement (R2):** instruction-adherence s1 *(nearest)* ([[12-02-measurement-frame]] §2 card `laqf.mm.s1`; nearest-fit retained §5).
- **Method family:** `MF-1` (deterministic auto-approve), an instance under C5.
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); C7 (the skill-invocation gate); D4 (per-agent tool/scope lanes).

### LAQF.C6:End

---

## LAQF.C7 - Enforced Skill Invocation

> **Type:** Principle pattern (P) — LAQF Layer-C
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see C:0)
> **FPF kind:** Design (user config) — transform via Work (direct)
> **Detection characteristic:** instruction-adherence (`12-02` s1)
> **Source mechanism:** rc-19 (skill invocation advisory)

### LAQF.C7:0 - Use this when

Use this when a skill is supposed to fire on a trigger (a matching task, file type, or keyword) but invoking it is left to the model's discretion — and you need the skill to actually run rather than be bypassed in favour of the model patching code or answering directly.

**What goes wrong if missed.** Skill invocation is advisory, so the model can skip the skill and act directly — patching code without the mandated workflow, answering without the prescribed procedure (rc-19; S-028). A "you should invoke skill X" instruction is a prompt-level "don't-skip" and, like any advisory, is not a forbid (ME-4 [L20]; L15).

**What this buys.** A PreToolUse trigger-match hook that blocks the bypass: when the trigger condition holds, the matching skill must run before the agent may take the alternative action. Invocation becomes deterministic.

**Not this pattern when.** The skill is genuinely optional / discretionary. C7 enforces *mandatory* skills; an optional skill stays advisory (a C5 judgement-side classification).

### LAQF.C7:1 - Problem frame

The config defines skills meant to fire on specific triggers, but the model decides whether to invoke them. Because invocation is advisory it shares the adherence ceiling (L15 ≈70%) and the agentic-misalignment finding that a prompt-level instruction does not deterministically constrain behaviour (ME-4 [L20]) — so on some turns the model bypasses the skill and patches directly. This is a Design cause (C:0): the invocation surface is the user's to gate. The frame is to make a mandatory skill's invocation deterministic via a trigger-match hook.

### LAQF.C7:2 - Problem

How can a mandatory skill be guaranteed to fire when its trigger condition holds — rather than being bypassed by the model acting directly — when invocation is currently advisory and advisories do not forbid?

### LAQF.C7:3 - Forces

| Force | Tension |
|---|---|
| Enforced vs advisory invocation | A hook that blocks bypass ↔ discretion that plateaus ~70% (L15). |
| Mandatory vs optional | A skill that must fire ↔ one that is genuinely discretionary (C5). |
| Gate vs flexibility | Guaranteed invocation ↔ a brittle block on edge cases. |
| Design-able | The invocation surface is the user's config to gate. |

### LAQF.C7:4 - Solution

Gate mandatory skills with a **PreToolUse trigger-match hook**. When the trigger condition holds (task class, file type, keyword), the hook blocks the alternative action (e.g. a direct Edit) until the matching skill has run (`MF-1` deterministic forbid). This is a specific `MF-1` instance of C5: C7 applies the deterministic-over-advisory ruling to skill invocation, exactly as C6 applies it to permissions and F2 to commit hygiene. Reserve enforcement for genuinely mandatory skills; optional ones stay advisory (a C5 judgement classification). The transformation is direct: invocation moves from the model's discretion to a deterministic gate.

- **Trigger-match hook.** A PreToolUse hook fires the mandatory skill when its trigger holds.
- **Block the bypass.** The alternative action (direct Edit/answer) is blocked until the skill has run.
- **Mandatory only.** Enforce skills that must fire; leave discretionary skills advisory (C5).

*Make a mandatory skill's invocation a gate, not a suggestion — an advisory "invoke X" is bypassed exactly when it matters.*

### LAQF.C7:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A mandatory skill behind a trigger-match hook always fires; an advisory one fires only when the model chooses to attend it.

**Show #1 (Claude Code session).** A project mandates the agent-pipeline skill for any `.go` edit. Under C7: a PreToolUse hook detects the `.go` Edit, finds the pipeline skill not yet run, and blocks the Edit until it is — the workflow cannot be skipped. Without C7: on a busy turn the model patches the `.go` file directly, bypassing the mandated pipeline (S-028), and the advisory "always use the pipeline" held only ~70% of the time (L15).

**Show #2 (process-control episteme).** A manufacturing line with a mandatory QA station puts a physical gate before the next stage: the part cannot advance until QA stamps it. A sign reading "please run QA" would be skipped under deadline pressure. C7 is the QA gate for mandatory skills; ME-4 [L20] is the evidence that, for an LLM, the sign alone is skipped exactly under pressure.

### LAQF.C7:6 - Bias-Annotation

Lenses tested: **Gov**, **Did**. Scope: mandatory-skill invocation.

- **Gov bias:** the trigger-match gate is an accountability control (the mandatory skill provably ran); the hook log is the audit trail, shared with C5/C6.
- **Did bias:** "mandatory skill → trigger-match hook" is a single teachable placement; the carve-out (optional skills stay advisory) prevents over-gating.

### LAQF.C7:7 - Conformance Checklist

1. **CC-C7-1 (Trigger-match gate).** Mandatory skills fire via a PreToolUse trigger-match hook.
2. **CC-C7-2 (Bypass blocked).** The alternative action is blocked until the mandatory skill has run.
3. **CC-C7-3 (Mandatory scope).** Only genuinely mandatory skills are gated; optional ones stay advisory (C5).
4. **CC-C7-4 (Detection wired).** Reads instruction-adherence s1: leading = trigger-fire / bypass-blocked count; lagging = mandated-skill-skipped events surfacing in review.

### LAQF.C7:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Advisory "always invoke X"** | bypassed under pressure (ME-4; ~70%, L15) | gate with a PreToolUse trigger-match hook |
| **Gate every skill** | brittle blocks on discretionary skills | enforce mandatory only; optional stay advisory |
| **Trigger too broad** | blocks legitimate direct actions | scope the trigger to the genuine mandatory case |

### LAQF.C7:9 - Consequences

**Benefits.** Mandatory skills always fire; the mandated workflow cannot be silently bypassed; instruction-adherence (s1) on skill invocation reaches the green band; the pipeline disciplines (D-layer) gain a reliable entry gate.

**Trade-offs.** The hook is code to maintain and an over-broad trigger blocks legitimate direct actions; bounded by enforcing only genuinely mandatory skills and scoping the trigger tightly.

### LAQF.C7:10 - Rationale

rc-19 is the skill-invocation `MF-1` instance of the C5 meta-pattern, alongside C6 (permissions) and F2 (commit hygiene). C7 owns one specific placement — the trigger-match gate on mandatory skills — leaving C5 to own the deterministic-vs-advisory classification. This split keeps each pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) and makes C7's "block the bypass" mechanism reusable wherever a mandatory procedure must precede an action.

### LAQF.C7:11 - SoTA-Echoing

- **Claim:** advisory invocation plateaus at the adherence ceiling. **Practice:** CLAUDE.md guidance ≈70% advisory adherence. **Source:** L15 (T3). **Alignment:** C7 moves mandatory-skill invocation off the advisory ceiling onto a deterministic gate. **Status:** adopt.
- **Claim:** a prompt-level instruction is not a forbid. **Practice:** agentic-misalignment work — direct commands disobeyed; only deterministic gates prevent. **Source:** ME-4 [L20]. **Alignment:** C7's trigger-match hook is exactly the deterministic gate for invocation. **Status:** adopt.

### LAQF.C7:12 - Relations

- **Design cause (C:0):** advisory skill invocation via [[../11-fpf-diagnostic]] D2 — transformed by a trigger-match gate; MUST NOT read as gating discretionary skills.
- **Measurement (R2):** instruction-adherence s1 ([[12-02-measurement-frame]] §2 card `laqf.mm.s1`).
- **Method family:** `MF-1` (deterministic forbid), an instance under C5.
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); C6 (the permission-coverage gate); D4 (role lanes); E1 (Claim Requires Observed Event — the verification-side gate).

### LAQF.C7:End

---

## See also

- [[12-12-patterns-C-ru]] — Russian twin
- [[12-10-patterns-A]] — frozen house-style exemplar (the 13-section template C1–C7 reuse)
- [[12-11-patterns-B]] — Layer-B (Boundary) patterns; B3 measures the load C1/C2 act on
- [[12-00-spine]] — keystone: §5 roster (Design kind + detection), §4.3 relation records, §4.1 edition direction
- [[12-01-source-pack]] — G.2 pack; §8 palette `LAQF.sota.iter3.palette` cited by every §11 (L-/ME-/MF-/Γ_epist ids)
- [[12-02-measurement-frame]] — detection axes (§5 pattern↔characteristic; §2 DHCMethod cards; §3 CAL bands; §4 leading/lagging)
- [[_inputs/rc-digest]] — §3 Layer-C mechanisms (rc-13…rc-19)
- [[../11-fpf-diagnostic]] — D2 design-space ruling (the basis for the C:0 design contract)
- `FPF-Spec.md:65183` E.8 authoring conventions · `:65272` canonical template · `:24417` A.19 · `:42826` C.16 · `:87746` G.2
