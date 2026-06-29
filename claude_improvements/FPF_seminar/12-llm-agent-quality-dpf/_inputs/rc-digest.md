---
tags: [claude-improvements, fpf-seminar, laqf, dpf-input, rc-digest]
created: 2026-06-28
status: input
role: Working digest of the 30 root causes plus the shared measurement frame. Consumed by S2–S6 authoring so per-pattern sessions need not re-read all 30 source files.
sources:
  - "[[../../10-root-causes-overview]]"
  - "[[../../01-symptoms-inventory]]"
  - "[[../../02-external-research]]"
  - "[[../../04-reflection-evidence]]"
  - "[[../../FPF_seminar/11-fpf-diagnostic]]"
---

# RC digest — 30 mechanisms, layer kinds, and the shared measurement frame

Distilled from the catalogue for LAQF authoring. Each entry is a **mechanism** (cause), not a symptom. The FPF kind column applies the `11-fpf-diagnostic` D2 ruling: Layer A is a **Law** (design within, mitigate effects only); Layer B is an **environment boundary** (adapt; propose upstream); Layers C–F are **design-space** (direct transformation via Work). The pattern-ID column is the provisional LAQF mapping, finalised by F.18 in S1.

## §1 Layer A — Model-internal (Laws / Constraints, A.6.B-L)

Intrinsic to Claude 4.x weights. Cannot be eliminated by this user; the pattern mitigates downstream effects.

| RC | Mechanism | FPF kind | Drives | Pattern |
|---|---|---|---|---|
| rc-01-rlhf-pushback-loop | RLHF anti-sycophancy overcorrection → push-back, false-dichotomy, "hypothesis disproven", arguing loop | Law | S-010, S-017, S-019, S-021 | **A1** Substance-Gated Pushback |
| rc-02-helpfulness-as-artefact | Turn-output gradient pulls toward "produce a complete artefact"; delta-only feels like under-delivery | Law | S-005, S-006, S-011, S-014, S-029 | **A2** Delta Over Whole-Artefact |
| rc-03-verbosity-task-complexity | Length calibrated to *perceived* task complexity; open-ended prompts → long outputs unwarranted | Law | S-005, S-011, S-033 | **A3** Answer-Budget Before Prose |
| rc-04-tokenizer-densification | 4.7+ tokenizer charges 12–35% more tokens for same English; effective context shrinks silently | Law | S-001 (indirect) | **A4** Effective-Fill Accounting |
| rc-05-tool-calling-preference-drop | Favours reasoning over tool calls; fewer Reads → more speculation, lost reconnaissance | Law | S-015, S-016, S-027 | **A5** Read Before Assert |
| rc-06-no-working-memory | No persistent working memory; own prior draft becomes source-of-truth → fabricated facts, paraphrase drift | Law | S-014, S-015 | **A6** User-Anchored Facts Over Self-Draft |
| rc-07-asymmetric-ask-vs-guess | Asking feels like stalling (no artefact); guessing feels like momentum → premature action, random assumptions | Law | S-007, S-015, S-016 | **A7** Reconnaissance Before Action |
| rc-08-sycophantic-gap-filling | Terse feedback projects unstated criticism → unilateral scope extension beyond what user flagged | Law | S-012, S-013, S-029 | **A8** Literal Scope On Terse Feedback |

## §2 Layer B — Harness (environment boundary)

Claude Code runtime behaviour. Adapt to; some warrant upstream proposals.

| RC | Mechanism | FPF kind | Drives | Pattern |
|---|---|---|---|---|
| rc-09-long-context-soft-cliff | Monotonic accuracy decay; practitioner cliff ~50–60% before autocompact ~75–80% | Boundary | S-001 | **B1** Rotate Before The Cliff |
| rc-10-compaction-derailment | Post-compact loss of task identity; agent restarts work or drops constraints | Boundary | S-001, S-013 | **B2** Authoritative Handoff Re-Entry |
| rc-11-claude-md-attention-budget | Model attends ~150 instructions; system prompt eats ~50; 509-line stack → rule drop | Boundary | S-026, all adherence cases | **B3** Attention-Budget Ledger |
| rc-12-no-platform-brevity-cap | No turn-level brevity enforcement; Anthropic tried ≤25/≤100 caps, reverted after 3% eval drop | Boundary | S-005, S-011, S-033 | **B4** Self-Imposed Output Budget |

## §3 Layer C — Configuration (design-space)

The CLAUDE.md, skills, agents, hooks already deployed. Directly transformable.

| RC | Mechanism | FPF kind | Drives | Pattern |
|---|---|---|---|---|
| rc-13-claude-md-bloat | Effective CLAUDE.md stack 509 lines — 2.5×–5× over Anthropic guidance budget | Design | all adherence drift | **C1** Instruction-Stack Within Budget |
| rc-14-inter-asset-conflicts | Direct rule conflicts (one-question vs batched; subagent vs main approval; disclosure block IS preamble) | Design | S-007, S-008, S-009, S-026 | **C2** Single-Owner Rule Resolution |
| rc-15-engineering-attitude-skill-missing | No skill encodes Fisher's maxim, anti-false-dichotomy, shadow-mode/CBC, kill-two-birds heuristic | Design | S-017–S-022, S-024 | **C3** Encoded Engineering Posture |
| rc-16-no-facts-list-scaffold | No template prescribes `[USER]`/`[DRAFT]` facts-list scaffold; model rolls own restatement | Design | S-014, S-015 | **C4** Tagged Facts Scaffold |
| rc-17-advisory-only-rules | Brevity, reconnaissance, citation discipline encoded only as advisories — no PostToolUse/Stop/output-shape hooks | Design | S-003, S-005, S-008, S-011 | **C5** Deterministic Over Advisory |
| rc-18-permission-allowlist-drift | `permission_auto_approve.py` does not fully cover dispatch surface → approval fatigue | Design | S-002, S-031 | **C6** Whole-Path Permission Coverage |
| rc-19-skill-invocation-advisory | `Skill` invocation advisory — model can bypass and patch code directly; no PreToolUse trigger-match hook | Design | S-028 | **C7** Enforced Skill Invocation |

## §4 Layer D — Workflow / pipeline topology (design-space)

| RC | Mechanism | FPF kind | Drives | Pattern |
|---|---|---|---|---|
| rc-20-waterfall-pipeline | Full spec → domain → plan → code; reality invalidates assumptions before code; no re-entry after POC | Design | S-032, S-036 | **D1** Re-Entry Across Phase Boundary |
| rc-21-monolithic-and-duplicate-outputs | Every stage emits one giant MD + a JSON shadow; pipeline-level graphomania | Design | S-033, S-034 | **D2** Atomic Single-Form Emission |
| rc-22-manual-dispatch-no-roadmap | User manually invokes every stage; no parallelism; no roadmap/milestone tracking | Design | S-035, S-039 | **D3** Roadmap-Anchored Dispatch |
| rc-23-role-boundary-violations | Agents decide outside scope (TPM declares "frontend-only"; TPM reads code); no per-agent tool/scope hook | Design | S-037, S-038 | **D4** Enforced Role Lanes |

## §5 Layer E — Output integrity / verification (design-space)

| RC | Mechanism | FPF kind | Drives | Pattern |
|---|---|---|---|---|
| rc-24-done-without-verification | Agent claims build/test pass without running them; no hook checks claim vs tool-call history | Design | S-027 | **E1** Claim Requires Observed Event |
| rc-25-citation-not-enforced | Bare "see d32" without path/quote slips through; no Stop hook flags unresolved references | Design | S-003, S-008 | **E2** Enforced Citation Anchors |
| rc-26-no-bullshit-detector | No counter-evidence audit; assertions accepted at face value | Design | S-023 | **E3** Counter-Evidence Audit |
| rc-27-output-ordering-not-preserved | Multi-item output reorders silently | Design | S-004 | **E4** Input-Order Fidelity |
| rc-28-lint-test-output-flood | Lint/test stdout dumped into context every run; no default `--quiet` + JSON-on-failure | Design | S-041 | **E5** Quiet Toolchain Output |

## §6 Layer F — Process / git hygiene (design-space)

| RC | Mechanism | FPF kind | Drives | Pattern |
|---|---|---|---|---|
| rc-29-no-master-pull-protocol | No mechanism pulls fresh master into branch after commit; branches drift | Design | S-025 | **F1** Bounded Branch Freshness |
| rc-30-coauthor-trailer-leak | "Never add Co-Authored-By" in CLAUDE.md only; no PreToolUse hook strips trailers from `git commit` | Design | S-026 | **F2** Deterministic Commit Hygiene |

## §7 Shared measurement characteristics (the eight)

These are the CharacteristicSpace axes for the measurement frame (S2). Each derives from the RCs it indexes — they are **harvested**, not invented. Polarity and bands defined in `12-02-measurement-frame`.

1. **instruction-adherence** — RCs 01, 07, 08, 11, 13, 14, 17, 19, 30. Signal: "rule stated → rule violated" within a session. Sharpest probe: S-026 Co-Authored-By trailer leak (single deterministic rule). Polarity: higher-is-better.
2. **reconnaissance-depth** — RCs 05, 06, 07, 16, 25. Signal: files Read/Edited before assertion; Disclosure-block presence; `[USER]`/`[DRAFT]` fact ratio. Anchor: Laurenzo reads-per-edit 2.0 → target ≥3.0. Polarity: higher-is-better (with diminishing returns).
3. **context-integrity** — RCs 04, 06, 09, 10, 16, 28. Signal: effective fill % at the practitioner cliff; post-compaction task-identity preservation. Polarity: target-is-best (stay below cliff).
4. **sycophancy-rate** — RCs 01, 02, 08, 15. Signal: "modified version of what was asked" per 50 turns; multi-file edits triggered by single-item feedback. Polarity: lower-is-better.
5. **output-economy** — RCs 02, 03, 12, 21, 28. Signal: tokens/turn; lines/stage; tokens/Bash on passing runs. Polarity: lower-is-better (floor at task-necessary content).
6. **verification-fidelity** — RCs 24, 25, 26, 27. Signal: terminal assertions backed by an observable event; claim-without-evidence rate. Polarity: higher-is-better.
7. **attention-budget-load** — RCs 04, 11, 13, 14, 19. Signal: instruction-stack lines; conflicting rule pairs; always-on skill token ratio. Polarity: lower-is-better (ceiling target).
8. **scope-fidelity** — RCs 08, 20, 22, 23, 27. Signal: edit-target overlap with user-named scope; out-of-lane calls; pipeline re-entry events. Polarity: higher-is-better.

## §8 SoTA anchors (from `02-external-research`)

Operational reference values for bands and acceptance signals:

- **IFScale** — 68 % instruction-following accuracy at 500 instructions (R5). Backs `attention-budget-load` ceiling.
- **Laurenzo** — reads-per-edit fell 6.6 → 2.0 across model generations (R2.2). Backs `reconnaissance-depth` target ≥3.0.
- **MRCR v2** — 93 % → 76 % accuracy as context grows 256K → 1M (R4.4). Backs `context-integrity` cliff.
- **Tokenizer densification** — ~30 % denser per same English (R1.4). Backs `context-integrity` / `output-economy`.
- **Anthropic brevity cap** — reverted ≤25/≤100 word caps after a 3 % eval drop (R2.1). Backs `output-economy` floor (do not over-clamp).
- **CLAUDE.md adherence ceiling** — advisory rules plateau ~70 % (R3.2). Backs `C5` (deterministic over advisory) and `instruction-adherence`.
- **Current instruction stack** — 509 lines = UAP 216 + devbox-setup 196 + workspace 97 (measured). Backs `C1` numeric trim target and `attention-budget-load` baseline.

## §9 Provenance note

Layer/mechanism text is lifted from `10-root-causes-overview` (authoritative). FPF-kind column applies `11-fpf-diagnostic` §D2. The eight characteristics and SoTA anchors were synthesised in S0 reconnaissance (2026-06-28) and cross-checked against `02-external-research`. Provisional pattern titles are placeholders pending the F.18 naming run in S1.
