---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, patterns, layer-f, e8-patterns]
seminar-iteration: 3
created: 2026-06-28
status: patterns-layer-f
method: FPF E.8 (authoring conventions) · 11-fpf-diagnostic D2 (Design-space / Work quadrant) · consumes 12-01 palette LAQF.sota.iter3.palette + 12-02 detection axes
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-15-patterns-F-ru]]"
---

# LAQF — Layer F patterns (process / git hygiene): F1–F2

The two **Layer-F** patterns of LAQF. Each addresses a property of the agent's *process surface* — the git-hygiene discipline around how a working branch is kept current and how a commit is shaped: whether the branch's base is pulled fresh before it drifts past a usable bound, and whether a banned commit trailer is stripped deterministically rather than merely forbidden in prose. In FPF terms each is a **Design** cause ([[../11-fpf-diagnostic]] D2 design-space): not a model-internal Law to mitigate (Layer A), nor someone else's harness boundary to adapt around (Layer B), but *the user's own process surface* — transformable outright by direct Work.

These patterns reuse the house style frozen in [[12-10-patterns-A]] (the full `E.8` thirteen-section template, `FPF-Spec.md:65272`). Each cites the SoTA pack by id ([[12-01-source-pack]] §8 palette `LAQF.sota.iter3.palette`) and wires its detection slot to one `A.19` characteristic ([[12-02-measurement-frame]] §5). They assert no new evidence and re-paraphrase no source — an id, never a quote (`G.2:4.2`, `FPF-Spec.md:87904`).

## F:0 - The Layer-F design contract (read once, applies to F1–F2)

Stated here once so each Solution need not repeat it (`E.8:0.3` anti-repetition, `FPF-Spec.md:65234`). Layer F shares the Design quadrant with Layers C–E, so this contract **inherits the Layer-C design contract** ([[12-12-patterns-C]] C:0) rather than restating it, specialising it to the process / git-hygiene surface under the same [[../11-fpf-diagnostic]] D2 design-space ruling (D–F are all Design / direct-Work):

- **The cause is the user-owned process surface — neither a Law nor a harness boundary.** Each F-pattern names a missing process gate (a branch left to drift out of date, a banned trailer left to advisory). Like Layer C, this surface is the user's to author — git, hooks, and the worktree workflow are all under the user's hand.
- **Direct Work, no hedge** (inherited from C:0). An F-pattern's Solution *adds the gate*: it checks the branch's freshness at the integration point, it strips the banned trailer at the commit boundary. There is no "mitigate-only" caveat — the gate can be made to hold.
- **Layer-1 states *what*; Layer-2 (S6) realises *how*** (inherited from C:0). This Domain edition states the process property; the Local Practice edition (this user's actual `wt sync` cadence, `PreToolUse(Bash git commit)` hook) is the realisation ([[12-20-local-practice-edition]]).
- **Prefer deterministic over advisory where a rule must hold** (inherited from C:0 → C5). Both Layer-F properties are mechanically checkable — a branch-behind count against `origin/master`, the presence of a banned trailer in a commit message — so both belong in a hook (`MF-1`), not a prose rule. C5 owns the classification; F1 and F2 inherit the preference and point to C5. Unlike Layer E (a mix of `MF-1` gates and the `MF-2` audit), Layer F is wholly deterministic.
- **Detection is behavioural.** Each pattern's success is observed through one of the eight `A.19` characteristics ([[12-02-measurement-frame]] §1), read at the **leading** (mid-session) indicator, not only the lagging outcome (§4 of the frame). Layer F reads verification-fidelity (s6) for the freshness gate and instruction-adherence (s1) for the trailer gate.

---

## LAQF.F1 - Bounded Branch Freshness

> **Type:** Principle pattern (P) — LAQF Layer-F
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see F:0)
> **FPF kind:** Design (process / git hygiene) — transform via Work (direct)
> **Detection characteristic:** verification-fidelity (`12-02` s6)
> **Source mechanism:** rc-29 (no master-pull protocol)

### LAQF.F1:0 - Use this when

Use this when an agent works on a feature branch over many commits and the branch's base silently falls behind `master`/`main` — and you want the branch kept within a bounded freshness of its integration target, with the currency checked before integration rather than discovered at merge time.

**What goes wrong if missed.** No mechanism pulls fresh `master` into the branch after a commit, so the branch drifts (rc-29; S-025). Each commit widens the gap between what the agent builds against and what the branch will merge into; nothing checks the branch-behind count, so the divergence surfaces only as a conflict-laden, regression-prone merge once the work is "done". The agent has no persistent sense of repository state across turns (rc-06 / A6), so the drift is invisible to it.

**What this buys.** A freshness gate that verifies the branch's distance from `origin/master` at the integration point (commit / push / PR) and flags or blocks when it exceeds a bounded threshold — so the branch is pulled current *before* it drifts past a usable bound, and an integration-readiness claim is backed by an observed freshness check rather than assumed.

**Not this pattern when.** The branch is deliberately isolated from `master` (a long-lived experiment, a frozen release line) where divergence is intended. F1 bounds *unintended* drift on branches meant to integrate; F2 (Deterministic Commit Hygiene) shapes the *content* of a commit, and B2 (Authoritative Handoff Re-Entry) re-establishes *context* identity, not branch currency.

### LAQF.F1:1 - Problem frame

A feature branch is forked from `master` at a point in time, but `master` keeps moving; with every upstream commit the branch's base goes more stale, and the cost of reconciling the two grows super-linearly with the divergence. The agent does not feel this — it has no working memory of repository state across turns (A6) and no instruction makes it check — so it builds against an increasingly obsolete base and the drift is paid all at once as a painful merge. The repository already knows the branch-behind count; what is missing is a gate that reads it at the integration point and holds the branch within a freshness bound. This is a Design cause (F:0): the gate is the user's to author. The frame is to bound branch drift by verifying currency before integration.

### LAQF.F1:2 - Problem

How can a working branch be kept within a bounded freshness of its integration target — its distance from `origin/master` verified at the integration point and reconciled before it exceeds the bound — so divergence is paid down incrementally rather than discovered as a late, conflict-laden merge?

### LAQF.F1:3 - Forces

| Force | Tension |
|---|---|
| Bounded vs unbounded drift | A branch kept current within a bound ↔ a branch left to diverge until merge. |
| Gate vs advisory | A freshness check at integration ↔ a prose "remember to pull master" (≈70%, L15). |
| Strictness vs isolation | Bounding unintended drift ↔ a false flag on a deliberately-isolated branch. |
| Design-able | The freshness gate is the user's surface; it is authored, not adapted-around. |

### LAQF.F1:4 - Solution

Bound branch drift by **verifying currency at the integration point**. Author a freshness gate — a Stop / `PreToolUse(git push)` check — that reads the branch's distance from `origin/master` (the branch-behind count) and flags or blocks when it exceeds a bounded threshold, prompting a pull-fresh before the work integrates (`MF-1` deterministic forbid, [[12-01-source-pack]] §6). The integration-readiness of the branch becomes a claim backed by an observed freshness check, not an assumption. This is a specific `MF-1` instance of the C5 ruling — the process-side sibling of F2 (commit hygiene) and the verification-side analogue of E1 (result claims): each gates a claim on an observed event the repository already records. Reserve the gate for branches meant to integrate; a deliberately-isolated branch is exempt. The transformation is direct: drift goes from invisible-until-merge to verified-at-integration.

- **Branch ⟶ behind-count check.** The gate reads the distance from `origin/master` at the integration point.
- **Past the bound ⟶ reconcile first.** A branch beyond the freshness threshold is pulled current before it integrates.
- **Integrating branches only.** A deliberately-isolated branch is exempt from the bound.

*Keep the branch within a freshness bound — verify its distance from master at integration and reconcile before it drifts, do not discover the gap at merge.*

### LAQF.F1:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A branch kept current within a freshness bound integrates cleanly by construction; a branch left to drift pays the whole divergence at once, as a conflict-laden merge whose cost grew while no one was looking.

**Show #1 (Claude Code session).** The agent works a feature branch across a day of commits while `master` advances underneath it. Under F1: a freshness gate reports the branch is 40 commits behind `origin/master` at push time, blocks the push, and the branch is synced current before it integrates — the divergence is paid down in small increments. Without F1: nothing checks the gap, the branch is opened as a PR 40 commits stale, and the merge surfaces conflicts and silent regressions against changes the agent never built against (S-025).

**Show #2 (continuous-integration episteme).** Trunk-based development and continuous integration exist precisely because long-lived branches diverge: the discipline is to integrate early and often, keeping each branch within a small, bounded distance of trunk, because the cost of a merge grows super-linearly with divergence and a week-old branch is a known hazard. F1 is that discipline applied to the agent's branch — bound the drift, verify it at integration — and A6 is the reason it must be a gate, not a habit: the agent has no working memory of how far the branch has drifted.

### LAQF.F1:6 - Bias-Annotation

Lenses tested: **Arch**, **Gov**. Scope: integrating feature branches.

- **Arch bias:** treats branch freshness as a contract between branch and trunk — the branch stays within a bounded distance of `origin/master`, checkable at the integration boundary; risk is over-strictness on a legitimately-isolated branch — bounded by exempting branches not meant to integrate.
- **Gov bias:** the freshness check is an accountability gate (the branch's currency is provably verified before merge); the gate log is the audit trail, shared with F2 and the C5/C6/C7 controls.

### LAQF.F1:7 - Conformance Checklist

1. **CC-F1-1 (Bound declared).** A freshness bound (max commits / age behind `origin/master`) is declared for integrating branches.
2. **CC-F1-2 (Verified at integration).** The branch-behind count is checked at the integration point (commit / push / PR) and a branch past the bound is reconciled before it integrates (`MF-1`).
3. **CC-F1-3 (Isolation exempt).** A deliberately-isolated branch is exempt from the bound.
4. **CC-F1-4 (Detection wired).** Reads verification-fidelity s6: leading = branch-behind-count unchecked at commit/push (a freshness check that did not run); lagging = stale-base merge conflicts / silent regressions surfacing at integration (§4 frame).

### LAQF.F1:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Let the branch drift until merge** | the divergence is paid all at once, conflict-laden (S-025) | verify the behind-count at integration; reconcile within the bound |
| **Advisory "remember to pull master"** | a prose reminder plateaus at the adherence ceiling (~70%, L15) | enforce a freshness gate at the integration point (`MF-1`) |
| **Flag a deliberately-isolated branch** | over-blocks a long-lived experiment / frozen line | exempt branches not meant to integrate |

### LAQF.F1:9 - Consequences

**Benefits.** Branches integrate within a bounded freshness; late conflict-laden merges drop; verification-fidelity (s6) on integration-readiness reaches the green band; the divergence is paid down incrementally instead of as a single painful reconciliation.

**Trade-offs.** The freshness gate is code to maintain and a badly-tuned bound can nag on a branch that is current enough or block a legitimately-isolated one; bounded by tuning the threshold to the team's integration cadence and exempting branches not meant to integrate.

### LAQF.F1:10 - Rationale

rc-29 is the process-side `MF-1` instance of the C5 meta-pattern: the same "advisory does not enforce; gate it on an observed event" move, applied to branch currency rather than a terminal result (E1) or a commit trailer (F2). F1 owns one placement — the freshness check at the integration point — leaving C5 to own the classification. The leverage is that the repository *already records* the branch-behind count; the pattern is a single move (`E.8` maturity rule, `FPF-Spec.md:65222`) that reads it at the right moment. Keeping F1 distinct from B2 preserves each `EntityOfConcern` (`E.8:0.3`): B2 re-establishes *context* identity after a break, F1 verifies *branch* currency before integration — different surfaces, different breaks.

### LAQF.F1:11 - SoTA-Echoing

- **Claim:** a process step left advisory is not performed reliably; only an enforced gate makes it hold. **Practice:** CLAUDE.md guidance ≈70% advisory adherence; PreToolUse/Stop hooks deterministically forbid. **Source:** L15 (T5). **Alignment:** F1 moves the pull-fresh step — currently uncovered (S-025) — off the advisory ceiling onto a freshness gate at integration. **Status:** adopt.
- **Claim:** a harness-enforced gate is what makes a procedure hold across turns. **Practice:** Plan Mode / approval gates as harness-enforced, not advisory. **Source:** L16 (T1+T5). **Alignment:** F1 makes the freshness check harness-enforced at the integration boundary rather than a per-turn habit. **Status:** adapt (L16 gates plan→execute; F1 gates branch→integration).

### LAQF.F1:12 - Relations

- **Design cause (F:0):** the missing branch-freshness gate via [[../11-fpf-diagnostic]] D2 — transformed by a behind-count check at integration; MUST NOT read as forbidding deliberately-isolated branches.
- **Measurement (R2):** verification-fidelity s6 ([[12-02-measurement-frame]] §2 card `laqf.mm.s6`).
- **Method family:** `MF-1` (deterministic forbid — freshness gate at integration), an instance under C5.
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); F2 (the commit-hygiene sibling in the same process / `MF-1` family); E1 (the result-claim analogue — a claim gated on an observed event); A6 (the no-working-memory Law that makes the drift invisible to the agent).

### LAQF.F1:End

---

## LAQF.F2 - Deterministic Commit Hygiene

> **Type:** Principle pattern (P) — LAQF Layer-F
> **Status:** Build (v0.1)
> **Normativity:** Normative (design-transformation; see F:0)
> **FPF kind:** Design (process / git hygiene) — transform via Work (direct)
> **Detection characteristic:** instruction-adherence (`12-02` s1)
> **Source mechanism:** rc-30 (Co-Authored-By trailer leak)

### LAQF.F2:0 - Use this when

Use this when there is a hard, mechanical rule about commit content — "never add a `Co-Authored-By` trailer", "no `Generated-with` line", "commit messages in British English" — and you want it enforced at the commit boundary rather than left as a prose ban the agent forgets under load.

**What goes wrong if missed.** "Never add `Co-Authored-By`" lives only in `CLAUDE.md`; no `PreToolUse(Bash git commit)` hook strips the trailer (rc-30; S-026). The ban relies on adherence, and an advisory rule plateaus at the adherence ceiling (≈70%, L15) and decays as the instruction stack grows (G.2-F2), so the banned trailer slips into a commit, gets pushed, and becomes part of the permanent history before anyone notices. The rule is single, deterministic, and exactly checkable — the precise case a hook should own.

**What this buys.** A `PreToolUse(git commit)` hook that scans the commit message for the banned trailer and strips it (or blocks the commit) deterministically — so the rule holds at 100% regardless of where it sits in the instruction stack or how loaded the context is. The hygiene rule moves off the advisory ceiling onto a gate.

**Not this pattern when.** The rule is a genuine judgement about commit *quality* ("is this message clear?") with no mechanical check — that is advisory by nature (`MF-2`, the E3 territory). F2 enforces *mechanically-checkable* commit-content rules; F1 (Bounded Branch Freshness) governs branch *currency*, and the C5 meta-pattern owns the deterministic-vs-advisory classification F2 instantiates.

### LAQF.F2:1 - Problem frame

The `Co-Authored-By` ban is the sharpest possible adherence probe: a single, unambiguous, mechanically-checkable rule with a known-bad string. Yet it is encoded only as prose in a 509-line instruction stack (L23), and a prose rule is attended ≈70% of the time (L15), less as the stack grows and the rule sits far from the model's attention (G.2-F2). So the one rule that could be enforced perfectly is instead left to slip — and once a banned trailer is committed and pushed, it is in the permanent record. The commit boundary is exactly where a hook can read the message and strip the trailer with certainty. This is a Design cause (F:0): the hook is the user's to author. The frame is to enforce mechanically-checkable commit-content rules at the commit boundary, not in prose.

### LAQF.F2:2 - Problem

How can a hard, mechanically-checkable commit-content rule (no banned trailer) be enforced at 100% at the commit boundary — independent of where the rule sits in the instruction stack or how loaded the context is — rather than relying on advisory adherence that plateaus near 70%?

### LAQF.F2:3 - Forces

| Force | Tension |
|---|---|
| Enforced vs advised rule | A commit-boundary strip ↔ a prose "never add the trailer" at ~70% (L15). |
| Gate vs stack distance | A hook fires regardless of position ↔ a rule attended less as the stack grows (G.2-F2). |
| Strip vs block | Silently removing the banned trailer ↔ blocking the commit for the agent to fix. |
| Design-able | The commit-boundary hook is the user's surface; it is authored, not adapted-around. |

### LAQF.F2:4 - Solution

Enforce mechanically-checkable commit rules with a **commit-boundary hook**. Author a `PreToolUse(Bash git commit)` hook that scans the commit message for the banned trailer (`Co-Authored-By`, `Generated-with`, …) and strips it — or blocks the commit for the agent to repair — deterministically (`MF-1` deterministic forbid, [[12-01-source-pack]] §6). The rule holds at 100% regardless of its position in the instruction stack or the context load, because the gate reads the actual commit message rather than relying on the model attending a prose ban. This is a specific `MF-1` instance of the C5 ruling — the canonical one, since the `Co-Authored-By` ban is the sharpest single-rule adherence probe — and the commit-content sibling of F1's branch-freshness gate. Reserve it for mechanically-checkable rules; a judgement about message quality stays advisory. The transformation is direct: the hygiene rule moves from a prose ban to an enforced strip.

- **Commit message ⟶ trailer scan.** The hook reads the message at the `git commit` boundary.
- **Banned trailer ⟶ stripped or blocked.** A banned trailer is removed (or the commit blocked) before it lands.
- **Checkable rules only.** A judgement about message quality stays advisory (`MF-2`), not a strip.

*Strip the banned trailer at the commit boundary — let a single deterministic rule be enforced by a hook, not left to a prose ban the model attends 70% of the time.*

### LAQF.F2:5 - Archetypal Grounding (Tell-Show-Show)

**Tell.** A commit rule enforced by a boundary hook holds every time by construction; the same rule left as prose holds about seven times in ten, and less as the instruction stack grows around it.

**Show #1 (Claude Code session).** The agent finishes work and runs `git commit` with a `Co-Authored-By: Claude` trailer appended out of habit. Under F2: the `PreToolUse(git commit)` hook scans the message, strips the banned trailer, and the commit lands clean — the ban holds regardless of how far down the 509-line stack (L23) the rule sits. Without F2: the prose ban is attended ≈70% of the time (L15), the trailer slips through on a loaded turn, the commit is pushed, and the banned line is now in the permanent history (S-026).

**Show #2 (commit-hook episteme).** Git's own `commit-msg` / `pre-commit` hooks, DCO sign-off enforcement, and CI commit-lint exist because a contribution policy stated only in `CONTRIBUTING.md` is violated, while a `commit-msg` hook that rejects or rewrites a malformed message holds 100%. F2 is that hook discipline for the agent's commits — the rule lives at the boundary, not in prose — and G.2-F2 is the reason it is needed: the advisory rule decays exactly as the instruction stack it lives in grows.

### LAQF.F2:6 - Bias-Annotation

Lenses tested: **Gov**, **Did**. Scope: mechanically-checkable commit-content rules.

- **Gov bias:** the trailer-strip is an accountability gate (the ban provably holds on every commit); the hook log is the audit trail, shared with F1 and the C5/C6/C7 controls.
- **Did bias:** "banned trailer → stripped at the commit boundary" is a single teachable gate; the carve-out (judgement about message quality stays advisory) prevents over-reaching into commit content the hook cannot mechanically check.

### LAQF.F2:7 - Conformance Checklist

1. **CC-F2-1 (Boundary-enforced).** A banned commit-content rule fires a `PreToolUse(git commit)` scan at the commit boundary (`MF-1`).
2. **CC-F2-2 (Stripped or blocked).** A banned trailer is stripped (or the commit blocked) before it lands, regardless of instruction-stack position.
3. **CC-F2-3 (Checkable rules only).** Only mechanically-checkable rules are hooked; judgement about message quality stays advisory.
4. **CC-F2-4 (Detection wired).** Reads instruction-adherence s1: leading = trailer-scan hits (near-misses caught at the commit boundary); lagging = banned-trailer / stated-rule-violated events surfacing in pushed history or review (§4 frame).

### LAQF.F2:8 - Common Anti-Patterns and How to Avoid Them

| Anti-pattern | Why it fails | Repair |
|---|---|---|
| **Ban the trailer in prose only** | adherence plateaus ~70% and decays with stack growth (L15, G.2-F2) | enforce a `PreToolUse(git commit)` strip (`MF-1`) |
| **Let the banned trailer reach pushed history** | once committed and pushed it is permanent (S-026) | strip or block at the commit boundary before it lands |
| **Hook a judgement about message quality** | "is this message clear?" has no mechanical check | keep checkable rules in the hook; judgement stays advisory (`MF-2`) |

### LAQF.F2:9 - Consequences

**Benefits.** The banned trailer never reaches a commit; the sharpest adherence rule holds at 100% regardless of stack position or context load; instruction-adherence (s1) on this rule reaches the green band; the permanent history stays clean without relying on the model attending a distant prose ban.

**Trade-offs.** The hook is code to maintain and a too-broad matcher could strip a line the user actually wanted; bounded by scoping the scan to the specific banned trailers and preferring a strip-with-log over a silent rewrite where the change should be visible.

### LAQF.F2:10 - Rationale

rc-30 is the canonical `MF-1` instance of the C5 meta-pattern: a single, deterministic, mechanically-checkable rule is exactly what belongs in a hook rather than prose, and the `Co-Authored-By` ban is the sharpest such probe in the whole stack (one known-bad string, no judgement). F2 owns one placement — the commit-boundary trailer scan — leaving C5 to own the classification and F1 to own branch currency. Splitting F2 (a checkable commit-content rule) from E3 (a judgement audit with no mechanical check) keeps each pattern a single move (`E.8` maturity rule, `FPF-Spec.md:65222`): F2 is deterministic because the rule is checkable; E3 is advisory because its claim is not.

### LAQF.F2:11 - SoTA-Echoing

- **Claim:** advisory rules plateau at the adherence ceiling and decay as the instruction stack grows; only deterministic gates forbid. **Practice:** CLAUDE.md guidance ≈70% advisory adherence; adherence drops with stack length. **Source:** L15 (T5); G.2-F2. **Alignment:** F2 moves the single sharpest adherence rule (the trailer ban) off the decaying advisory ceiling onto a commit-boundary hook. **Status:** adopt.
- **Claim:** a prompt-level "never do X" is disobeyed under load; a hook-level forbid is mandatory. **Practice:** agentic-misalignment — models disobey direct commands; hook-level forbid required. **Source:** ME-4 [L20] (T4+T5). **Alignment:** F2 is exactly that hook-level forbid for the banned trailer, the commit-side sibling of E1's Stop gate. **Status:** adopt.

### LAQF.F2:12 - Relations

- **Design cause (F:0):** the missing commit-hygiene gate via [[../11-fpf-diagnostic]] D2 — transformed by a `PreToolUse(git commit)` strip; MUST NOT read as editing commit content beyond the mechanically-checkable banned rule.
- **Measurement (R2):** instruction-adherence s1 ([[12-02-measurement-frame]] §2 card `laqf.mm.s1`).
- **Method family:** `MF-1` (deterministic forbid — `PreToolUse(git commit)` trailer strip), the canonical instance under C5.
- **Coordinates with:** C5 (the classifier that governs this `MF-1` placement); F1 (the branch-freshness sibling in the same process / `MF-1` family); C6 / C7 / E1 / E2 (the other `MF-1` gates under C5); E3 (the judgement audit F2 is distinguished from — checkable rule vs unverifiable claim).

### LAQF.F2:End

---

## See also

- [[12-15-patterns-F-ru]] — Russian twin
- [[12-10-patterns-A]] — frozen house-style exemplar (the 13-section template F1–F2 reuse)
- [[12-12-patterns-C]] — Layer-C (Design) patterns; F:0 inherits the C:0 design contract; C5 owns the deterministic/advisory classification F1/F2 instantiate
- [[12-14-patterns-E]] — Layer-E (verification) patterns; E1 is F1's result-claim analogue, E3 is F2's advisory counterpart
- [[12-00-spine]] — keystone: §5 roster (Design kind + detection), §4.3 relation records, §4.1 edition direction
- [[12-01-source-pack]] — G.2 pack; §8 palette `LAQF.sota.iter3.palette` cited by every §11 (L-/ME-/MF-/Γ_epist ids)
- [[12-02-measurement-frame]] — detection axes (§5 pattern↔characteristic; §2 DHCMethod cards; §3 CAL bands; §4 leading/lagging)
- [[12-20-local-practice-edition]] — Layer-2 realisation of F1 (`wt sync` cadence) and F2 (`PreToolUse(git commit)` hook)
- [[_inputs/rc-digest]] — §6 Layer-F mechanisms (rc-29, rc-30)
- [[../11-fpf-diagnostic]] — D2 design-space ruling (the basis for the F:0 design contract)
- `FPF-Spec.md:65183` E.8 authoring conventions · `:65272` canonical template · `:24417` A.19 · `:42826` C.16 · `:87746` G.2
