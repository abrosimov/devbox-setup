---
tags: [claude-improvements, phase2, root-causes, fpf]
phase: 2
created: 2026-06-27
status: synthesis
method: FPF (First Principles Framework) — separate mechanism from symptom; cluster by causal layer
---

# Root causes overview — 30 mechanisms behind the symptoms

Synthesised from [[01-symptoms-inventory]] (41 symptoms), [[02-external-research]] (Anthropic + community evidence), [[03-current-config-map]] (gap analysis), [[04-reflection-evidence]] (5 behavioural mechanisms). Each root cause is a **mechanism**, not a symptom. Mechanisms are clustered by causal layer (model / harness / config / workflow / verification / process). Symptoms can map to multiple mechanisms; each mechanism justifies ≥5 fix proposals (see per-RC files).

## Layer A — Model-internal (training / architecture)

These are intrinsic to Claude 4.x weights. We can mitigate via prompting, hooks, and topology — we cannot directly change them.

| RC | Mechanism | Drives symptoms |
|---|---|---|
| [[rc-01-rlhf-pushback-loop]] | RLHF anti-sycophancy overcorrection in 4.7 → push-back, false-dichotomy, "hypothesis disproven", arguing loop | S-010, S-017, S-019, S-021 |
| [[rc-02-helpfulness-as-artefact]] | Turn output gradient pulls toward "produce a complete artefact" — delta-only feels like under-delivery | S-005, S-006, S-011, S-014, S-029 |
| [[rc-03-verbosity-task-complexity]] | 4.8 calibrates length to *perceived* task complexity — open-ended prompts → long outputs even when not warranted | S-005, S-011, S-033 |
| [[rc-04-tokenizer-densification]] | 4.7+ tokenizer charges 12-35% more tokens for same English; effective context shrunk silently | S-001 (indirectly) |
| [[rc-05-tool-calling-preference-drop]] | 4.8 favours reasoning over tool calls; fewer Reads → more speculation, lost reconnaissance | S-015, S-016, S-027 |
| [[rc-06-no-working-memory]] | No persistent working-memory mechanism; own prior draft becomes source-of-truth → fabricated facts, paraphrase drift | S-014, S-015, RC-ref-2, RC-ref-4 |
| [[rc-07-asymmetric-ask-vs-guess]] | Asking feels like stalling (no artefact); guessing feels like momentum → premature action and random assumptions | S-007, S-015, S-016 |
| [[rc-08-sycophantic-gap-filling]] | Terse user feedback projects unstated criticism → unilateral scope extension beyond what user flagged | S-012, S-013, S-029 |

## Layer B — Harness (Claude Code platform)

Behaviours of the Claude Code runtime and how it interacts with the model.

| RC | Mechanism | Drives symptoms |
|---|---|---|
| [[rc-09-long-context-soft-cliff]] | Monotonic accuracy decay — practitioner cliff at ~50-60% before autocompact at ~75-80% | S-001 |
| [[rc-10-compaction-derailment]] | Post-compact loss of task identity; agent restarts work or drops constraints; documented in April-2026 postmortem | S-001, S-013 |
| [[rc-11-claude-md-attention-budget]] | Model attends ~150 instructions; system prompt eats ~50; current effective stack 509 lines → rule drop | S-026, all instruction-adherence cases |
| [[rc-12-no-platform-brevity-cap]] | No turn-level brevity enforcement at platform level — Anthropic tried ≤25/≤100 word caps, reverted after 3% eval drop | S-005, S-011, S-033 |

## Layer C — Configuration (this user's `dot_claude/` choices)

The CLAUDE.md, skills, agents, hooks already deployed.

| RC | Mechanism | Drives symptoms |
|---|---|---|
| [[rc-13-claude-md-bloat]] | Effective CLAUDE.md stack 509 lines — 2.5×–5× over Anthropic's guidance budget | All adherence drift |
| [[rc-14-inter-asset-conflicts]] | Direct rule conflicts: "one question at a time" vs "batched"; subagent vs main-thread approval ownership; disclosure block IS preamble | S-007, S-008, S-009, S-026 |
| [[rc-15-engineering-attitude-skill-missing]] | No skill encodes Fisher's maxim, anti-false-dichotomy, shadow-mode/CBC, kill-two-birds heuristic | S-017, S-018, S-019, S-020, S-021, S-022, S-024 |
| [[rc-16-no-facts-list-scaffold]] | No skill/template prescribes `[USER]`/`[DRAFT]` facts-list scaffold; model rolls own restatement | S-014, S-015 |
| [[rc-17-advisory-only-rules]] | Brevity, reconnaissance, citation discipline encoded only as CLAUDE.md advisories — no PostToolUse / Stop / output-shape hooks | S-003, S-005, S-008, S-011 |
| [[rc-18-permission-allowlist-drift]] | `permission_auto_approve.py` does not fully cover dispatch surface (subagent Task path, some Glob/Grep edge cases) → approval fatigue | S-002, S-031 |
| [[rc-19-skill-invocation-advisory]] | `Skill` tool invocation is advisory — model can bypass and patch code directly. No PreToolUse hook detects skill-trigger match | S-028 |

## Layer D — Workflow / pipeline topology

The agent pipeline and how stages connect.

| RC | Mechanism | Drives symptoms |
|---|---|---|
| [[rc-20-waterfall-pipeline]] | Full spec → full domain → full plan → code; reality invalidates assumptions before code; no re-entry after POC | S-032, S-036 |
| [[rc-21-monolithic-and-duplicate-outputs]] | Every stage emits one giant MD + a JSON shadow; already-existing graphomania at pipeline level | S-033, S-034 |
| [[rc-22-manual-dispatch-no-roadmap]] | User manually invokes every stage; no parallelism; no roadmap/milestone tracking | S-035, S-039 |
| [[rc-23-role-boundary-violations]] | Agents decide outside their scope (TPM declares "frontend-only"; TPM reads code). No hook enforces tool/scope per agent | S-037, S-038 |

## Layer E — Output integrity / verification

How the harness validates what the agent claims.

| RC | Mechanism | Drives symptoms |
|---|---|---|
| [[rc-24-done-without-verification]] | Agent claims build/test pass without running them. No hook checks claim against tool-call history | S-027 |
| [[rc-25-citation-not-enforced]] | Bare "see d32" without path/quote slips through; no Stop hook flags unresolved references | S-003, S-008 |
| [[rc-26-no-bullshit-detector]] | No counter-evidence audit; assertions accepted at face value | S-023 |
| [[rc-27-output-ordering-not-preserved]] | Multi-item output reorders silently | S-004 |
| [[rc-28-lint-test-output-flood]] | Lint/test stdout dumped into context every run; no default `--quiet` + JSON-on-failure pattern | S-041 |

## Layer F — Process / git hygiene

Branch and commit-level discipline.

| RC | Mechanism | Drives symptoms |
|---|---|---|
| [[rc-29-no-master-pull-protocol]] | No mechanism pulls fresh master into branch after commit; branches drift | S-025 |
| [[rc-30-coauthor-trailer-leak]] | "Never add Co-Authored-By" lives in CLAUDE.md only; no PreToolUse hook strips trailers from `Bash(git commit *)` | S-026 |

## Cross-cutting design observations

1. **Advisory vs deterministic.** The current setup leans heavily on CLAUDE.md / skills (advisory, ~70% adherence per Anthropic) for behavioural rules. Where the user wants reliability, deterministic mechanisms (hooks, settings.json permissions, agent `tools:` constraints) are under-utilised. Six categories have zero hook coverage (see [[03-current-config-map#4. Gaps and weaknesses]]).

2. **Bloat amplifies all other root causes.** RC-11 (Anthropic platform) and RC-13 (this user's config) compound: a model with attention budget for ~150 rules is being given a 509-line stack with internal conflicts. The conflicts are the rules the model is most likely to drop.

3. **Re-entry is the missing topology pattern.** Waterfall (RC-20), monolithic outputs (RC-21), no working-memory scaffold (RC-16), drift after compaction (RC-10) all share the same shape: information loss across phase boundaries with no mechanism to recover.

4. **Verification gap is structural.** RC-24 through RC-28 are all "agent claims X without proof". The pattern is a missing PostToolUse-call-history audit against final-message claims.

## Mapping back

- All 41 symptoms in [[01-symptoms-inventory]] are covered by ≥1 root cause.
- All 5 behavioural mechanisms in [[04-reflection-evidence]] map to RC-02, RC-06, RC-07, RC-08 (Layer A) and RC-16 (Layer C).
- All Anthropic-acknowledged regressions in [[02-external-research#R1]] map to RC-01, RC-03, RC-05, RC-09, RC-10, RC-12.

## See also

- [[00-MoC]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
