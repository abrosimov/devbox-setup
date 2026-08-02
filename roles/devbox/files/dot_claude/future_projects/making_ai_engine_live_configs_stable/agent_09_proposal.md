# Proposal: Unification of AI Engine Live Configs Synchronization

## The Problem: Safety Net vs Single Source of Truth

Currently, AI engines (Claude Code and Antigravity CLI) actively modify their `settings.json` files during runtime to persist user approvals (`alwaysAllow`) and dynamic paths (`trustedWorkspaces`). 

This creates a conflict between two deployment principles:
1. **Safety Net:** Blindly copying the repository template over the local `settings.json` destroys runtime approvals, forcing the user to re-approve previously granted permissions. We recently mitigated this for `agy-push` by introducing a `merge_settings.py` script that merges the repository template into the local file during deployment.
2. **Single Source of Truth (SSoT):** Merging on push protects the local environment, but it leaves the repository ignorant of the new permissions. If the user moves to a different machine, those approvals are lost. To maintain Git as the SSoT, runtime states must be pulled back into the repository.

## The Solution: A Unified Diff-Pull-Validate-Push Workflow

Instead of relying solely on a defensive merge during `push`, we propose an interactive, drift-aware synchronization pipeline that standardises both `agy-push` and `claude-push`.

### 1. Drift Detection (Diff)
Before any push operation, the pipeline compares the active `settings.json` (`~/.gemini/antigravity-cli/settings.json` or `~/.claude/settings.json`) against its respective repository template (`.j2`).

### 2. Interactive Pull & Merge (Pull Review)
If drift is detected (e.g., new `alwaysAllow` rules or `trustedWorkspaces` are present locally but missing in Git), the pipeline halts and suggests pulling the changes.
A unified pull-review script will heuristically merge the local additions back into the repository's `.j2` templates, preserving Jinja variables and removing duplicates. 

### 3. Commit
Once the repository templates are enriched with the local permissions, the pipeline can optionally suggest a commit (e.g., `chore(ai): sync local permissions`).

### 4. Validate & Push
Only after the repository is synced and validated does the Ansible deployment (`push`) proceed, safely deploying the updated configuration to the local environment with correct permissions (`0600`).

## Technical Implementation

1. **Unify the Pull Review Script:**
   - Abstract the existing `scripts/claude-pull-review` into a generic `scripts/sync_ai_settings.py`.
   - The script will accept target identifiers (e.g., `--target agy` or `--target claude`) to resolve the correct repository and local paths.

2. **Update Makefile Targets:**
   - Introduce `agy-diff` and `agy-pull-review` targets mirroring the existing Claude targets.
   - Introduce a high-level `make ai-sync` command that coordinates the full loop for all AI tools.
   - Refactor `agy-push` and `claude-push` to depend on their respective `-diff` targets. If drift is detected, `make` will exit with a helpful error: *"Drift detected! Run `make <target>-pull-review` before pushing to persist your local permissions."*

3. **Retain Defensive Pushes as Fallbacks:**
   - While `merge_settings.py` remains a useful fallback for raw Ansible runs, the `Makefile` workflow will guarantee that the repository is always strictly ahead of or equal to the local environment before a push occurs.
