---
tags: [claude-improvements, phase3, root-cause, layer-F]
phase: 3
rc-id: RC-30
layer: F
created: 2026-06-27
symptoms: [S-026]
---

# RC-30 — `Co-Authored-By` trailer keeps reappearing despite explicit ban

## Mechanism

The ban "Never add `Co-Authored-By` trailers to commit messages" lives only in `USER_AUTHORITY_PROTOCOL.md § Git Commits` (lines 142-144 — [[03-current-config-map#2 USER_AUTHORITY_PROTOCOL.md]]). It is advisory: no PreToolUse hook on `Bash(git commit *)` strips or refuses messages containing the substring, no post-commit hook on the host repo verifies trailers. The rule is one of dozens in a 216-line file at line 142, well past the attention-budget knee ([[02-external-research#R5]] item 6: model attends ~150 instructions; CLAUDE.md ≤200 lines guidance), which makes it exactly the class of rule the model drops ([[02-external-research#R2.3]] — "CLAUDE.md rules are silently dropped … violated across multi-paragraph outputs, including outputs explicitly about instruction following"). The leak is structural: layer F (process) is missing a deterministic gate. Surface: pre-Bash hook, post-commit hook, existing `git_safe_commit.py` helper.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-026]]
- External: [[02-external-research#R2.3]] (GitHub #53459 — CLAUDE.md rules silently dropped), [[02-external-research#R2.1]] (April postmortem — caching bug cleared reasoning, increased forgetfulness), [[02-external-research#R5]] item 6 (≤200 lines guidance; current stack is 509)
- Config gaps: [[03-current-config-map#3.10 Git hygiene]] — "USER_AUTHORITY_PROTOCOL ban exists — but no `Bash(git commit *)` PreToolUse hook strips trailers. The ban relies on adherence."
- Counter-evidence: [[10-root-causes-overview#RC-11 claude-md-attention-budget]], [[10-root-causes-overview#RC-13 claude-md-bloat]] — even strengthening the CLAUDE.md rule is unlikely to fix this; deterministic gate is required.

## Fix proposals (≥5)

### F1 — PreToolUse Bash hook stripping `Co-Authored-By` from `git commit`

- **Surface:** hook (new `bin/pre_bash_strip_coauthor.py`, registered on `PreToolUse(Bash)`)
- **Effort:** medium
- **Impact:** high
- **Risk:** low — pattern is precise; very low false-positive surface
- **Approach:** Match command head `git commit` (incl. `--amend`). Inspect every form: `-m "…"`, `-F <file>`, heredoc `<<EOF`, multi-arg `-m "…" -m "…"`. Detect `Co-Authored-By:` (and case variants, e.g. `co-authored-by:`) anywhere in the message body. Two modes via config: **strip** (rewrite the command to remove the trailer line) — preferred, transparent — or **refuse** (exit 2 with message pointing at UAP § Git Commits) — louder, blocks the commit. Default: strip. Log every strip event to `.claude/state/coauthor_strips.log` for transparency.
- **Steps:**
  1. Implement `roles/devbox/files/dot_claude/bin/pre_bash_strip_coauthor.py` modelled on `pre_bash_safety_gate.py`.
  2. Cover `-m`, `-F`, heredoc, multi-line message variants.
  3. Register `PreToolUse(Bash)` matcher in `hooks.json` after `pre_bash_safety_gate`.
  4. Tests `bin/tests/test_pre_bash_strip_coauthor.py` covering all command shapes.
- **Touches/replaces:** `hooks.json`, sibling to `pre_bash_safety_gate.py`.

### F2 — Extend `git_safe_commit.py` to strip on call site

- **Surface:** bin script (extend existing `bin/git_safe_commit.py`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — `git_safe_commit.py` already exists ([[03-current-config-map#3.10]])
- **Approach:** When the script is invoked as the commit driver (current path through `permission_auto_approve.py` for some commit shapes), strip the trailer in-script before delegating to `git commit`. Defence-in-depth: even if F1 misses a command shape, calls routed through this helper are clean.
- **Steps:**
  1. Open `bin/git_safe_commit.py` and add `_strip_coauthor(message: str) -> str`.
  2. Apply to message input regardless of source (`-m`, `-F`, stdin).
  3. Emit a single-line warning to stderr when stripping fires.
- **Touches/replaces:** `bin/git_safe_commit.py`.

### F3 — Post-commit verifier on host repo

- **Surface:** bin script + git hook installer (new `bin/install_post_commit_coauthor_check.sh` + `proj hooks` extension)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low — verifies after the fact; cannot rewrite, only flag
- **Approach:** Install a `post-commit` git hook (per repo, via `proj hooks` workspace tooling) that runs `git log -1 --pretty=%B | grep -i co-authored-by` and on hit prints a loud warning + suggests `git commit --amend` to remove the trailer. Catches anything that slipped past F1 and F2 (e.g. manual `git commit -m` typed in a shell outside the assistant).
- **Steps:**
  1. Add the post-commit hook template under `roles/devbox/files/dot_claude/templates/git-hooks/post-commit`.
  2. Extend the workspace `proj hooks` function to install it on `proj clone`/`proj new`.
  3. Document in workspace `CLAUDE.md` git-hygiene section.
- **Touches/replaces:** workspace fish functions in `roles/devbox/files/.config/fish/functions/proj.fish`, new template file.

### F4 — Per-SE-agent system-prompt clause re-emphasising the ban

- **Surface:** agent body (edit SE + reviewer agents)
- **Effort:** low
- **Impact:** **low (counter-evidence below)**
- **Risk:** low — text-only
- **Approach:** Add a one-line `## Commit trailers` block to `software_engineer_*.md`, `code_reviewer.md`, `refactor_cleaner.md`: "Never add `Co-Authored-By` trailers, by Claude or by any agent. The repository has hooks that strip them; do not generate them in the first place." Counter-evidence acknowledged: RC-11 and RC-13 already show that even strong CLAUDE.md rules are dropped; this clause is unlikely to be effective on its own but cheap to add and reinforces the deterministic F1/F2/F3 layer.
- **Steps:**
  1. Add the clause to 5 agent files.
- **Touches/replaces:** 5 agent files.

### F5 — Promote ban into `agent-base-protocol` skill at `alwaysApply: true`

- **Surface:** skill (edit existing `skills/agent-base-protocol/SKILL.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — moves the rule from a deep CLAUDE.md line to a near-the-top skill; still advisory
- **Approach:** Add a `## Commit Hygiene` section to `agent-base-protocol/SKILL.md` (already `alwaysApply: true`) containing the trailer ban + a one-line statement that hooks enforce it. Brings the rule closer to attention budget head. No new skill — extends existing.
- **Steps:**
  1. Open `roles/devbox/files/dot_claude/skills/agent-base-protocol/SKILL.md`.
  2. Add `## Commit Hygiene` (≤5 lines).
  3. Cross-link `pre_bash_strip_coauthor.py` (F1).
- **Touches/replaces:** `skills/agent-base-protocol/SKILL.md`.

### F6 — settings.json deny on raw `git commit *Co-Authored-By*` pattern

- **Surface:** settings.json (edit `permissions.deny`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — refuses commits with the trailer; tighter than F1's strip mode
- **Approach:** Add `Bash(git commit *Co-Authored-By*)` and case variants to `permissions.deny`. Refuses the call entirely. Pair with F1's strip mode to give the user a choice: strip silently (F1) or refuse loudly (F6); recommend F1 default and F6 in "strict" mode.
- **Steps:**
  1. Edit `roles/devbox/files/dot_claude/settings.json` `permissions.deny` block.
  2. Add the two patterns (uppercase and lowercase forms).
  3. Document in `editing-claude-config` skill.
- **Touches/replaces:** `settings.json` permissions block.

## Acceptance signal

- Audit of 50 most recent commits across active worktrees shows zero `Co-Authored-By` trailers post-F1 deployment.
- `pre_bash_strip_coauthor.py` strip-event log shows N>0 strips in the first week (confirms the hook is catching real leaks) followed by a steady decline.
- Post-commit hook (F3) fires zero times after F1+F2 are deployed (verification confirms deterministic gates work).
- `agent-base-protocol` skill section is visible in subagent context at session start.
- Settings.json deny rule (F6) catches any leak that bypasses the strip hook (defence-in-depth check).

## Trade-offs and counter-evidence

This RC is the cleanest example of the broader pattern in [[10-root-causes-overview#Cross-cutting design observations]] item 1: relying on advisory rules where deterministic gates are available. The user named the symptom explicitly because the prior advisory approach demonstrably failed ([[02-external-research#R2.3]] — CLAUDE.md rules silently dropped, particularly in outputs explicitly about instruction following). Therefore F4 ("add another rule") is acknowledged as nearly-ineffective on its own — it stays as cheap reinforcement, not as the primary fix. F1 + F6 together are the deterministic core. The strip-vs-refuse choice (F1 strip default; F6 refuse) is a real design trade-off: silent stripping risks the user not knowing it happened (mitigated by the log file); refuse is louder but blocks the commit. Bias toward strip + log to keep the assistant moving while preserving forensics. No Anthropic counter-evidence specific to this trailer pattern. Risk of regex evasion (e.g. `Co_Authored_By`, zero-width spaces) is low — those forms would not be generated by the model in the first place.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-29-no-master-pull-protocol]] (sibling — git hygiene layer)
- [[rc-11-claude-md-attention-budget]] (root cause of advisory-rule drop)
- [[rc-13-claude-md-bloat]] (compounding cause)
- [[rc-17-advisory-only-rules]] (broader pattern of advisory-vs-deterministic gap)
