# Routed Cue Set — Claude Tuning

**Status:** candidate route set enumerated; W1 selected (RI1 + RI2). W2-W5 remain candidate-only.
**Date:** 2026-07-21.
**FPF grounding:** shaped as `RoutedCueSet` (B.4.1). Discharges `CC-B.4.1-2` (`candidateRouteSet` named). `routeDecision` / `selectedRoute` / `routeRationale` — recorded per wave, not up-front.

## sourceCuePackRef

`problem_cards.md` — 8 problem cards (PC1-PC8) as `U.PreArticulationCuePack`.

## candidateRouteSet — 13 routes across 4 families

### Structural family (config shape)

| ID | Route | Cost |
|---|---|---|
| **RS1** | Add `problem:` + `related:` optional fields to skill/agent frontmatter | Low |
| **RS2** | Generate `SKILLS-INDEX.md` cross-index from the `related:` graph | Low |
| **RS3** | Split UAP into a thin always-on top layer + drilldown into skills | Med |
| **RS4** | Small meta-library (5-10 patterns, full Alexander template) documenting cross-cutting protocols | Low |
| **RS5** | Extend `make validate-claude` to validate `related:` links | Low |

### Content family (rule shape inside artefacts)

| ID | Route | Cost |
|---|---|---|
| **RC1** | Replace "Restated intent" → "Understood ask" (quote-back + concrete parse); fires only on non-trivial parse | Low |
| **RC2** | Retire "Assumptions" slot; add rule *"seek evidence when verifiable in one grep/read/LSP"* | Low |
| **RC3** | Retire checkpoint format as template | Low |
| **RC4** | Retire ban-list from `synthesis_and_proposal.md` §1; replace with one line *"Reader sees results, not process"* | Low |
| **RC5** | Add persistence clause: *"match reply scope to ask scope; do not stop mid-ask to prompt about items already in it"* | Low |
| **RC6** | Add compound-ask placement rule (answer at end of reply, not above the tool-call log) | Low |

### Mechanical family (hooks)

| ID | Route | Cost |
|---|---|---|
| **RM1** | PreToolUse hook denying Edit/Write/MultiEdit on `.go`/`.py`/`.ts`/`.tsx` outside a subagent chain | Med |

### Instrumentation family

| ID | Route | Cost |
|---|---|---|
| **RI1** | Rules-budget script — count imperative statements per artefact; publish aggregate | Low |
| **RI2** | Audit `alwaysApply: true` set — verify each fires for ≥80% of sessions | Low |

## Route × PC coverage matrix

Legend: **●** primary target · **○** secondary/derivative effect.

|  | PC1 evidence | PC2 intent | PC3 delegate | PC4 scope | PC5 geometry | PC6 xlink | PC7 budget | PC8 always-on |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| RS1 problem/related | | | | | | ● | ○ | |
| RS2 SKILLS-INDEX | | | | | | ● | ● | |
| RS3 split UAP | | | | | ● | | ● | |
| RS4 meta-library | | | | | | ● | | |
| RS5 validate related | | | | | | ● | | |
| RC1 Understood ask | | ● | | | ○ | | | |
| RC2 seek evidence | ● | | | | ○ | | | |
| RC3 retire checkpoint | | | | | ● | | ○ | |
| RC4 retire ban-list | | | | | ● | | ○ | |
| RC5 persistence | | | ○ | ● | | | | |
| RC6 answer at end | | | | | ● | | | |
| RM1 delegation hook | | | ● | ○ | | | | |
| RI1 rules-budget script | | | | | | | ● | ● |
| RI2 always-on audit | | | | | | | ○ | ● |

## Coverage observations

1. **PC5 (geometry)** — touched by 6 routes. It is a symptom cluster, not a single problem.
2. **PC1 (evidence)** — only RC2. Thin coverage; may need an agent-boundary hook alongside the prose rule. Flag for review after W1 baseline.
3. **PC3 (delegation)** — only RM1 (mechanical). Prior evidence: the prompt-level rule already exists and is ignored, so a hook is the only viable route.
4. **PC6 / PC7 / PC8 (structural triad)** — mostly covered by the RS family. Coherent — the new cues get structural answers.
5. **RS1 + RS2 + RI1** — mutually reinforcing: `related:` (RS1) feeds INDEX (RS2); the rules-budget script (RI1) gives a before/after metric for both.

## Forces per family

| Family | (+) | (−) |
|---|---|---|
| **RS-structural** | Once-and-done; low ongoing cost | Migration cost; non-standard frontmatter fields → cross-tool compatibility risk |
| **RC-content** | Low-cost local edits; changes measurable | Prompt-level fixes historically ignored (cf. PC3); risk of new prose bloat if applied carelessly |
| **RM-mechanical** | Hard-enforceable; cannot be bypassed | Hook maintenance; false-positives block legitimate work |
| **RI-instrumentation** | Observability without behaviour change | Requires interpretation to drive action; initial build cost |

## multiRoutePolicy — wave-based rollout

No single-shot selection. Routes are selected in waves, each producing evidence for the next.

| Wave | Routes | Rationale |
|---|---|---|
| **W1 — measure first** | RI1 → RI2 | Without metrics we cannot know whether we are actually over-budget. Cheap; baseline for everything downstream. |
| **W2 — structural quick wins** | RS1, RS2, RS5 | `related:` + INDEX + validation. The research verdict: this is the one Alexander insight the current config genuinely lacks. |
| **W3 — content edits (batch)** | RC1-RC6 | All Low cost, all on the same files (UAP + a few skills) — do in one pass. |
| **W4 — riskier structural** | RS3, RM1 | Split UAP; delegation hook. Require dry-run; wait for the W1 baseline. |
| **W5 — nice-to-have** | RS4 | Meta-library documenting cross-cutting protocols. Defer until W1-W4 stabilise. |

## Selection state (per CC-B.4.1-3)

- **W1** — **completed 2026-07-21**: RI1 → RI2. `routeRationale` for RI1: see `route_RI1_rules_budget.md`; baseline captured (`rules_budget_baseline.md`) — 119 always-on rules, under budget, 60% used. `routeRationale` for RI2: see `route_RI2_always_on_audit.md`; 46-rule demotion candidate list produced.
- **W2** — **opened 2026-07-21**: `route_W2_structural.md`. `selectedRoute = {RS1, RS2, RS5, RI2-demotions, trigger-consistency-validator}`. `routeRationale` in the deep-dive. Contains open questions Q-W2-1..3 to resolve before implementation.
- **W3-W5** — `selectedRoute` **pending**. Named as candidates only. W3 will also inherit the `project-preferences` split (Q-RI2-2 = W3 incremental). Selection at each wave requires an explicit `routeRationale` in the corresponding deep-dive file.

## Currently in analysis

**W2 open** — see `route_W2_structural.md`. Resolve Q-W2-1..3 before starting the frontmatter batch.

## Next-session start point

1. Read `problem_cards.md` (cues).
2. Read this file (routes + matrix + waves).
3. Read `route_RI1_rules_budget.md` + `rules_budget_baseline.md` (W1 output).
4. Read `route_RI2_always_on_audit.md` (W1 output — 46-rule demotion recommendation, Q-RI2-1..3 resolved).
5. Read `route_W2_structural.md` (currently open — decide Q-W2-1..3, then execute the sequencing).
