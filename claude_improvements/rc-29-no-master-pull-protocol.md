---
tags: [claude-improvements, phase3, root-cause, layer-F]
phase: 3
rc-id: RC-29
layer: F
created: 2026-06-27
symptoms: [S-025]
---

# RC-29 — No protocol to pull fresh master into the working branch

## Mechanism

No mechanism, hook, or skill pulls fresh `origin/<default>` into the current working branch after meaningful events (post-commit, post-PR-merge, session start, worktree creation). Branches drift; merges become harder over time; the user explicitly asked for a protocol that pulls master after each commit ([[01-symptoms-inventory#S-025]]). Partial coverage exists in `wt sync` (Projects-level docs) — it merges the recorded `wt-parent` into the current worktree — but it must be invoked manually and is per-worktree, not per-commit. `permission_auto_approve.py` and `pre_bash_safety_gate.py` cover destructive git ops but neither prompts fresh-pull. Surface: process layer / git hygiene — zero coverage ([[03-current-config-map#3.10 Git hygiene]]).

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-025]]
- External: [[02-external-research#R3.3]] (multi-agent decomposition — file-based handoffs; stale base → handoff drift)
- Config gaps: [[03-current-config-map#3.10 Git hygiene]] — "No hook detects/forces 'pull master into branch'"; `wt sync` referenced but manual only

## Fix proposals (≥5)

### F1 — PostToolUse Bash hook offering fresh-pull after `git commit`

- **Surface:** hook (new `bin/post_bash_master_sync_nudge.py`, registered on `PostToolUse(Bash)`)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — must not auto-merge; nudge only. Auto-merge on a feature branch can introduce unwanted changes.
- **Approach:** Detect `git commit` (and `git commit --amend`) in the tool call. After success, run `git fetch origin <default> --quiet` and compute `git rev-list --count HEAD..origin/<default>`. If >0, emit `additionalContext`: "origin/<default> is N commits ahead. Run `wt sync` or `git merge --ff-only origin/<default>`." If FF-only is safe (no divergent commits on the current branch), include a one-liner that runs it. Never run the merge automatically.
- **Steps:**
  1. Implement `roles/devbox/files/dot_claude/bin/post_bash_master_sync_nudge.py`.
  2. Resolve default branch via `git symbolic-ref refs/remotes/origin/HEAD`.
  3. Use `_claude_lib.hooks.emit_additional_context`.
  4. Register on `PostToolUse(Bash)` matcher in `hooks.json`.
- **Touches/replaces:** `hooks.json`.

### F2 — Stop hook surfacing branch-staleness once per session

- **Surface:** hook (extend `bin/stop_format.py` or new `bin/stop_branch_freshness.py`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — informational only
- **Approach:** At session-end (Stop matcher), check whether the working branch is N commits behind `origin/<default>` (N≥5 configurable). Emit one summary line into `additionalContext`. Cheap; sole purpose is to ensure the user sees staleness before closing the session.
- **Steps:**
  1. Implement `stop_branch_freshness.py`.
  2. Skip when not inside a git worktree or when branch is the default branch.
  3. Cache last-fetch timestamp in `.claude/state/` to avoid repeated `git fetch` on every Stop.
- **Touches/replaces:** `hooks.json`.

### F3 — New command `/techne-sync-master`

- **Surface:** command (new `commands/techne-sync-master.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** medium — invokes a merge; needs Stop-condition checks for clean working tree
- **Approach:** Single-shot command: `git fetch origin <default>`; if working tree clean and FF-only possible → run `git merge --ff-only origin/<default>`; else explain and stop. Mirrors `wt sync` but available as a slash command inside the active worktree without leaving the assistant.
- **Steps:**
  1. Create `commands/techne-sync-master.md` per `techne-` prefix convention.
  2. Call out via existing safety gates (`pre_bash_safety_gate.py`) to refuse on dirty working tree.
  3. Cross-link from `wt sync` documentation in workspace `CLAUDE.md`.
- **Touches/replaces:** none.

### F4 — Output-style nudge after every commit message in assistant output

- **Surface:** output-style (edit existing default or via `agents/software_engineer_*.md` body)
- **Effort:** low
- **Impact:** low
- **Risk:** low — text only
- **Approach:** Add a "post-commit reminder" line that SE agents emit immediately after announcing a successful commit: "Branch is now ahead of last sync — consider `/techne-sync-master` or `wt sync`." Pure no-code nudge complementing the F1 hook.
- **Steps:**
  1. Add the line to 3 SE agent files: `software_engineer_go.md`, `software_engineer_python.md`, `software_engineer_frontend.md`.
  2. Cross-reference `branch-freshness` skill (F5).
- **Touches/replaces:** 3 agent files.

### F5 — New skill `branch-freshness`

- **Surface:** skill (new `skills/branch-freshness/SKILL.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory, ≤60 lines
- **Approach:** Skill codifies: when to sync (post-commit, post-PR-merge, before opening PR, weekly), what to use (`wt sync` for worktrees with recorded parents, `git merge --ff-only origin/<default>` for FF-safe cases, rebase for clean linear history), how to recover from conflicts (`git merge --abort` is safe; `git rebase --abort` is safe). `alwaysApply: false`; triggered when prompt contains `merge`, `rebase`, `sync`, `behind`, `stale`, `master`, `main`.
- **Steps:**
  1. Scaffold via `skill-builder`.
  2. Frontmatter trigger list as above.
- **Touches/replaces:** none.

### F6 — Permission allowlist for `git fetch` (no-code settings change)

- **Surface:** settings.json (edit `permissions.allow`)
- **Effort:** low
- **Impact:** low
- **Risk:** low — read-only operation
- **Approach:** Ensure `Bash(git fetch *)` is in `permissions.allow`. Without it, F1/F2 hooks asking for `git fetch` may surface a permission prompt and undermine the nudge. Examined as part of the broader allowlist hygiene work (RC-18).
- **Steps:**
  1. Verify `Bash(git fetch *)` in `permissions.allow` in `settings.json`.
  2. Add if absent.
- **Touches/replaces:** `settings.json`.

## Acceptance signal

- After `git commit` succeeds in 10 sample sessions: ≥9 surface the master-staleness nudge or no nudge needed (already fresh).
- `/techne-sync-master` succeeds on a clean worktree without a permission prompt.
- Working branches across active worktrees observed to be <10 commits behind origin/master over a week (currently unbounded).
- `stop_branch_freshness` warning fires at session-end exactly when staleness threshold (5 commits) is breached.
- Conflict-on-sync incidents tracked manually drop after two weeks of regular sync.

## Trade-offs and counter-evidence

Auto-merge after every commit (a stricter variant than F1's nudge) is the obvious "ideal" but creates two real risks: (1) it runs without the user's eyes on the merge result; (2) it can introduce unrelated upstream changes mid-task, contaminating the diff under review. Nudge-only is the right ergonomic. F3 (`/techne-sync-master`) overlaps with `wt sync` from the workspace tooling — risk of two slightly-different sync paths drifting. Mitigation: have `/techne-sync-master` delegate to `wt sync` when invoked inside a worktree with a recorded `wt-parent`. F5 is the one allowed new skill; do not add a second. No Anthropic counter-evidence. Counter-evidence within this repo: this RC is closely adjacent to the user's existing `wt sync` design — duplication risk if not coordinated.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-30-coauthor-trailer-leak]] (sibling — git hygiene layer)
- [[rc-24-done-without-verification]] (verification cousin — branch state vs claim)
