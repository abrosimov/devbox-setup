---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-18
layer: C
created: 2026-06-27
symptoms: [S-002, S-031]
---

# RC-18 — `permission_auto_approve.py` does not cover every dispatch path; permission prompts persist

## Mechanism

[[03-current-config-map#3.13 Permission allowlist hygiene]] documents that `permission_auto_approve.py` (PermissionRequest hook) and `settings.json:138-499` `permissions.allow`/`deny` are both deployed, yet the user is still prompted on routine actions during sessions. Claude itself flagged the permissions config as "messed up" (S-002 verbatim). S-031 names the specific case: `Bash(git push *)` was blanket-denied, forcing approval on every push to a feature branch. Mechanism: the auto-approve hook's `SAFE_COMMAND_FAMILIES` whitelist enumerates Bash heads (git, ls, grep, etc.) but does not currently extend to subagent dispatch via `Task`, certain Glob/Grep edge cases, or per-machine overrides. The `settings.json` deny rules are intentionally aggressive for safety; the allow rules are conservative because the user maintains both work and personal profiles and refuses to share allowlist content across them. Net result: every approval prompt is a context-switch tax on the user; the prompts compound across long sessions; over time the user starts auto-clicking approve, which defeats the safety intent. Friction without protection is worse than either alone.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-002]] (allow/deny list "messed up", Claude itself flagged), [[01-symptoms-inventory#S-031]] (`git push *` deny → manual approval every push).
- External: [[02-external-research#R3.2]] auto-approve rates rise 20%→40% over ~750 sessions in practitioner studies — drift is documented.
- Config gaps: [[03-current-config-map#3.13]] `permission_auto_approve.py` exists with `SAFE_COMMAND_FAMILIES` but appears ineffective in current session; `claude_fix_perms.py` exists but unscheduled; `techne-fewer-permission-prompts` skill exists but invoked manually.
- Reflection: not direct, but compounds with [[04-reflection-evidence#RC-ref-3]] — friction taxes the user's working memory across sessions.

## Fix proposals

### F1 — Extend `SAFE_COMMAND_FAMILIES` to cover subagent Task dispatch

- **Surface:** bin script (existing)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — broadening auto-approve has security cost; mitigated by tier split (F3).
- **Approach:** Audit `bin/permission_auto_approve.py` to confirm which tool surfaces it currently intercepts. If subagent-dispatched calls (Task tool) bypass the PermissionRequest path or arrive with a different signature, extend the matcher. Same for Glob/Grep/Read invoked inside subagents. Document the discovered gap in the script's docstring.
- **Steps:**
  1. Read `bin/permission_auto_approve.py` to confirm matcher signature.
  2. Add a code-path for subagent-originating Task calls; verify with a synthetic Task dispatch.
  3. Extend `SAFE_COMMAND_FAMILIES` for any newly observed safe heads.
  4. Cover with test simulating subagent Task in `bin/tests/test_permission_auto_approve.py`.
- **Touches/replaces:** `bin/permission_auto_approve.py`; `bin/tests/test_permission_auto_approve.py`.

### F2 — Scheduled `techne-fewer-permission-prompts` per profile

- **Surface:** workflow / Makefile target
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** The skill exists but invocation is manual. Add a Makefile target `make perms-mine PROFILE=personal` (or work) that wraps the skill's underlying Python script (`techne_fewer_permission_prompts.py` per skill spec) — scans the last N days of transcripts, extracts deterministic-safe commands, proposes additions to `settings.local.json`. Run manually weekly; document in project README.
- **Steps:**
  1. Add `perms-mine` target to `Makefile`.
  2. Document scheduling guidance in `roles/devbox/files/dot_claude/skills/techne-fewer-permission-prompts/SKILL.md`.
  3. Output should land in `~/.claude/settings.local.json` (per-machine, gitignored), not the shared `settings.json`.
- **Touches/replaces:** `Makefile`; skill SKILL.md.

### F3 — Split allowlist into tiers (read-only / mutation / destructive)

- **Surface:** settings.json
- **Effort:** medium
- **Impact:** high
- **Risk:** low — clarification, not relaxation.
- **Approach:** No-code restructure of `settings.json:138-499`. Currently `permissions.allow`/`deny` are flat lists. Reorganise into three logical tiers via JSON comments or grouping convention: T1 read-only (always allow), T2 mutation (allow with auto-approve for safe heads, prompt otherwise), T3 destructive (always deny, hook-blocked). Makes intent explicit; reduces noise from over-broad rules; makes per-profile overrides easier to reason about.
- **Steps:**
  1. Audit current allow/deny entries; categorise each into T1/T2/T3.
  2. Restructure `settings.json` with section comments.
  3. Move some currently-denied safe heads (e.g. `git push origin <feature-branch>`) into T2 with auto-approve.
- **Touches/replaces:** `roles/devbox/files/dot_claude/settings.json`.

### F4 — Per-agent `tools:` reduce explicit (no-code)

- **Surface:** agent-frontmatter
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** No-code. Many agents currently declare broad `tools:` (Read, Write, Edit, Bash, Glob, Grep, …). Read-only agents (`code_reviewer`, `consistency_checker`, `freshness_auditor`, `domain_expert`, `meta_reviewer`) should not have Write/Edit/Bash. Per-agent tightening means PermissionRequest never fires for forbidden tools — fewer prompts by construction. Pairs with security improvement: a runaway reviewer cannot write code.
- **Steps:**
  1. Audit 28 agents; classify each as read-only / read-write / executor.
  2. Remove Write/Edit/Bash from read-only agents.
  3. Remove Bash from agents that only need file ops.
  4. Cross-check `agent-builder` skill validation passes.
- **Touches/replaces:** ~10-15 `agents/*.md` files.

### F5 — `settings.local.json` profile for per-machine overrides

- **Surface:** settings.json + workflow
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Claude Code respects `settings.local.json` for per-machine overlay without re-prompting. Currently the deployed `settings.json` is one-size-fits-all. Document a convention: shared safety rules in `settings.json` (committed to repo), machine-specific allow extensions in `settings.local.json` (gitignored, deployed as part of `local/` overlay). Personal laptop can auto-approve `make personal-deploy`; work laptop can auto-approve `ssh work-jump-host`. Neither leaks across.
- **Steps:**
  1. Document the split convention in `devbox-setup/CLAUDE.md` and `roles/devbox/files/dot_claude/skills/editing-claude-config/SKILL.md`.
  2. Add `roles/devbox/local/.claude/settings.local.json.example` as a template (gitignored real file).
  3. Update Ansible deployment to copy `settings.local.json` if present in `roles/devbox/local/` to `~/.claude/settings.local.json`.
- **Touches/replaces:** docs + Ansible task in `roles/devbox/tasks/install_configs.yml`.

## Acceptance signal

- In 10 fresh sessions, count of permission prompts drops by ≥50% versus baseline (instrumented via hook log).
- `bin/permission_auto_approve.py` correctly auto-approves subagent-dispatched Task calls on safe heads.
- `git push origin <feature-branch>` no longer prompts for approval (S-031 specifically resolved).
- Read-only agents (`code_reviewer` etc.) cannot trigger Write/Edit/Bash — verified via `make validate-claude`.
- `settings.local.json` overlay deploys per-profile without leaking into the committed `settings.json`.

## Trade-offs and counter-evidence

- **Auto-approve drift is a security pattern.** [[02-external-research#R3.2]] documents auto-approve rates rising 20%→40% over ~750 sessions — broad allowlists tend to grow. Mitigation: F3 tier split prevents T3 (destructive) ever being auto-approved; F2 mining proposes additions but user reviews the diff.
- **F4 (per-agent tools tightening) breaks legitimate cross-tool flows.** Some reviewers want to run `golangci-lint` (Bash); some doc agents want to commit (Bash). Audit carefully; do not blanket-remove. Workflow validation must pass.
- **F1 (subagent dispatch coverage) requires understanding the Task tool's PermissionRequest signature** — may require instrumentation to discover the gap. Spend time on observation before patching blindly.
- **F5 (`settings.local.json`) splits config across two files** — adds maintenance cost; benefit only realises if both profiles are actively used. Keep convention minimal.
- **Counter-evidence**: User feedback S-002 says Claude itself flagged the config as broken. The fix may not be addition but removal — there may be deny rules that are over-broad and should be narrowed (e.g. `Bash(git push *)` blanket deny). Start with F3 audit before F1/F2.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-17-advisory-only-rules]] — adjacent: rules without enforcement
