---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, patterns, layer-e, e8-patterns]
seminar-iteration: 3
created: 2026-06-28
status: patterns-layer-e
method: FPF E.8 (authoring conventions) · 11-fpf-diagnostic D2 (Design-space / Work quadrant) · consumes 12-01 palette LAQF.sota.iter3.palette + 12-02 detection axes
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-14-patterns-E-ru]]"
---

# LAQF — Layer E patterns (output integrity / verification): E1–E5

The five **Layer-E** patterns of LAQF. Each addresses a property of the agent's *verification surface* — the gate between the model emitting a claim and that claim reaching the user: whether a "build passed" is backed by an observed run, whether a citation resolves, whether an assertion was audited against counter-evidence, whether a multi-item output keeps its input order, whether the toolchain floods the window. In FPF terms each is a **Design** cause ([[../11-fpf-diagnostic]] D2 design-space): not a model-internal Law to mitigate (Layer A), nor someone else's harness boundary to adapt around (Layer B), but *the user's own verification surface* — transformable outright by direct Work.

These patterns reuse the house style frozen in [[12-10-patterns-A]] (the full `E.8` thirteen-section template, `FPF-Spec.md:65272`). Each cites the SoTA pack by id ([[12-01-source-pack]] §8 palette `LAQF.sota.iter3.palette`) and wires its detection slot to one `A.19` characteristic ([[12-02-measurement-frame]] §5). They assert no new evidence and re-paraphrase no source — an id, never a quote (`G.2:4.2`, `FPF-Spec.md:87904`).

## E:0 - The Layer-E design contract (read once, applies to E1–E5)

Stated here once so each Solution need not repeat it (`E.8:0.3` anti-repetition, `FPF-Spec.md:65234`). Layer E shares the Design quadrant with Layer C, so this contract **inherits the Layer-C design contract** ([[12-12-patterns-C]] C:0) rather than restating it, specialising it to the verification surface under the same [[../11-fpf-diagnostic]] D2 design-space ruling (D–F are all Design / direct-Work):

- **The cause is the user-owned verification surface — neither a Law nor a harness boundary.** Each E-pattern names a missing gate between claim and delivery (an unrun test claimed as passing, an unresolved citation, an unaudited assertion, a reordered list, a flood of tool output). Like Layer C, this surface is the user's to author.
- **Direct Work, no hedge** (inherited from C:0). An E-pattern's Solution *adds the gate*: it checks the claim against the tool-call history, requires the citation to resolve, audits for counter-evidence, verifies the order, quiets the toolchain. There is no "mitigate-only" caveat — the gate can be made to hold.
- **Layer-1 states *what*; Layer-2 (S6) realises *how*** (inherited from C:0). This Domain edition states the verification property; the Local Practice edition (the user's actual Stop / SubagentStop / PreToolUse hooks, output-shape rules) is the realisation.
- **Prefer deterministic over advisory where a rule must hold** (inherited from C:0 → C5). A checkable claim — build/test passed (E1), a citation resolves (E2), an order matches (E4), tool output is quiet (E5) — belongs in a hook (`MF-1`/`MF-6`); a genuine judgement audit (E3, where no mechanical check exists) stays advisory (`MF-2`). C5 owns the classification; E-patterns inherit the preference and point to C5.
- **Detection is behavioural.** Each pattern's success is observed through one of the eight `A.19` characteristics ([[12-02-measurement-frame]] §1), read at the **leading** (mid-session) indicator, not only the lagging outcome (§4 of the frame). Layer E reads mostly verification-fidelity (s6), with output-economy (s5) for the toolchain flood.

---

## LAQF.E1 - Claim Requires Observed Event

> **Type:** Principle pattern (P) — LAQF Layer-E
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see E:0)
> **FPF kind:** Design (verification surface) — transform via Work (direct)
> **Detection characteristic:** verification-fidelity (`12-02` s6)
> **Source mechanism:** rc-24 (done-without-verification)

### LAQF.E1:0 - Use this when

Use this when the agent reports a terminal result — "the build passes", "tests are green", "the lint is clean" — and you need that report to be backed by an actually-executed run rather than asserted from the model's expectation of what the run would show.

**What goes wrong if missed.** The agent claims the build or tests passed without running them; nothing checks the claim against the tool-call history (rc-24; S-027). The model's gradient toward a finished artefact (A2's Law) makes "it passes" the natural close, and a prompt-level "always verify" is a don't, which is not a forbid (ME-4 [L20]).

**What this buys.** A Stop / SubagentStop hook that gates the terminal claim on an observed event: when the agent asserts a result, the hook checks the tool-call history for the corresponding run and blocks the claim if the run is absent. "It passes" can only be said after it was observed to pass.

**Not this pattern when.** The statement is an explicit plan or intention ("I will now run the tests"), not a claim of completed fact. E1 gates *result claims*; E2 (Enforced Citation Anchors) gates *reference* claims, and E3 (Counter-Evidence Audit) handles judgement claims with no mechanical check.

### LAQF.E1:1 - Problem frame

The agent is pulled toward a clean close — the turn-output gradient rewards a finished, passing artefact (rc-02 / A2) — so "the build passes" is emitted because it *should* pass, not because it was seen to. The harness records every tool call, so the evidence for or against the claim already exists; what is missing is a gate that consults it. Agentic-misalignment work is explicit that a prompt-level instruction to verify is disobeyed under pressure (ME-4 [L20]); only a deterministic gate prevents the unbacked claim. This is a Design cause (E:0): the gate is the user's to author. The frame is to require an observed event behind every result claim.

### LAQF.E1:2 - Problem

How can a terminal result claim ("build/tests passed") be admitted only when the corresponding run is present in the tool-call history — so the agent cannot report a result it never observed?

### LAQF.E1:3 - Forces

| Force | Tension |
|---|---|
| Observed vs asserted result | A claim backed by a run ↔ a claim from expectation (A2 gradient). |
| Gate vs advisory | A Stop hook that checks history ↔ a prompt-level "always verify" (ME-4). |
| Strictness vs flow | Blocking an unbacked claim ↔ a false block on a genuinely-run result. |
| Design-able | The verification gate is the user's surface; it is authored, not adapted-around. |

### LAQF.E1:4 - Solution

Gate terminal result claims on an **observed tool event**. Author a Stop / SubagentStop hook that, when the agent asserts a result (build/test/lint pass), scans the tool-call history for the matching run and blocks the claim if no such run is present (`MF-1` deterministic forbid, [[12-01-source-pack]] §6). The claim becomes admissible only behind evidence the harness already records. This is a specific `MF-1` instance of the C5 ruling — the verification-side sibling of C7 (skill invocation), C6 (permissions) and F2 (commit hygiene). Reserve the gate for *result claims*; an explicit intention is not a claim. The transformation is direct: the surface gains the check that consults the history.

- **Result claim ⟶ history check.** A Stop hook matches the asserted result against an executed run.
- **No run, no claim.** An unbacked result claim is blocked, not delivered.
- **Claims only, not intentions.** "I will run X" is an intention; the gate fires on "X passed".

*Let "it passes" be sayable only after it was observed to pass — gate the claim on the run, do not trust the expectation.*

### LAQF.E1:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A result claim gated on an observed run is true by construction; a result asserted from expectation is right only when the expectation happens to hold.

**Show #1 (Claude Code session).** The agent edits code and writes "all tests pass". Under E1: the Stop hook scans the turn's tool calls, finds no test run after the last edit, and blocks the close until the tests are actually executed — the green claim cannot precede the green run. Without E1: the agent reports passing tests it never ran, the user merges on the strength of it, and the failure surfaces in CI (S-027).

**Show #2 (aviation episteme).** A pre-flight checklist is not read from memory of a normal aircraft — each item is physically confirmed and called, because "the gear is down" asserted from expectation has killed people. E1 is the checklist discipline for agent claims: the result is *confirmed against the instrument* (the tool-call history), and ME-4 [L20] is the evidence that, for an LLM, the from-memory assertion is exactly what slips under pressure.

### LAQF.E1:6 - Bias-Annotation

Lenses tested: **Gov**, **Did**. Scope: terminal result claims.

- **Gov bias:** the claim-vs-history check is an accountability gate (the result provably ran); the hook log is the audit trail, shared with E2 and the C5/C6/C7 controls.
- **Did bias:** "result claim → observed-event check" is a single teachable gate; the carve-out (intentions are not claims) prevents over-blocking ordinary planning language.

### LAQF.E1:7 - Conformance Checklist

1. **CC-E1-1 (Claim gated).** A terminal result claim fires a Stop / SubagentStop check against the tool-call history.
2. **CC-E1-2 (No run, no claim).** A result claim with no matching executed run is blocked.
3. **CC-E1-3 (Claims, not intentions).** The gate fires on completed-result claims, not on stated intentions to run.
4. **CC-E1-4 (Detection wired).** Reads verification-fidelity s6: leading = claim-emitted-without-prior-tool-event flag; lagging = false "build/test passed" reaching the user (§4 frame).

### LAQF.E1:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Say "it passes" from expectation** | the run was never observed (A2 gradient) | gate the claim on a matching run in history |
| **Advisory "always verify"** | a prompt-level don't is not a forbid (ME-4) | enforce a Stop / SubagentStop check (`MF-1`) |
| **Block stated intentions too** | over-blocks ordinary planning language | fire only on completed-result claims |

### LAQF.E1:9 - Consequences

**Benefits.** Result claims become true by construction; false "it passes" stops reaching the user; verification-fidelity (s6) reaches the green band; the downstream stages that trust the claim (CI, review) gain a reliable gate.

**Trade-offs.** The Stop hook is code to maintain and a mis-scoped matcher can false-block a genuinely-run result; bounded by matching the claim to the specific run and firing only on completed-result claims, not intentions.

### LAQF.E1:10 - Rationale

rc-24 is the verification-side `MF-1` instance of the C5 meta-pattern: the same "advisory does not forbid; gate it" move, applied to the terminal claim. E1 owns one placement — the result-claim-vs-history check — leaving C5 to own the classification and E2 to own reference claims. The leverage is that the harness *already records* the evidence; the pattern is a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) that consults it, which is why E1 is the cheapest of the E-gates to realise.

### LAQF.E1:11 - SoTA-Echoing

- **Claim:** a prompt-level instruction to verify is disobeyed under pressure; only a deterministic gate prevents it. **Practice:** agentic-misalignment — models disobey direct commands; hook-level forbid mandatory. **Source:** ME-4 [L20]. **Alignment:** E1's Stop check is exactly that deterministic gate for result claims. **Status:** adopt.
- **Claim:** a harness-enforced gate is what makes a procedure hold across turns. **Practice:** Plan Mode / approval gates as harness-enforced, not advisory. **Source:** L16 (T1+T5). **Alignment:** E1 makes the verify-before-claim step harness-enforced rather than advisory. **Status:** adapt (L16 gates plan→execute; E1 gates claim→delivery).

### LAQF.E1:12 - Relations

- **Design cause (E:0):** the missing result-verification gate via [[../11-fpf-diagnostic]] D2 — transformed by a Stop-hook history check; MUST NOT read as blocking stated intentions.
- **Measurement (R2):** verification-fidelity s6 ([[12-02-measurement-frame]] §2 card `laqf.mm.s6`).
- **Method family:** `MF-1` (deterministic forbid — Stop / SubagentStop quality gate), an instance under C5.
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); E2 (the reference-claim sibling); E3 (judgement claims with no mechanical check); A2 (the Law-gradient toward a clean close that E1 gates).

### LAQF.E1:End

---

## LAQF.E2 - Enforced Citation Anchors

> **Type:** Principle pattern (P) — LAQF Layer-E
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see E:0)
> **FPF kind:** Design (verification surface) — transform via Work (direct)
> **Detection characteristic:** verification-fidelity (`12-02` s6)
> **Source mechanism:** rc-25 (citation not enforced)

### LAQF.E2:0 - Use this when

Use this when the agent refers to a source by a bare token — "see d32", "per the earlier doc", "[L05]" — and you need each such reference to resolve to a checkable anchor (a path, a line, a quote) rather than gesturing at a source the reader cannot follow.

**What goes wrong if missed.** A bare "see d32" with no path or quote slips through; nothing flags the unresolved reference (rc-25; S-003, S-008). The reader cannot verify the citation, and because the model has no persistent working memory (rc-06 / A6) the bare token may point at a source it has half-fabricated. An advisory "always cite properly" plateaus at the adherence ceiling (≈70%, L15).

**What this buys.** A Stop hook that scans the turn for reference tokens and requires each to resolve — a path/line or a quoted anchor — blocking completion on an unresolved reference. A citation either resolves or does not ship.

**Not this pattern when.** The text makes no source claim (pure reasoning, the agent's own proposal). E2 enforces *references to sources*; E1 (Claim Requires Observed Event) gates *result* claims, and A6 (User-Anchored Facts) is the Law-side discipline that keeps the cited fact anchored to the user/file rather than the model's draft.

### LAQF.E2:1 - Problem frame

The agent cites because citing signals rigour, but a bare token costs nothing to emit and everything to verify — and with no working memory the token may resolve to a source the model only thinks it remembers (A6). The harness can scan the emitted text for reference shapes and demand each resolve, but nothing does so by default, and the prompt-level "cite with a path/quote" sits on the advisory ceiling (L15 ≈70%). This is a Design cause (E:0): the citation gate is the user's to author. The frame is to require every reference token to resolve to a checkable anchor before the turn completes.

### LAQF.E2:2 - Problem

How can every source reference in a turn be required to resolve to a checkable anchor (path/line/quote) — so a bare, unverifiable, or half-fabricated citation cannot reach the reader?

### LAQF.E2:3 - Forces

| Force | Tension |
|---|---|
| Resolvable vs bare reference | A path/line/quote anchor ↔ a bare "see d32" token. |
| Gate vs advisory | A Stop hook that requires resolution ↔ "cite properly" at ~70% (L15). |
| Strictness vs flow | Blocking an unresolved reference ↔ a false block on a valid informal aside. |
| Design-able | The citation gate is the user's surface; it is authored, not adapted-around. |

### LAQF.E2:4 - Solution

Require every reference token to **resolve to a checkable anchor**. Author a Stop hook that scans the turn for reference shapes (a "see X", a bracketed id, a doc pointer) and requires each to carry a resolvable anchor — a path/line or a verbatim quote — blocking completion on any that does not resolve (`MF-1` deterministic forbid, [[12-01-source-pack]] §6). This is a specific `MF-1` instance of the C5 ruling, the reference-claim sibling of E1's result gate. It is the assurance complement of A6: A6 keeps the cited fact anchored to the user/file at emission, E2 verifies at the boundary that the anchor actually resolves. Reserve it for source references, not for the agent's own reasoning. The transformation is direct: the surface gains the resolve-or-block check.

- **Reference ⟶ resolvable anchor.** Each source token must carry a path/line or a verbatim quote.
- **Unresolved ⟶ blocked.** A reference that does not resolve blocks the turn's completion.
- **References, not reasoning.** The gate fires on source citations, not the agent's own proposals.

*Make every "see X" carry a checkable anchor — a citation either resolves to a path or quote, or it does not ship.*

### LAQF.E2:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A reference that must resolve to a path or quote is verifiable by construction; a bare token is an unfalsifiable gesture the reader cannot check.

**Show #1 (Claude Code session).** A review summary says "this violates the rule in d32". Under E2: the Stop hook finds the bare "d32" token, demands it resolve to a file/line or a quoted rule, and blocks the close until it does — the citation becomes `docs/rules.md:42` with the quoted clause. Without E2: "see d32" ships, the reader cannot find d32, and the cited rule turns out to be misremembered (S-003, S-008).

**Show #2 (scholarly-citation episteme).** A journal's reference-integrity check rejects a manuscript whose in-text citation has no resolvable entry in the bibliography; a documentation CI's broken-link checker fails the build on a dead anchor. E2 is that integrity check for agent output — every reference must resolve — and A6 is the reason it is needed: without working memory, the model's bare token is exactly the citation most likely to be fabricated.

### LAQF.E2:6 - Bias-Annotation

Lenses tested: **Gov**, **Did**. Scope: source-reference tokens.

- **Gov bias:** the resolve-or-block check is an accountability gate (every citation provably resolves); the hook log is the audit trail, shared with E1.
- **Did bias:** "reference token → must resolve to an anchor" is a single teachable gate; the carve-out (the agent's own reasoning is not a citation) prevents over-blocking informal text.

### LAQF.E2:7 - Conformance Checklist

1. **CC-E2-1 (Anchor required).** Each source reference carries a resolvable anchor — a path/line or a verbatim quote.
2. **CC-E2-2 (Unresolved blocked).** A reference token that does not resolve blocks the turn's completion (`MF-1`).
3. **CC-E2-3 (References, not reasoning).** The gate fires on source citations, not on the agent's own proposals.
4. **CC-E2-4 (Detection wired).** Reads verification-fidelity s6: leading = unresolved-reference token count in the turn; lagging = unverifiable citations surfacing in review.

### LAQF.E2:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Emit a bare "see d32"** | the reader cannot verify it; may be fabricated (A6) | require a path/line or verbatim quote anchor |
| **Advisory "cite properly"** | plateaus at the adherence ceiling (~70%, L15) | enforce a Stop-hook resolve-or-block check |
| **Treat reasoning as a citation** | over-blocks the agent's own proposals | fire only on references to external sources |

### LAQF.E2:9 - Consequences

**Benefits.** Every citation resolves to something checkable; bare and fabricated references stop reaching the reader; verification-fidelity (s6) on references reaches the green band; A6's emission-time anchoring gains a boundary-time check.

**Trade-offs.** The scanner is code to maintain and a loose reference-shape matcher can false-block an informal aside; bounded by scoping the match to genuine source references and firing only on unresolved anchors.

### LAQF.E2:10 - Rationale

rc-25 is the reference-claim `MF-1` instance of the C5 meta-pattern, alongside E1 (result claims), C6/C7 and F2. E2 owns one placement — the resolve-or-block scan on reference tokens — leaving C5 to own the classification and A6 to own the emission-time discipline. Splitting A6 (anchor the fact as you write it) from E2 (verify the anchor resolves at the boundary) keeps each pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) and gives the no-working-memory failure both a write-side and a check-side guard.

### LAQF.E2:11 - SoTA-Echoing

- **Claim:** advisory rules plateau at the adherence ceiling; only deterministic gates forbid. **Practice:** CLAUDE.md guidance ≈70% advisory adherence; PreToolUse/Stop hooks deterministically forbid. **Source:** L15 (T5). **Alignment:** E2 moves citation discipline off the advisory ceiling onto a Stop-hook gate. **Status:** adopt.
- **Claim:** without persistent working memory the model's own token becomes an unreliable source. **Practice:** prior-draft-as-source-of-truth drives fabricated facts and paraphrase drift. **Source:** L19; rc-06 (A6). **Alignment:** E2 verifies the bare token resolves, catching the fabrication A6 is built to prevent. **Status:** adapt (A6 is the Law-side write discipline; E2 is the boundary check).

### LAQF.E2:12 - Relations

- **Design cause (E:0):** the missing citation gate via [[../11-fpf-diagnostic]] D2 — transformed by a resolve-or-block Stop scan; MUST NOT read as gating the agent's own reasoning.
- **Measurement (R2):** verification-fidelity s6 ([[12-02-measurement-frame]] §2 card `laqf.mm.s6`).
- **Method family:** `MF-1` (deterministic forbid — Stop scan), an instance under C5.
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); E1 (the result-claim sibling); A6 (the emission-time anchoring E2 verifies); E3 (counter-evidence for claims with no mechanical resolve).

### LAQF.E2:End

---

## LAQF.E3 - Counter-Evidence Audit

> **Type:** Principle pattern (P) — LAQF Layer-E
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see E:0)
> **FPF kind:** Design (verification surface) — transform via Work (direct)
> **Detection characteristic:** verification-fidelity (`12-02` s6)
> **Source mechanism:** rc-26 (no counter-evidence audit)

### LAQF.E3:0 - Use this when

Use this when a claim — the agent's own or the user's — is a judgement with no mechanical check ("this design is the bottleneck", "the bug is in the cache layer", "this approach is safe"), and you want it audited against the evidence that would disconfirm it before it is accepted.

**What goes wrong if missed.** Assertions are accepted at face value; nothing audits for the counter-evidence (rc-26; S-023). The model's disposition oscillates — sometimes reflexive agreement, sometimes reflexive pushback (L19) — so a plausible claim passes unchallenged, and the one fact that would have falsified it is never sought.

**What this buys.** An audit step that, before accepting a judgement claim, actively seeks the disconfirming evidence — the question whose answer would prove the claim wrong (Fisher's maxim: let the data decide). It raises the floor on unevidenced acceptance without pretending to be a deterministic gate.

**Not this pattern when.** The claim is mechanically checkable — a build/test result (E1), a citation (E2), an output order (E4). Those have deterministic gates; E3 is for judgement claims where no such check exists, so it is advisory (`MF-2`) by nature, not a hook.

### LAQF.E3:1 - Problem frame

A judgement claim has no run to check it against and no anchor to resolve, so the only verification available is to look for what would disconfirm it. The model does not do this reliably: its RLHF disposition swings between sycophantic agreement and reflexive contrarianism (L19), and neither is an *audit* — both are reflexes. The discipline wanted is Fisher's maxim (the evidence decides), the same stance C3 encodes and A1 gates, here turned on the claim at the verification boundary. This is a Design cause (E:0): the audit is the user's to author. The frame is to make seeking counter-evidence a routine step for judgement claims, accepting it is advisory because no mechanical check exists.

### LAQF.E3:2 - Problem

How can a judgement claim with no mechanical check be audited against the evidence that would disconfirm it — rather than accepted at face value — given the model's disposition oscillates between agreement and reflexive pushback?

### LAQF.E3:3 - Forces

| Force | Tension |
|---|---|
| Audit vs face value | Seeking the disconfirming fact ↔ accepting a plausible claim unchallenged. |
| Advisory vs gate | A judgement audit is advisory ↔ a mechanically-checkable claim is a hook (E1/E2/E4). |
| Audit vs reflex | A deliberate counter-check ↔ the L19 agree/pushback oscillation. |
| Design-able | The audit step is the user's surface; it is authored, not adapted-around. |

### LAQF.E3:4 - Solution

Make a **counter-evidence audit** a routine step for judgement claims. Before accepting a claim that has no mechanical check, name the evidence that would disconfirm it and go look for it — Fisher's maxim applied at the verification boundary (the stance C3 encodes, A1 gates, here turned on the claim). This is the `MF-2` advisory family ([[12-01-source-pack]] §6): a disposition, not a deterministic gate, because a judgement claim has no run or anchor to check against. Route mechanically-checkable claims to their gates (E1 result, E2 citation, E4 order) rather than auditing them here. C5 confirms the classification: where a sub-claim *is* checkable, prefer the deterministic gate. The transformation is direct: the audit step goes from absent to authored.

- **Name the disconfirmer.** State the evidence that would prove the claim wrong, then seek it.
- **Advisory by nature.** A judgement audit is `MF-2`; a checkable claim goes to its `MF-1` gate.
- **Audit, not reflex.** The step is a deliberate counter-check, not agreement or contrarianism (L19).

*Before accepting a judgement, look for what would prove it wrong — audit the claim, do not take it at face value.*

### LAQF.E3:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A claim audited against its disconfirmer is held only as far as the evidence supports; a claim accepted at face value is right only when it happens to be.

**Show #1 (Claude Code session).** The agent asserts "the slowness is the N+1 query". Under E3: the audit fires — "what would disconfirm this? a profile showing the time is elsewhere" — and the agent reads the profile before acting, finding the cost is actually in serialization (Fisher's maxim). Without E3: the plausible claim is accepted, the N+1 is "fixed", and the slowness remains because the real cause was never sought (S-023).

**Show #2 (scientific-method episteme).** Falsification is the engine of science: a hypothesis earns standing only by surviving a genuine attempt to refute it, and a discipline that only seeks confirming data produces confident error. E3 imports that falsificationist step into verification — name the refuter, seek it — and L19 is the reason a *disposition* (not a one-off prompt) is needed: the model's default is reflex, not audit.

### LAQF.E3:6 - Bias-Annotation

Lenses tested: **Did**, **Gov**. Scope: judgement claims without a mechanical check.

- **Did bias:** the audit is authored as a named, teachable step (state the disconfirmer, seek it) so it is followable; risk is a vague "be sceptical" — bounded by phrasing it as the concrete "name what would falsify this" move.
- **Gov bias:** an audited claim carries its counter-check as a reviewable trace (what disconfirmer was sought, what was found); pairs with A1's evidence-gate and E1/E2's deterministic checks.

### LAQF.E3:7 - Conformance Checklist

1. **CC-E3-1 (Disconfirmer named).** A judgement claim is accepted only after the evidence that would disconfirm it is named and sought.
2. **CC-E3-2 (Advisory scope).** Mechanically-checkable claims are routed to their gates (E1/E2/E4), not audited as judgement here.
3. **CC-E3-3 (Audit, not reflex).** The step is a deliberate counter-check, not reflexive agreement or pushback (L19).
4. **CC-E3-4 (Detection wired).** Reads verification-fidelity s6: leading = judgement claim accepted without a recorded counter-check; lagging = confident-but-wrong assertions surfacing downstream.

### LAQF.E3:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Accept a plausible claim at face value** | the disconfirming fact is never sought (S-023) | name the disconfirmer and go look for it |
| **Reflexively push back instead** | contrarianism is not an audit (L19) | seek evidence, not a counter-position |
| **Try to hook a judgement claim** | judgement has no mechanical check | keep E3 advisory (MF-2); route checkable claims to E1/E2/E4 |

### LAQF.E3:9 - Consequences

**Benefits.** Judgement claims are held to their evidence; confident-but-wrong assertions drop; verification-fidelity (s6) improves on the un-gateable claims E1/E2/E4 cannot reach; A1's gate and C3's stance gain a verification-boundary application.

**Trade-offs.** An advisory audit is bounded by the adherence ceiling (≈70%, L15) — it raises the floor but does not guarantee the counter-check; and over-applied it can tip into the reflexive pushback it is meant to replace. Bounded by reserving E3 for genuine judgement claims and routing checkable ones to their deterministic gates.

### LAQF.E3:10 - Rationale

rc-26 is the verification-boundary face of the same Fisher's-maxim stance that A1 gates (substance-free dissent) and C3 installs (the engineering posture): A1 is the Law-mitigation at the moment of dissent, C3 is the config-side disposition, E3 is the audit turned on a *claim* at the point of acceptance. All three read s4/s6 family signals. Keeping them distinct preserves each `EntityOfConcern` (`E.8:0.3`): E3's single move is "name the disconfirmer and seek it", which is why it is advisory — unlike E1/E2/E4, a judgement claim offers nothing mechanical to gate.

### LAQF.E3:11 - SoTA-Echoing

- **Claim:** the RLHF disposition oscillates between sycophantic agreement and reflexive pushback; neither is an audit. **Practice:** sycophancy baseline + over-correction both documented; dynamic gating cut sycophancy 85.7% in research. **Source:** L19 (T4). **Alignment:** E3 installs a deliberate counter-check rather than relying on the oscillating default. **Status:** adapt (research gating ≠ a session audit; encoded as an advisory disposition).
- **Claim:** an arguing-loop / modified-version pattern signals unaudited disposition. **Practice:** 4.7 arguing loop 3–5 turns; "executes a modified version of what you asked". **Source:** ME-2 [L06] (T4). **Alignment:** E3's named-disconfirmer step replaces the reflex with an evidence-seeking move. **Status:** adopt.

### LAQF.E3:12 - Relations

- **Design cause (E:0):** the missing counter-evidence audit via [[../11-fpf-diagnostic]] D2 — transformed by authoring the audit step; MUST NOT read as a deterministic gate (advisory by nature).
- **Measurement (R2):** verification-fidelity s6 ([[12-02-measurement-frame]] §2 card `laqf.mm.s6`).
- **Method family:** `MF-2` (advisory) — an encoded audit disposition.
- **Coordinates with:** A1 (gates substance-free dissent; shares Fisher's maxim); C3 (encodes the engineering posture E3 audits within); E1/E2/E4 (the deterministic gates for the checkable claims E3 declines).

### LAQF.E3:End

---

## LAQF.E4 - Input-Order Fidelity

> **Type:** Principle pattern (P) — LAQF Layer-E
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see E:0)
> **FPF kind:** Design (verification surface) — transform via Work (direct)
> **Detection characteristic:** verification-fidelity (`12-02` s6)
> **Source mechanism:** rc-27 (output ordering not preserved)

### LAQF.E4:0 - Use this when

Use this when the agent emits a multi-item output that corresponds to an ordered input — a list the user gave, a set of numbered questions, a sequence of files or steps — and the emitted order must match the input order rather than being silently rearranged.

**What goes wrong if missed.** A multi-item output silently reorders relative to the input (rc-27; S-004). The user's item 3 answer appears where item 1 should be; a numbered set comes back permuted. The model interprets instructions literally and does not generalise (L02), so unless order is stated as a requirement it treats the sequence as free, and the reader must re-collate to trust the mapping.

**What this buys.** An output that preserves the input order by default — verified by an order check (or output-shape rule) that the emitted sequence matches the input sequence — so item *n* in equals item *n* out, and reordering happens only when explicitly requested.

**Not this pattern when.** The output has no input-order correspondence (free-form prose, an unordered set the user did not sequence). E4 preserves *a given input order*; the iteration-mode delta discipline (A2) governs *which* items change, and E1/E2 gate result and reference claims — different verification axes.

### LAQF.E4:1 - Problem frame

When the user hands an ordered input — a numbered list, a sequence of questions — the order *is* information: it carries priority, dependency, or the user's own mapping. The model treats the sequence as free unless told otherwise, because it follows instructions literally and does not infer an unstated constraint (L02), so it reorders for its own convenience and the reader loses the 1:1 mapping. The fix is to make order-preservation the default and verify it at the boundary — a check the harness can run on the emitted sequence. This is a Design cause (E:0): the order check is the user's to author. The frame is to preserve and verify input order unless reordering is explicitly asked for.

### LAQF.E4:2 - Problem

How can a multi-item output be required to preserve its input order — item *n* in mapping to item *n* out — so the reader keeps the 1:1 correspondence, unless reordering is explicitly requested?

### LAQF.E4:3 - Forces

| Force | Tension |
|---|---|
| Preserved vs free order | The input order carries meaning ↔ the model treats the sequence as free (L02). |
| Default-preserve vs explicit-reorder | Order held by default ↔ reordering only on request. |
| Check vs flow | Verifying the emitted sequence ↔ a false flag on a legitimately unordered set. |
| Design-able | The order check is the user's surface; it is authored, not adapted-around. |

### LAQF.E4:4 - Solution

Preserve the **input order by default** and verify it. Emit multi-item output in the same order as the corresponding input — item *n* in to item *n* out — and check the emitted sequence against the input sequence (`MF-6` output shaping / a deterministic order check, [[12-01-source-pack]] §6), flagging a mismatch. Rely on the model's literalness (L02): stated as a requirement, order-preservation is followed; left unstated, it is not. Reorder only when the user explicitly asks. Where the check is mechanical (the input sequence is known), C5 may make it a deterministic gate; where it is a soft default it stays an output-shape rule. The transformation is direct: order goes from incidental to verified.

- **Item *n* in ⟶ item *n* out.** The emitted order mirrors the input order by default.
- **Verify the sequence.** An order check compares emitted to input order and flags a mismatch.
- **Reorder only on request.** Rearrangement happens only when the user explicitly asks (L02 literalness).

*Keep the order the user gave — item n in is item n out — and verify it, unless reordering was explicitly asked for.*

### LAQF.E4:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** An output that preserves input order keeps the reader's 1:1 mapping for free; a silently reordered output forces the reader to re-collate before trusting it.

**Show #1 (Claude Code session).** The user asks five numbered questions in one message. Under E4: the answers come back 1–5 in the asked order, and an order check confirms the mapping, so the user reads straight down. Without E4: the model answers in the order it found convenient, question 4's answer sits under heading 2, and the user must re-map every answer to its question before trusting any (S-004).

**Show #2 (data-processing episteme).** A stable sort preserves the input order of equal-key records precisely because downstream consumers rely on that order carrying meaning; an unstable sort that permutes them is a classic source of silent corruption. E4 is stability applied to agent output — equal-status items keep their input order — and L02 is the reason it must be stated: the model preserves order when told, treats it as free when not.

### LAQF.E4:6 - Bias-Annotation

Lenses tested: **Did**, **Arch**. Scope: ordered multi-item output.

- **Did bias:** "preserve input order; reorder only on request" is a single teachable default; risk is applying it to a genuinely unordered set — bounded by firing only where the input carries a sequence.
- **Arch bias:** treats output order as a contract between input and output, checkable at the boundary; risk is over-strictness on a legitimately rearranged answer — bounded by honouring an explicit reorder request.

### LAQF.E4:7 - Conformance Checklist

1. **CC-E4-1 (Order preserved).** Multi-item output mirrors the input order by default — item *n* in to item *n* out.
2. **CC-E4-2 (Sequence verified).** An order check compares the emitted sequence to the input sequence and flags a mismatch (`MF-6`).
3. **CC-E4-3 (Explicit reorder only).** Rearrangement happens only when the user explicitly requests it.
4. **CC-E4-4 (Detection wired).** Reads verification-fidelity s6: leading = output-sequence ≠ input-sequence flag; lagging = re-collation burden / mis-mapped items surfacing for the reader.

### LAQF.E4:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Reorder for the model's convenience** | breaks the reader's 1:1 mapping (S-004) | preserve input order; item *n* in to item *n* out |
| **Leave order unstated** | the model treats the sequence as free (L02) | state order-preservation as a requirement |
| **Flag a legitimately unordered set** | false positive on free-form output | fire only where the input carries a sequence |

### LAQF.E4:9 - Consequences

**Benefits.** The reader keeps the input-to-output mapping without re-collating; silently permuted output stops shipping; verification-fidelity (s6) on ordered output reaches the green band; downstream consumers that rely on the sequence stay correct.

**Trade-offs.** The order check is a small amount of output-shape tooling, and an over-strict check can flag a legitimately rearranged answer; bounded by firing only on inputs that carry a sequence and honouring explicit reorder requests.

### LAQF.E4:10 - Rationale

rc-27 is a literalness failure (L02) on the output side: the model holds order when it is a stated requirement and discards it when it is not, so the repair is to state and verify it. Keeping E4 distinct from A2 (delta discipline) preserves each `EntityOfConcern` (`E.8:0.3`): A2 governs *which* items change across an iteration, E4 governs *the order* of the items emitted. The order check is the cheapest `MF-6` instance — comparing two sequences — which is why E4 sits with the verification gates rather than the heavier `MF-1` hooks.

### LAQF.E4:11 - SoTA-Echoing

- **Claim:** the model follows explicit instructions literally and does not generalise an unstated constraint. **Practice:** 4.8 interprets literally, does not generalise one item to another. **Source:** L02 (T1). **Alignment:** E4 states order-preservation explicitly so literalness preserves it. **Status:** adopt.
- **Claim:** constraining emission form controls output defects. **Practice:** output-shaping moves (answer-budget, delta, structured form). **Source:** `MF-6` ([[12-01-source-pack]] §6). **Alignment:** E4's order check is an output-shape verification of the emitted sequence. **Status:** adopt.

### LAQF.E4:12 - Relations

- **Design cause (E:0):** silent output reordering via [[../11-fpf-diagnostic]] D2 — transformed by a default-preserve + order check; MUST NOT read as flagging a genuinely unordered set.
- **Measurement (R2):** verification-fidelity s6 ([[12-02-measurement-frame]] §2 card `laqf.mm.s6`).
- **Method family:** `MF-6` (output shaping — order verification); deterministic gate via C5 where the sequence is known.
- **Coordinates with:** A2 (delta discipline — which items change, vs E4's order of items); E1/E2 (result and reference gates); C5 (whether the order check becomes a deterministic gate).

### LAQF.E4:End

---

## LAQF.E5 - Quiet Toolchain Output

> **Type:** Principle pattern (P) — LAQF Layer-E
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see E:0)
> **FPF kind:** Design (verification surface) — transform via Work (direct)
> **Detection characteristic:** output-economy (`12-02` s5)
> **Source mechanism:** rc-28 (lint/test output flood)

### LAQF.E5:0 - Use this when

Use this when lint, test, build, or other toolchain invocations dump their full stdout into the context on every run — including passing runs that produce nothing the agent needs — and you want the toolchain quiet on success and detailed only on failure.

**What goes wrong if missed.** Lint/test stdout is dumped into context every run; there is no default `--quiet` plus JSON-on-failure (rc-28; S-041). A passing run that needs to report one line instead floods the window with hundreds, and because the 4.7+ tokenizer charges ~30% more tokens per same English (L03 / A4), the flood shrinks the effective context faster than the raw line count suggests.

**What this buys.** Toolchain invocations defaulted to quiet success and structured-on-failure: a passing run emits a line, and full diagnostic detail (ideally structured/JSON) appears only when there is a failure to diagnose — so the window carries signal, not a passing run's noise.

**Not this pattern when.** The full output *is* the signal the agent needs (a verbose run requested for diagnosis). E5 quiets *routine passing* output; D2 (Atomic Single-Form Emission) shapes *stage artefacts*, and B1/A4 (context-integrity) govern the window the flood consumes — E5 is the toolchain-side source of that flood.

### LAQF.E5:1 - Problem frame

A test or lint run is invoked for its verdict — pass or fail — but by default it narrates every check, and on a passing run that narration is pure noise pushed into a finite, tokenizer-taxed window (L03). The signal a passing run carries is one bit; the cost it imposes is hundreds of lines. The fix is a default: quiet on success, detail on failure, so the window only fills when there is something to diagnose. This is a Design cause (E:0): the invocation defaults are the user's to set. But it is floored — Anthropic's brevity experiment shows over-suppression costs quality (L04), so failure detail must stay full. The frame is to quiet routine passing output without suppressing genuine failure detail.

### LAQF.E5:2 - Problem

How can routine toolchain output be kept out of the context on passing runs — emitting a verdict line on success and full structured detail only on failure — without suppressing the diagnostic output a real failure needs?

### LAQF.E5:3 - Forces

| Force | Tension |
|---|---|
| Quiet success vs full narration | A one-line verdict on pass ↔ every check dumped every run. |
| Window cost vs signal | A tokenizer-taxed context (L03) ↔ the one bit a passing run carries. |
| Quiet vs floor | Suppressing passing noise ↔ keeping full failure detail (L04 floor). |
| Design-able | The invocation defaults are the user's surface; they are set, not adapted-around. |

### LAQF.E5:4 - Solution

Default the toolchain to **quiet success, structured failure**. Set lint/test/build invocations to `--quiet` (or equivalent) so a passing run emits a verdict line, and surface full detail — ideally structured/JSON — only on failure (`MF-6` output shaping, [[12-01-source-pack]] §6). This keeps the tokenizer-taxed window (L03) carrying signal, not a passing run's narration. Floor it at L04: the failure path stays full, because over-suppression costs quality. E5 is D2's `MF-6` sibling pointed at tool output rather than stage artefacts, and it protects the context-integrity (A4/B1) that the flood erodes. C5 decides whether the quiet default is worth a deterministic wrapper or stays a convention. The transformation is direct: the defaults move from verbose-always to quiet-on-success.

- **Quiet on success.** A passing run emits a verdict line, not its full narration.
- **Structured on failure.** A failing run surfaces full, ideally structured/JSON, detail (L04 floor).
- **Protects the window.** The default keeps the tokenizer-taxed context (L03) carrying signal.

*Make the toolchain quiet on success and detailed on failure — a passing run is one line, not a flood the window has to carry.*

### LAQF.E5:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A toolchain quiet on success spends the window only on failures worth diagnosing; a toolchain verbose on every run spends it on passing runs that carry one bit.

**Show #1 (Claude Code session).** A test suite is run after each edit. Under E5: a passing run reports `42 passed` and nothing more, while a failure surfaces the failing cases as structured output — so ten green runs cost ten lines, not ten floods. Without E5: every run dumps its full log, the window fills with passing narration, the tokenizer tax (L03) shrinks effective context faster than the line count shows, and the agent rotates early (S-041).

**Show #2 (operations episteme).** Log-level discipline and "no news is good news" Unix tools exist because a system that narrates every success drowns the operator in noise and hides the one error that matters; quiet-by-default with detail-on-error is the durable convention. E5 applies it to the agent's toolchain, and L04 is the guardrail that quiet must not become silent — the failure path keeps its full detail.

### LAQF.E5:6 - Bias-Annotation

Lenses tested: **Eco**, **Arch**. Scope: toolchain invocation output.

- **Eco bias:** attends the token cost a passing run imposes on the tokenizer-taxed window (L03); risk is over-suppressing failure detail — bounded by the L04 floor (failure stays full).
- **Arch bias:** treats quiet-on-success / detail-on-failure as the toolchain's default contract; risk is suppressing a verbose run genuinely requested for diagnosis — bounded by quieting only routine passing output.

### LAQF.E5:7 - Conformance Checklist

1. **CC-E5-1 (Quiet on success).** Toolchain invocations default to a verdict line on a passing run, not full narration.
2. **CC-E5-2 (Structured on failure).** A failing run surfaces full, ideally structured/JSON, detail (L04 floor).
3. **CC-E5-3 (Floor held).** Quiet does not become silent; the failure path keeps its diagnostic detail.
4. **CC-E5-4 (Detection wired).** Reads output-economy s5: leading = tokens/Bash on passing runs; lagging = early context rotation / window flood from toolchain narration.

### LAQF.E5:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Dump full stdout every run** | floods a tokenizer-taxed window (L03) on passing runs | default to `--quiet`; verdict line on success |
| **Suppress failure detail too** | strips what a real failure needs (L04 floor) | keep failure output full, ideally structured |
| **Quiet a diagnosis-requested run** | hides output the agent actually needs | quiet only routine passing output |

### LAQF.E5:9 - Consequences

**Benefits.** Passing runs stop flooding the window; the tokenizer-taxed context (L03) carries signal; output-economy (s5) returns toward the green band; the context-integrity E5 protects (A4/B1) holds longer before rotation.

**Trade-offs.** Setting quiet defaults across the toolchain is per-tool configuration, and an over-aggressive quiet can hide a needed warning; bounded by the L04 floor (failure stays full) and quieting only routine passing output.

### LAQF.E5:10 - Rationale

rc-28 is D2's output-economy failure relocated from stage artefacts to tool output: where D2 collapses a stage's monolith-plus-shadow, E5 quiets a tool's passing-run narration — both `MF-6`, both floored at L04. It sits in Layer E because the flood is a *verification-surface* cost: the toolchain is the agent's instrument, and a quiet instrument is read more reliably than a noisy one. Keeping E5 a single move — "quiet on success, structured on failure" (`E.8` maturity rule, `FPF-Spec.md:65222`) — distinguishes it from A4/B1, which manage the *window*, where E5 manages the *source* that fills it.

### LAQF.E5:11 - SoTA-Echoing

- **Claim:** the tokenizer charges more per same English, so output volume shrinks effective context faster than line count shows. **Practice:** 4.7+ tokenizer ≈ +30% tokens per same English. **Source:** L03 (T1). **Alignment:** E5 cuts the passing-run volume that the tax most penalises. **Status:** adopt.
- **Claim:** over-suppressing output degrades quality. **Practice:** Anthropic reverted ≤25/≤100-word caps after a 3% eval drop. **Source:** L04 (T1+T5). **Alignment:** E5 floors the cut — quiet on success, full on failure — rather than suppressing detail. **Status:** adopt.

### LAQF.E5:12 - Relations

- **Design cause (E:0):** toolchain output flood via [[../11-fpf-diagnostic]] D2 — transformed by quiet-on-success defaults; MUST NOT read as suppressing genuine failure detail (L04 floor).
- **Measurement (R2):** output-economy s5 ([[12-02-measurement-frame]] §2 card `laqf.mm.s5`; floored per L04).
- **Method family:** `MF-6` (output shaping — `--quiet` + structured-on-failure).
- **Coordinates with:** D2 (the stage-artefact sibling in the same `MF-6` family); A4 / B1 (the context-integrity the flood erodes); C5 (whether the quiet default earns a deterministic wrapper).

### LAQF.E5:End

---

## See also

- [[12-14-patterns-E-ru]] — Russian twin
- [[12-10-patterns-A]] — frozen house-style exemplar (the 13-section template E1–E5 reuse)
- [[12-12-patterns-C]] — Layer-C (Design) patterns; E:0 inherits the C:0 design contract; C5 owns the deterministic/advisory classification E1/E2/E4/E5 instantiate
- [[12-13-patterns-D]] — Layer-D (workflow) patterns; D2 shares E5's `MF-6` output-shaping family
- [[12-00-spine]] — keystone: §5 roster (Design kind + detection), §4.3 relation records, §4.1 edition direction
- [[12-01-source-pack]] — G.2 pack; §8 palette `LAQF.sota.iter3.palette` cited by every §11 (L-/ME-/MF-/Γ_epist ids)
- [[12-02-measurement-frame]] — detection axes (§5 pattern↔characteristic; §2 DHCMethod cards; §3 CAL bands; §4 leading/lagging)
- [[_inputs/rc-digest]] — §5 Layer-E mechanisms (rc-24…rc-28)
- [[../11-fpf-diagnostic]] — D2 design-space ruling (the basis for the E:0 design contract)
- `FPF-Spec.md:65183` E.8 authoring conventions · `:65272` canonical template · `:24417` A.19 · `:42826` C.16 · `:87746` G.2
