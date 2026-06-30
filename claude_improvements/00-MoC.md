---
tags: [claude-improvements, MoC, hub]
phase: 4
created: 2026-06-27
status: hub
---

# Claude Code improvements — Map of Content

Comprehensive analysis of Claude Code (Opus 4.7/4.8) behavioural problems, root causes, and concrete fix proposals. Designed to be picked up across sessions: each file is atomic, cross-linked, and self-explanatory.

## Where to start

| If you want to … | Read |
|---|---|
| See the original user complaints | [[01-symptoms-inventory]] (41 atomic symptoms with verbatim quotes) |
| See what Anthropic + community know | [[02-external-research]] (~80 cited sources) |
| See what `dot_claude/` already does, where it has gaps | [[03-current-config-map]] |
| See behavioural mechanisms from Claude's own reflection | [[04-reflection-evidence]] |
| See all 31 root causes at a glance | [[10-root-causes-overview]] |
| Pick a single root cause and start fixing | Any `rc-NN-*` file (each has ≥5 fix proposals) |
| See the prioritised action plan + agent-topology DSS (3×SE vs 1×SE) | [[20-consolidation-plan]] |

## Catalogue by causal layer

### Layer A — Model-internal (8 RCs)

Behaviours intrinsic to Claude 4.x weights. We mitigate via prompting, hooks, topology — we cannot change them.

- [[rc-01-rlhf-pushback-loop]] — anti-sycophancy overcorrection → arguing loops
- [[rc-02-helpfulness-as-artefact]] — turn-output gradient pulls toward complete artefact
- [[rc-03-verbosity-task-complexity]] — 4.8 length scales with perceived complexity
- [[rc-04-tokenizer-densification]] — 4.7+ tokenizer 12-35% denser
- [[rc-05-tool-calling-preference-drop]] — 4.8 prefers reasoning over tool calls
- [[rc-06-no-working-memory]] — own draft becomes source-of-truth
- [[rc-07-asymmetric-ask-vs-guess]] — asking feels like stalling, guessing like momentum
- [[rc-08-sycophantic-gap-filling]] — terse feedback → unilateral scope extension

### Layer B — Harness / Claude Code platform (4 RCs)

Behaviours of the runtime.

- [[rc-09-long-context-soft-cliff]] — accuracy decay at 50-60% before autocompact at 75-80%
- [[rc-10-compaction-derailment]] — task identity loss after compaction
- [[rc-11-claude-md-attention-budget]] — model attends ~150 instructions
- [[rc-12-no-platform-brevity-cap]] — Anthropic-tried hard caps hurt evals

### Layer C — Configuration (7 RCs)

This user's `dot_claude/` choices.

- [[rc-13-claude-md-bloat]] — 509 effective lines vs ~200 budget
- [[rc-14-inter-asset-conflicts]] — direct rule conflicts across skills/UAP
- [[rc-15-engineering-attitude-skill-missing]] — Fisher's maxim, anti-false-dichotomy not encoded
- [[rc-16-no-facts-list-scaffold]] — no `[USER]`/`[DRAFT]` working-memory template
- [[rc-17-advisory-only-rules]] — brevity, reconnaissance, citation only as text
- [[rc-18-permission-allowlist-drift]] — auto-approve does not cover all paths
- [[rc-19-skill-invocation-advisory]] — model bypasses `Skill` tool

### Layer D — Workflow / pipeline (4 RCs)

Agent pipeline and stage connectivity.

- [[rc-20-waterfall-pipeline]] — full spec → full domain → full plan → code, one-way
- [[rc-21-monolithic-and-duplicate-outputs]] — giant MD + JSON shadow per stage
- [[rc-22-manual-dispatch-no-roadmap]] — no parallelism, no milestone tracking
- [[rc-23-role-boundary-violations]] — TPM reads code, designer makes scope calls

### Layer E — Output integrity / verification (5 RCs)

How the harness validates agent claims.

- [[rc-24-done-without-verification]] — "tests pass" without running tests
- [[rc-25-citation-not-enforced]] — bare "see d32" slips through
- [[rc-26-no-bullshit-detector]] — counter-evidence audit absent
- [[rc-27-output-ordering-not-preserved]] — silent reordering
- [[rc-28-lint-test-output-flood]] — raw stdout floods context

### Layer F — Process / git hygiene (2 RCs)

Branch and commit discipline.

- [[rc-29-no-master-pull-protocol]] — no auto-fetch after commit
- [[rc-30-coauthor-trailer-leak]] — Co-Author ban advisory only

### Cross-layer additions

RCs that span more than one causal layer and so do not sit cleanly under one of A-F.

- [[rc-31-agent-satisficing]] — workarounds in code instead of root-cause fix in config (Layer C primary, Layer E spillover). Captures Fix 8 — DoD block, PostToolUse workaround-pattern hook, debugging diff-first protocol.

## Symptom → root-cause cross-reference

Quick lookup for "I saw symptom S-XYZ — which RCs does it map to?". Strongest mapping listed first.

| Symptom | Primary RCs |
|---|---|
| [[01-symptoms-inventory#S-001]] context degradation past 55% | RC-09, RC-04, RC-10 |
| [[01-symptoms-inventory#S-002]] allow/deny list broken | RC-18 |
| [[01-symptoms-inventory#S-003]] cites without context | RC-25, RC-17 |
| [[01-symptoms-inventory#S-004]] wrong output order | RC-27 |
| [[01-symptoms-inventory#S-005]] 4.8 graphomania | RC-03, RC-12, RC-02 |
| [[01-symptoms-inventory#S-006]] repeats self+user | RC-02, RC-06 |
| [[01-symptoms-inventory#S-007]] asks too early | RC-07, RC-14 |
| [[01-symptoms-inventory#S-008]] questions without context | RC-25, RC-17 |
| [[01-symptoms-inventory#S-009]] burns tokens re-confirming | RC-02, RC-06 |
| [[01-symptoms-inventory#S-010]] only paraphrases | RC-01, RC-02 |
| [[01-symptoms-inventory#S-011]] pub-talk style | RC-03, RC-12 |
| [[01-symptoms-inventory#S-012]] initiative creep | RC-08, RC-02 |
| [[01-symptoms-inventory#S-013]] reframing | RC-08, RC-10 |
| [[01-symptoms-inventory#S-014]] paraphrase + odd conclusions | RC-06, RC-16 |
| [[01-symptoms-inventory#S-015]] random assumptions up front | RC-07, RC-06, RC-16 |
| [[01-symptoms-inventory#S-016]] rushes to solve | RC-07, RC-05 |
| [[01-symptoms-inventory#S-017]] push-back pattern | RC-01, RC-15 |
| [[01-symptoms-inventory#S-018]] reinvents wheels | RC-15 |
| [[01-symptoms-inventory#S-019]] developer not engineer | RC-15, RC-01 |
| [[01-symptoms-inventory#S-020]] fears stack changes | RC-15 |
| [[01-symptoms-inventory#S-021]] false dichotomies | RC-15, RC-01 |
| [[01-symptoms-inventory#S-022]] no kill-2-birds | RC-15 |
| [[01-symptoms-inventory#S-023]] no bullshit detector | RC-26 |
| [[01-symptoms-inventory#S-024]] external locus of control | RC-15 |
| [[01-symptoms-inventory#S-025]] no fresh master | RC-29 |
| [[01-symptoms-inventory#S-026]] Co-Author trailer | RC-30, RC-11, RC-13 |
| [[01-symptoms-inventory#S-027]] false done | RC-24, RC-05 |
| [[01-symptoms-inventory#S-028]] skill suppression | RC-19 |
| [[01-symptoms-inventory#S-029]] no proactive options | RC-08, RC-02 |
| [[01-symptoms-inventory#S-030]] command shadowing | (existing `techne-` prefix policy adequate) |
| [[01-symptoms-inventory#S-031]] git push friction | RC-18 |
| [[01-symptoms-inventory#S-032]] waterfall | RC-20 |
| [[01-symptoms-inventory#S-033]] monolithic outputs | RC-21, RC-03 |
| [[01-symptoms-inventory#S-034]] MD+JSON duplication | RC-21 |
| [[01-symptoms-inventory#S-035]] manual dispatch | RC-22 |
| [[01-symptoms-inventory#S-036]] no re-entry after POC | RC-20 |
| [[01-symptoms-inventory#S-037]] TPM reads code | RC-23 |
| [[01-symptoms-inventory#S-038]] scope decisions out of lane | RC-23 |
| [[01-symptoms-inventory#S-039]] no roadmaps | RC-22 |
| [[01-symptoms-inventory#S-040]] no out-of-CLI feedback | (no RC — feature, not bug) |
| [[01-symptoms-inventory#S-041]] lint/test output flood | RC-28 |
| [[01-symptoms-inventory#S-018]] reinvents wheels (also: workaround helpers `_absolutise_*`) | RC-15, **RC-31** |
| [[01-symptoms-inventory#S-024]] external locus of control (also: env-prefix patch instead of config fix) | RC-15, **RC-31** |
| [[01-symptoms-inventory#S-027]] false done (also: declared fixed via workaround) | RC-24, RC-05, **RC-31** |

## How to use this catalogue across sessions

The catalogue is designed for incremental work over weeks. Each `rc-NN-*.md` is self-contained: pick one, implement one or more of its fixes, mark in the file. Suggested workflow:

1. **Triage.** Skim [[10-root-causes-overview]]. Pick the RC with the highest impact-for-your-pain combination. Layer C (config) and Layer E (verification) fixes are usually quickest to land.
2. **Plan.** Inside the RC file, the 5+ fixes are tagged with effort/impact/risk. Pick 1-3 fixes. The hygiene rules guarantee at least 1 is no-code (settings/CLAUDE.md/agent-frontmatter only) so you have a cheap starting move.
3. **Execute.** Most fixes touch one of: `settings.json`, `hooks.json`, a `bin/*.py` script, a `skills/*/SKILL.md`, an `agents/*.md` frontmatter, a `commands/techne-*.md`. Asset surface vocabulary in [[_writer-instructions#Asset surface vocabulary]].
4. **Validate.** Each RC file ends with an "Acceptance signal" section — concrete observable outcomes. Use as eval input.
5. **Cross-link follow-ups.** When implementing fix `RC-XX.FN`, link the resulting commit/PR back to this catalogue.

## Fix surface frequency (across all 30 RCs)

Approximate distribution of fix surfaces proposed (helps prioritise infrastructure work):

- **New / extended hooks**: highest frequency. Most RCs include a PreToolUse, PostToolUse, or Stop hook.
- **New skills**: ≤1 per RC by design. Total ~25 new skills proposed. Heavy concentration in: `engineering-attitude` (RC-15), `working-memory-discipline` (RC-16), `delta-discipline` (RC-02), `citation-discipline` (RC-25), `counter-evidence-audit` (RC-26).
- **Output-styles**: ~15 new output-styles proposed. The single highest-leverage infrastructure to build is a robust output-style harness — many fixes ride on it.
- **settings.json edits**: ~12 fixes touch `permissions`, `env`, or `enabledPlugins`.
- **CLAUDE.md / USER_AUTHORITY_PROTOCOL.md edits**: ~10 fixes — mostly trims and section moves (RC-11, RC-13).
- **Per-agent `tools:` tightening**: ~8 fixes — small, high-leverage.
- **New commands**: ~10 new `techne-*` commands proposed.
- **Templates**: ~5 new templates (`facts-list.md`, `session-handoff.md`, etc.).

## Cross-cutting recommendations

Lifted from [[10-root-causes-overview#Cross-cutting design observations]]:

1. **Move from advisory to deterministic.** The current setup relies on CLAUDE.md / skills (~70% adherence) for most behavioural rules. Where reliability matters, deterministic mechanisms (hooks, settings.json permissions, agent `tools:` constraints) need more weight.
2. **Bloat compounds all other root causes.** Trim CLAUDE.md ([[rc-11-claude-md-attention-budget]], [[rc-13-claude-md-bloat]]) before piling on new rules.
3. **Re-entry is the missing topology.** Waterfall, monolithic outputs, no working-memory scaffold, drift after compaction all share the same shape — information loss across phase boundaries.
4. **Verification gap is structural.** RCs 24-28 are all "agent claims X without proof". The pattern is a missing PostToolUse-call-history audit against final-message claims.

## Sources not yet exploited

[[02-external-research#R6]] adds 39 new citations including:
- **IFScale (arXiv 2507.11538)** — quantitative instruction-following ceiling (68% at 500 instructions). Hardest evidence for RC-11, RC-13.
- **GH #7777** — verbatim "advisory rather than mandatory after 2-5 prompts". Mechanism for RC-17.
- **GH #45704** — Claude Code's own system prompt contains "Output Efficiency" that fights user CLAUDE.md verbosity rules. Mechanism for RC-13.
- **Anthropic "Writing tools for agents"** — `ResponseFormat` enum cut Slack tool output 206 → 72 tokens. Concrete pattern for RC-28.
- **Silicon Mirror (arXiv 2604.00478)** — 85.7% sycophancy reduction via dynamic gating; warns against contrarian over-correction. Mechanism for RC-01.

These would expand fix proposals in those RCs in a follow-up pass.

## Inventory

- **Phase 1 evidence (4 files)**: symptoms, external research, config map, behavioural reflection. ~1144 lines.
- **Phase 2 synthesis (1 file)**: root-causes overview. 107 lines.
- **Phase 3 fix files (31 files)**: one per RC, ~115 lines avg. ~3600 lines.
- **Phase 4 hub (this file) + consolidation plan**: navigation + [[20-consolidation-plan]] (prioritised tranches + agent-topology DSS).
- **Internal: `_writer-instructions.md`** (194 lines) — template + asset vocabulary used by writer agents.

Total: 38 files, ~5300 lines. Compact-per-file, indexed, cross-linked.

## Κάτοπτρον — FPF seminar

Full timeline: [[FPF_Seminar/seminar_timeline]]

| # | File | Focus |
|---|------|-------|
| 0 | [[FPF_Seminar/choosing_name]] | Project naming via FPF criteria. Decided: **Κάτοπτρον**. |
| 1 | [[FPF_Seminar/11-fpf-diagnostic]] (EN) · [[FPF_Seminar/11-fpf-diagnostic-ru]] (RU) | A.7 / A.6.B / C.16 audit: solution-contradicts-diagnosis, Laws vs Work, missing baselines, no WorkPlan DAG. |
| 2 | [[FPF_Seminar/choosing_name_with_fpf_48]] (EN) · [[FPF_Seminar/choosing_name_with_fpf_48-ru]] (RU) | Naming re-run through **F.18**: Name Card, 7-candidate set, ordinal NQD-front. Independently confirms **Κάτοπτρον**. |
| 3 | [[FPF_Seminar/12-llm-agent-quality-dpf/README]] (EN+RU twins) | **LAQF** — a two-layer **Domain Principle Framework** (`E.4.DPF`): 30 context-independent quality patterns (E.8) across six causal layers + an A.19/C.16 measurement frame (Layer 1), plus this user's `dot_claude/` realisation (Layer 2). Lands as a local monolith — never into FPF Core. F.18-ratified name; G.2 source pack; E.21/E.19 quality + admission notes. |

## See also

- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- [[10-root-causes-overview]]
- [[Список типовых сбоев в AI-native разработке]]
