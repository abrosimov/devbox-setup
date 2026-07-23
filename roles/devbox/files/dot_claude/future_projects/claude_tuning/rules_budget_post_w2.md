# Rules-Budget Report — post-W2 baseline

**Root:** `/Users/kabrosimov/Work/devbox-setup/roles/devbox/files/dot_claude`
**Budget reference:** 150–200 concurrent instructions
**Captured:** 2026-07-23 (after W2 apply landed in `4ffaf2f`)
**Baseline compared:** `rules_budget_baseline.md` (2026-07-21, pre-W2)

## Aggregate — baseline vs post-W2

| Scope | Artefacts | Flat | Hard | Soft | Strength-weighted |
|---|---:|---:|---:|---:|---:|
| Always-on (baseline) | 6 | 119 | 28 | 91 | 147 |
| Always-on (post-W2) | 3 | **73** | 17 | 56 | 90 |
| Δ always-on | −3 | **−46** | −11 | −35 | −57 |
| Trigger-loaded (baseline) | 85 | 957 | 157 | 800 | 1114 |
| Trigger-loaded (post-W2) | 87 | 999 | 167 | 832 | 1166 |
| Δ trigger | +2 | +42 | +10 | +32 | +52 |
| Scope-weighted aggregate (baseline) | — | — | — | — | 1314 |
| Scope-weighted aggregate (post-W2) | — | — | — | — | 1218 |
| Δ scope-weighted | — | — | — | — | −96 |

**Always-on flat count:** 73 (under the 150–200 budget). **Target from RI2 audit was −46; exact hit.**

## Always-on artefacts (post-W2)

| Artefact | Kind | Scope | Flat | Hard | Soft | Strength |
|---|---|---|---:|---:|---:|---:|
| `USER_AUTHORITY_PROTOCOL.md` | uap | always-on | 56 | 12 | 44 | 68 |
| `skills/project-preferences/SKILL.md` | skill | always-on | 11 | 3 | 8 | 14 |
| `skills/project-toolchain/SKILL.md` | skill | always-on | 6 | 2 | 4 | 8 |

## What changed vs baseline

**Demoted from always-on → trigger** (per RI2 audit verdicts, Phase 1b):

| Skill | Baseline flat (always-on) | Post-W2 flat (trigger) | Notes |
|---|---:|---:|---|
| `code-comments` | 21 | 21 | Reached via `problem:` field + `related:` edges (W2 apply). |
| `lint-discipline` | 21 | 21 | Reached via `problem:` field + `related:` edges (W2 apply). |
| `lsp-navigation` | 4 | — | **Merged into `lsp-tools`** (Phase 1a). Original artefact removed. |

**Kept always-on** (RI2 verdict: essential + already lean):
- `USER_AUTHORITY_PROTOCOL.md` (56 flat) — core authority protocol.
- `project-preferences` (11 flat) — flagged for split in W3 (Q-RI2-2 → W3).
- `project-toolchain` (6 flat) — invocation ergonomics, cannot be trigger-loaded reliably.

**Trigger delta reconciliation** (+42 flat):
- +21 from `code-comments` demotion (moved scope, same content).
- +21 from `lint-discipline` demotion (moved scope, same content).
- +0 net from `lsp-navigation` merge — `lsp-tools` trigger flat stayed at 2 (merged content sat below the counter's threshold or was already there).

## Verdict

- **Under budget.** 73/150 flat = 49% of the floor of the target band. Substantial headroom for future always-on additions if needed.
- **W2 hit its numeric target exactly.** RI2 audit predicted −46; delivered −46.
- **Scope-weighted total dropped 7.3%** (1314 → 1218) — the demoted rules cost less overall once trigger-scope discount is applied.
- **No follow-up rules-budget work needed in W2.** Next quantitative checkpoint: after `project-preferences` split (W3, Q-W3-2).

## References

- Baseline: [[rules_budget_baseline]] (pre-W2)
- W2 route: [[route_W2_structural]]
- RI2 audit that motivated the demotions: [[route_RI2_always_on_audit]]
- State snapshot capturing the apply: [[state/2026/07/2026-07-23-w2-apply-plus-git-hook-deny]]
- Generator: `roles/devbox/files/dot_claude/bin/rules_budget.py`
