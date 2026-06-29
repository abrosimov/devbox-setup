---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, local-practice-edition, e4-pfr, e53]
seminar-iteration: 3
created: 2026-06-28
status: local-practice-edition
method: FPF E.4.PFR (relation/edition records) · E.5.3 (unidirectional dependency) · G.11 (currentness) · consumes 03-current-config-map (realisation ground truth)
framework: LAQF — LLM-Agent Quality Principle Framework (Layer-2 Local Practice edition)
language-twin: "[[12-20-local-practice-edition-ru]]"
---

# LAQF — Layer-2 Local Practice edition (this user's `dot_claude/` realisation)

This is the **Layer-2 Local Practice edition** of LAQF: the concrete realisation of the thirty Layer-1 Domain patterns ([[12-10-patterns-A]] … [[12-15-patterns-F]]) in **this user's deployed `dot_claude/` configuration** — its hooks, skills, agents, commands, settings, and the `USER_AUTHORITY_PROTOCOL.md` it ships as `~/.claude/CLAUDE.md`. Where the Domain edition states *what* quality property must hold, this edition records *how* (and *whether*) it is currently realised, grounded in the ground-truth snapshot [[../../03-current-config-map]].

Per `E.5.3` (`FPF-Spec.md:64835`) the dependency is **strictly upward and acyclic**: the Local Practice edition depends on the Domain edition (LAQF), which depends on FPF Core — and never the reverse. A Domain pattern change does not silently rewrite this config; it raises a *refresh line* (`G.11` T4, [[12-00-spine]] §6). Equally, this realisation — however complete or incomplete — **writes nothing back into the Domain edition or FPF Core** (`E.5.3` CC-UD.1/2, `FPF-Spec.md:64890`). The edition is therefore allowed to **lag** the Domain edition, and §2 records that lag honestly: of the thirty patterns, this configuration fully realises a few, partially realises most, and leaves nine as open gaps — and that gap set *is* the improvement backlog (§5).

This is an **edition / relation** artefact, not a pattern catalogue: it creates no new `E.8` patterns and re-paraphrases no source — it wires existing Local assets to existing Domain patterns by id (`E.4.PFR`, `FPF-Spec.md:64478`).

## §0 Edition declaration (E.4.PFR)

| Slot | Declaration |
|---|---|
| **Edition** | `LAQF-Local v0.1` — Layer-2 Local Practice edition. |
| **Bounded context** | `AION_AUTOPOIESEON` workspace → this user's deployed `~/.claude/` (source: `roles/devbox/files/dot_claude/`). |
| **Realised subject** | The thirty Layer-1 LAQF patterns, instantiated as concrete hooks / skills / agents / commands / settings / protocol sections. |
| **Depends on** | `LAQF v0.1` (Domain edition); transitively FPF Core (`FPF-Spec.md`). Upward, acyclic (`E.5.3`). |
| **Edition status** | `build-with-gaps` — 2 realised (✅), 19 partial (◐), 9 gap (⬜); see §2. |
| **Ground truth** | [[../../03-current-config-map]] (inventory, gap analysis, inter-asset conflicts, instruction-stack size). |
| **Non-use boundary** | Not a re-statement of the Domain patterns, not a patch to FPF Core, not a runtime/build artefact — a reading map from Local assets to Domain ids. |

---

## §1 Edition dependency record (E.4.PFR + E.5.3)

The authoritative Local-side `FrameworkEditionDependencyRecord`, extending the representative one fixed in [[12-00-spine]] §4.2.

```text
FrameworkEditionDependencyRecord@Context:                # Local → Domain (+ Core)
  frameworkEditionRef:          LAQF-Local v0.1 (Layer-2 Local Practice edition)
  dependsOnEditionRefs:         LAQF v0.1 (Domain edition); transitively FPF Core (FPF-Spec.md)
  dependencyReason:             the dot_claude realisation instantiates Domain patterns as
                                concrete hooks (hooks.json), skills, agents, commands,
                                settings.json, and the USER_AUTHORITY_PROTOCOL.md shipped as
                                ~/.claude/CLAUDE.md
  compatibilityBoundary:        the Local edition MAY lag the Domain edition; a Domain pattern
                                change does NOT silently rewrite this config — it raises a
                                refresh line (§5 / G.11 T4). Current lag = 19 partial + 9 gap
                                of 30 (§2). The lag is admissible precisely because the
                                dependency is one-directional.
  deprecationOrSupersessionRefs: —
  refreshConditionRefs:         §5 (G.11 T4 — dot_claude config drift); also Domain pattern
                                change ([[12-00-spine]] §6 T1–T3)
  e53ConformanceNote:           Local → Domain → Core; acyclic; no back-edge. This realisation
                                writes nothing into the Domain edition or FPF Core
                                (CC-UD.1/2, FPF-Spec.md:64890). Gaps are a lag, not a
                                back-pressure on the Domain patterns.
```

---

## §2 Realisation map — 30 Domain patterns → `dot_claude/` assets

Status legend: **✅** realised (deterministic / fully encoded) · **◐** partial (advisory or incomplete) · **⬜** gap (no realisation, or a Domain-led property the config has not yet built). "Family" is the `MF-` method family ([[12-01-source-pack]] §6) the Local asset realises (or would, if built). Realisation facts and gap citations are from [[../../03-current-config-map]] (section refs in the right column).

### §2.A Layer A — Laws (mitigations)

| LAQF | Domain pattern | Local realisation (asset) | Family | Status |
|---|---|---|---|---|
| **A1** | Substance-Gated Pushback | UAP `§Helpfulness`, `§Voice`; `proposal_discipline.py` (nudge). Engineering-posture skill (Fisher's maxim) **missing** ([[../../03-current-config-map]] §3.5). | MF-2 | ◐ |
| **A2** | Delta Over Whole-Artefact | UAP `§Voice` iteration/delta mode; `proposal_discipline.py` nudges delta-over-rewrite (§3.2). | MF-2/MF-6 | ◐ |
| **A3** | Answer-Budget Before Prose | UAP `§Voice` default fact-density. No PostStop line-count gate (§3.2 gap). | MF-2 | ◐ |
| **A4** | Effective-Fill Accounting | `settings.json:12` `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`; `pre_compact_mask.py`; `iterative-retrieval` skill. No ≥50% early-fill warning (§4.3.1 gap). | MF-3 | ◐ |
| **A5** | Read Before Assert | `lsp-navigation` / `lsp-tools` skills; `pre_write_existing_guard.py` (Write only, §3.8). | MF-2 | ◐ |
| **A6** | User-Anchored Facts Over Self-Draft | UAP cite rule; `code-writing-protocols`. No `[USER]`/`[DRAFT]` scaffold (§3.6 gap). | MF-4 | ◐ |
| **A7** | Reconnaissance Before Action | UAP `§Inquiry` reconnaissance ladder + Disclosure block; `proposal_discipline.py` (UserPromptSubmit + Stop). | MF-2 | ◐ |
| **A8** | Literal Scope On Terse Feedback | UAP `§Proposal ≠ Approval`; `self-contained-options` skill. | MF-2 | ◐ |

### §2.B Layer B — Harness boundary

| LAQF | Domain pattern | Local realisation (asset) | Family | Status |
|---|---|---|---|---|
| **B1** | Rotate Before The Cliff | `settings.json:12` autocompact 80%; `session_save.py`; `pre_compact_mask.py`. 80% is past the 50–60% practitioner cliff (§4.3.1 gap). | MF-3 | ◐ |
| **B2** | Authoritative Handoff Re-Entry | `session_save.py` (PreCompact + SessionEnd) + progress spine (`bin/progress`) — durable state externalisation. | MF-4 | ✅ |
| **B3** | Attention-Budget Ledger | No mechanism tracks instruction-stack load; 509-line stack measured but unmanaged (§6, §4.3 gap). | MF-4 | ⬜ |
| **B4** | Self-Imposed Output Budget | UAP `§Voice` brevity modes. No PostStop output-size gate (§3.2 gap). | MF-6 | ◐ |

### §2.C Layer C — Configuration

| LAQF | Domain pattern | Local realisation (asset) | Family | Status |
|---|---|---|---|---|
| **C1** | Instruction-Stack Within Budget | Effective stack = **509 lines** (UAP 216 + project 196 + workspace 97), 2.5×–5× over budget; **not yet trimmed** (§6). | MF-6 | ⬜ |
| **C2** | Single-Owner Rule Resolution | Four inter-asset conflicts unresolved (one-question vs batched; subagent vs main approval; disclosure-block-is-preamble) (§5). | MF-4 | ⬜ |
| **C3** | Encoded Engineering Posture | No skill encodes Fisher's maxim / anti-false-dichotomy / shadow-CBC / kill-two-birds; `fpf-thinking` opt-in only (§3.5). | MF-2 | ⬜ |
| **C4** | Tagged Facts Scaffold | No `[USER]`/`[DRAFT]`/`[FILE path:line]` template; model rolls own restatement (§3.6). | MF-4 | ⬜ |
| **C5** | Deterministic Over Advisory | `hooks.json` (PreToolUse/PostToolUse/Stop layer) + `hooks-architecture` skill realise the meta-pattern partially; many rules still advisory (§3.15, §7). | MF-1 | ◐ |
| **C6** | Whole-Path Permission Coverage | `permission_auto_approve.py` (PermissionRequest) + `techne-fewer-permission-prompts` skill; still prompting on routine paths (§4.3.13). | MF-1 | ◐ |
| **C7** | Enforced Skill Invocation | `validate_skill_evals.py` (partial coverage); no PreToolUse trigger-match hook blocking bypass (§3.14 gap). | MF-1 | ⬜ |

### §2.D Layer D — Workflow / pipeline topology

| LAQF | Domain pattern | Local realisation (asset) | Family | Status |
|---|---|---|---|---|
| **D1** | Re-Entry Across Phase Boundary | `pre_plan_code_guard.py`; techne workflow commands; `workflow` skill — plan↔code gate. Manual re-entry (§3.3). | MF-3 | ◐ |
| **D2** | Atomic Single-Form Emission | `structured-output` skill. Pipeline still emits one giant MD + a JSON shadow per stage (§3, the rc-21 problem). | MF-6 | ◐ |
| **D3** | Roadmap-Anchored Dispatch | `bin/progress` spine + techne commands; dispatch still manual, no parallelism roadmap (§3). | MF-5/MF-4 | ◐ |
| **D4** | Enforced Role Lanes | Per-agent `tools:` frontmatter restricts the tool lane at dispatch (28 agents). No per-agent edit-scope runtime hook (§3.7). | MF-5 | ✅ |

### §2.E Layer E — Output integrity / verification

| LAQF | Domain pattern | Local realisation (asset) | Family | Status |
|---|---|---|---|---|
| **E1** | Claim Requires Observed Event | `stop_lint_gate.py`, `stop_format.py`, `post_edit_lint.py`. No hook validates a claimed test/build pass against an executed run (§3.15 gap). | MF-1 | ◐ |
| **E2** | Enforced Citation Anchors | UAP cite rule advisory only; no Stop hook flags bare "see d32" references (§3.12 gap). | MF-1 | ⬜ |
| **E3** | Counter-Evidence Audit | `code-reviewer` + `go-review-checklist`; `fpf-thinking` opt-in. No general counter-evidence audit (§3.9). | MF-2 | ◐ |
| **E4** | Input-Order Fidelity | Zero coverage — no mechanism preserves/verifies output order (§3.11 gap). | MF-6 | ⬜ |
| **E5** | Quiet Toolchain Output | `pre_bash_toolchain_guard`. No default `--quiet` + JSON-on-failure across the toolchain (§3.1 / rc-28 gap). | MF-6 | ◐ |

### §2.F Layer F — Process / git hygiene

| LAQF | Domain pattern | Local realisation (asset) | Family | Status |
|---|---|---|---|---|
| **F1** | Bounded Branch Freshness | `wt sync` fish function reconciles a worktree with its sync-source (manual); **no freshness gate** verifies branch-behind at integration (S-025 zero coverage, §3.10). | MF-1 | ⬜ |
| **F2** | Deterministic Commit Hygiene | UAP `§Git Commits` trailer ban (advisory) + `settings.json` `permissions.deny` blocks destructive git + `git_safe_commit.py`. **No** `PreToolUse(git commit)` trailer-strip hook (S-026 relies on adherence, §3.10). | MF-1 | ◐ |

**Tally:** ✅ 2 (B2, D4) · ◐ 19 · ⬜ 9 (B3, C1, C2, C3, C4, C7, E2, E4, F1). The nine gaps are the realisation backlog (§5); the partials are the deterministic-over-advisory (C5) upgrade surface.

---

## §3 Pattern-framework relation records (E.4.PFR)

Representative `PatternFrameworkRelationRecord`s wiring Local realisations to their governing Domain patterns — one per realisation class (✅ realised, ◐ partial, ⬜ Domain-led gap), mirroring the spine's representative-records method ([[12-00-spine]] §4.3). Each pattern's full realisation row is in §2; the per-record `blockedStrongerReading` enforces the `E.5.3` direction.

```text
LR1  PatternFrameworkRelationRecord@Context:                       # realised
  relationId: LAQF-Local.R.b2-handoff
  sourceRef: session_save.py (PreCompact+SessionEnd) + bin/progress spine
  targetRef: LAQF.B2 (Authoritative Handoff Re-Entry)
  relationFunction: realisation (Local instantiation of a Domain pattern)
  governedUse: the Local hooks instantiate B2's MF-4 state-externalisation; durable
               handoff survives compaction/session-end
  directGoverningPatternRef: LAQF.B2   dependencyOrEditionEffect: Local → Domain, upward
  blockedStrongerReading: the hook realising B2 MUST NOT read as redefining B2; Domain
               states what, the hook is one realisation of how
  refreshOrSupersessionCondition: session_save.py / progress schema change → refresh §2.B

LR2  relationId: LAQF-Local.R.d4-lanes                              # realised (scoped)
  sourceRef: per-agent `tools:` frontmatter across 28 agents
  targetRef: LAQF.D4 (Enforced Role Lanes)
  relationFunction: realisation (partial scope — tool lane only)
  governedUse: agent frontmatter restricts the MF-5 tool lane at dispatch
  directGoverningPatternRef: LAQF.D4   dependencyOrEditionEffect: Local → Domain, upward
  blockedStrongerReading: a tool-lane restriction is NOT a per-agent edit-scope runtime
               hook; the lane is tool-level, not scope-level (the §3.7 residual)
  refreshOrSupersessionCondition: agent roster / tools change → refresh §2.D

LR3  relationId: LAQF-Local.R.c5-hooks                              # partial (the meta-surface)
  sourceRef: hooks.json (PreToolUse/PostToolUse/Stop) + hooks-architecture skill
  targetRef: LAQF.C5 (Deterministic Over Advisory)
  relationFunction: realisation (partial — the MF-1 surface exists, coverage incomplete)
  governedUse: the hook layer is the Local realisation surface for every other MF-1 gate
               (C6, C7, E1, E2, F1, F2); C5 classifies which advisory rules earn a hook
  directGoverningPatternRef: LAQF.C5   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: an existing hook layer does NOT mean every must-hold rule is
               hooked; the lag is the un-hooked advisory rules (§2 ◐/⬜ rows)
  refreshOrSupersessionCondition: each closed gap adds an MF-1 hook → refresh §2

LR4  relationId: LAQF-Local.R.f2-trailer-gap                        # Domain-led gap (canonical lag)
  sourceRef: UAP §Git Commits (advisory ban) + settings.json permissions.deny (destructive git)
  targetRef: LAQF.F2 (Deterministic Commit Hygiene)
  relationFunction: realisation (incomplete — the MF-1 trailer-strip is unbuilt)
  governedUse: the Domain F2 specifies a PreToolUse(git commit) strip; the Local edition
               realises only the advisory ban + destructive-git deny, not the strip
  directGoverningPatternRef: LAQF.F2   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: the missing hook does NOT weaken the Domain F2 pattern; the gap
               is a Local lag, not a back-pressure on Domain (E.5.3 CC-UD.1/2)
  refreshOrSupersessionCondition: author the PreToolUse(git commit) trailer-strip → close
               the gap (§5 / G.11 T4)

LR5  relationId: LAQF-Local.R.f1-freshness-gap                      # Domain-led gap
  sourceRef: wt sync fish function (manual reconcile; no freshness gate)
  targetRef: LAQF.F1 (Bounded Branch Freshness)
  relationFunction: realisation (incomplete — corrective tool exists, gate unbuilt)
  governedUse: wt sync is the reconcile action; F1's integration-point freshness check is
               not realised (S-025 zero coverage)
  directGoverningPatternRef: LAQF.F1   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: the presence of wt sync does NOT satisfy F1; the gate (verify
               branch-behind at integration) is the missing part
  refreshOrSupersessionCondition: author a freshness gate over wt sync → close the gap (§5)

LR6  relationId: LAQF-Local.R.e4-order-gap                          # Domain-led gap (zero coverage)
  sourceRef: (none — §3.11 zero coverage)
  targetRef: LAQF.E4 (Input-Order Fidelity)
  relationFunction: realisation (absent — Domain property with no Local asset)
  governedUse: Domain E4 specifies an output-order check; the Local edition has none
  directGoverningPatternRef: LAQF.E4   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: the absence of a realisation does NOT remove the Domain E4
               pattern; it records a lag to be closed
  refreshOrSupersessionCondition: author an output-order check → close the gap (§5)
```

---

## §4 Framework package manifest (Local edition)

```text
FrameworkPackageManifest@Context:
  frameworkEditionRef:           LAQF-Local v0.1 (Layer-2 Local Practice edition)
  selectedPatternSetPublicationRef: §2 realisation map (30 Domain patterns → dot_claude assets)
  relationRecordRefs:            §3 LR1–LR6 (realised / partial / gap classes); full per-pattern
                                 realisation rows in §2.A–§2.F
  dependencyAndEditionRecordRefs: §1 (Local → Domain + Core); [[12-00-spine]] §4.2 (representative)
  editionStatus:                 build-with-gaps (✅ 2 · ◐ 19 · ⬜ 9 of 30)
  deprecationOrSupersessionRefs: —
  sourcePackRefs:                [[../../03-current-config-map]] (realisation ground truth);
                                 [[12-01-source-pack]] §6 (MF-family vocabulary)
  qualityEvidenceRefs:           → E.21/E.22 quality cycle, S7 ([[README]] + QA)
  refreshPlanOrCurrentnessRefs:  §5 (G.11 T4 — config drift); [[12-00-spine]] §6 (whole-framework)
  firstEntryCarrierRefs:         [[README]] (S7) + this edition file
  blockedRuntimeOrBuildReading:  LAQF-Local is a reading/authoring edition mapping deployed
                                 assets to Domain ids — it creates no imports, APIs, runtime
                                 deps, or build semantics; the assets it names have runtime
                                 effect, the manifest does not (FPF-Spec.md:64478)
```

---

## §5 Currentness & refresh — G.11 T4 (config drift)

This edition is the object of refresh trigger **T4** in the whole-framework `RefreshPlan` ([[12-00-spine]] §6): *Layer-2 config drift → refresh the Local Practice edition mapping, **not** the Domain patterns.*

```text
RefreshScope (G.11 T4, this edition):
  EntityOfConcernRef: LAQF-Local v0.1 (the §2 realisation map + §3 records)
  TargetScope:        the realisation map only — Domain patterns are out of scope here
  Triggers:
    T4a asset change   → a hook/skill/agent/command/settings edit in dot_claude/:
                         re-walk §2, update the affected row's asset + status
    T4b gap closed     → one of the 9 ⬜ rows gains a realisation (e.g. the F2 trailer-strip
                         hook, the E2 citation hook): flip ⬜→◐/✅, update §3 LR record
    T4c Domain change  → a Domain pattern changes (spine §6 T1–T3): raise a refresh line on
                         the affected §2 row; the Domain change does NOT auto-rewrite config
    T4d conflict fixed → a §2.C C2 inter-asset conflict is resolved: update §2.C + ground truth
  Action:             re-derive the map from a fresh [[../../03-current-config-map]] snapshot;
                      record the refresh in [[PROGRESS]] §9
  RequiredPins:       dot_claude commit hash; config-map snapshot date; Domain edition version
```

**The gap backlog (the realisation agenda).** The nine ⬜ rows are an ordered improvement surface, most of them a single `MF-1` hook or one skill/template away from ◐/✅: F2 trailer-strip hook, F1 freshness gate, E2 citation gate, E1 test-pass-vs-run check (upgrade ◐→✅), E4 order check, C7 skill-invocation hook, C4 facts scaffold, C3 engineering-posture skill, C1 stack trim, C2 conflict resolution, B3 attention-budget ledger. Each closure is a T4b refresh, not a Domain edit.

---

## §6 E.5.3 conformance check

The edition is conformant iff a reader can answer all four (`E.5.3` CC-UD, `FPF-Spec.md:64890`):

1. **Does the dependency point upward only?** Yes — `LAQF-Local → LAQF (Domain) → FPF Core`; the realisation borrows pattern *ids and semantics*, never the reverse (§1, §0).
2. **Is it acyclic — no back-edge?** Yes — no Local asset is depended on by the Domain edition or Core; the spine's §4.1 direction holds (§1 `e53ConformanceNote`).
3. **Does the realisation write into the Domain edition or Core?** No — it maps assets to Domain ids; the assets have runtime effect, the edition does not (§4 `blockedRuntimeOrBuildReading`).
4. **Are the gaps a lag, not a contradiction?** Yes — the 9 ⬜ + 19 ◐ rows are an admissible lag under `compatibilityBoundary` (§1); a Domain pattern change raises a refresh line (§5 T4c), it does not make the Local edition non-conformant.

> Layer-2 fixed. The realisation map (§2) doubles as the gap backlog (§5); closing a ⬜ row is a T4b config-drift refresh, never a Domain edit. Next (S7): wire this edition + the pattern monolith into [[README]], [[seminar_timeline]], [[../../00-MoC]]; run E.21/E.19 quality + admission notes.

## See also

- [[12-20-local-practice-edition-ru]] — Russian twin
- [[12-00-spine]] — keystone: §4.1 edition direction, §4.2 dependency records, §4.3 R1–R5, §6 G.11 refresh plan
- [[12-10-patterns-A]] · [[12-11-patterns-B]] · [[12-12-patterns-C]] · [[12-13-patterns-D]] · [[12-14-patterns-E]] · [[12-15-patterns-F]] — the 30 Domain patterns this edition realises
- [[../../03-current-config-map]] — realisation ground truth (inventory, gaps §4, conflicts §5, stack size §6)
- [[12-01-source-pack]] — §6 MF-family vocabulary referenced in the realisation map
- [[_inputs/rc-digest]] — 30-RC working digest
- [[../11-fpf-diagnostic]] — D2 Laws-vs-Work ruling (Layer A mitigate / C–F transform)
- `FPF-Spec.md:64387` E.4.PFR · `:64835` E.5.3 · `:64890` CC-UD.1/2 · `:91923` G.11 · `:64478` reading-framework (no runtime/build reading)
