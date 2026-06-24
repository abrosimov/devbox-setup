# Top friction bash commands

From the sample of 459 bash tool_use commands across 25 most recent sessions, these are the patterns that most often hit the permission-prompt path. Each entry includes the verbatim command, the heuristic-derived friction score, and a one-line note explaining why the global allow-list (in `~/.claude/settings.json`) misses it.

Allow-list reference: matcher is prefix-based on the **first segment** of a compound command after splitting by `&&`/`||`/`;`/`|`. Rules use either space-glob `Bash(git status *)` or colon-glob `Bash(git status:*)`.

---

## 1. Score 10 — mlops-be @ 2026-06-18T13:22:22.156Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, multi-line/loop, command-substitution

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && \
  for f in .gitlab-ci.yml docker/mlops/all/docker-compose-mt.yml docker/mlops/all/migration-tests/kube/config docker/mlops/all/migration-tests/setup/Dockerfile docker/mlops/all/migration-tests/setup/init_vault.py docker/mlops/all/migration-tests/setup/mock_tokenreview.py docker/mlops/all/migration-tests/setup/requirements.txt makefile pyproject.toml; do \
    h1=$(git show "a3dfdd33d:$f" 2>/dev/null | shasum | awk '{print $1}'); \
    h2=$(git -C "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" show "af98f9099:$f" 2>/dev/null | shasum | awk '{print $1}'); \
    if [ "$h1" = "$h2" ]; then echo "SAME  $f"; else echo "DIFF  $f  mig=$h1  vault=$h2"; fi; \
  done
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. multi-line `for/do/done` or shell block — newlines are preserved in the command string; the head matches but subsequent segments and continuations are unmatched. contains `$(...)` command substitution — the harness treats this as part of the prefix string, breaking any straight glob match.

---

## 2. Score 10 — mlops-be @ 2026-06-18T13:24:27.192Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: show, unusual git sub: -C

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git show "a3dfdd33d:pyproject.toml" > "$TMPDIR/mig_pyproject.toml" && git -C "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" show "af98f9099:pyproject.toml" > "$TMPDIR/vault_pyproject.toml" && diff "$TMPDIR/mig_pyproject.toml" "$TMPDIR/vault_pyproject.toml"
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `-C, show` that have no explicit `Bash(git -C *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 3. Score 10 — mlops-be @ 2026-06-18T13:28:18.100Z

**Reasons:** cd-prefix to absolute/$/~, 7 && segments, unusual git sub: ls-remote, unusual git sub: ls-remote

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" && git config --get "branch.OICM-7329_add_vault_to_migrations.remote" && git config --get "branch.OICM-7329_add_vault_to_migrations.merge" && echo "---" && git ls-remote origin "refs/heads/OICM-7329_add_vault_to_migrations" 2>/dev/null && echo "---mig---" && cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git ls-remote origin "refs/heads/OICM-7329_migration_for_encrypting_existing_blueprints" 2>/dev/null
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 7+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `ls-remote` that have no explicit `Bash(git ls-remote *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 4. Score 10 — mlops-be @ 2026-06-18T13:28:24.902Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: for-each-ref, unusual git sub: for-each-ref

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" && git for-each-ref --format='%(refname:short) -> upstream=%(upstream:short)' refs/heads/OICM-7329_add_vault_to_migrations && cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git for-each-ref --format='%(refname:short) -> upstream=%(upstream:short)' refs/heads/OICM-7329_migration_for_encrypting_existing_blueprints
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `for-each-ref` that have no explicit `Bash(git for-each-ref *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 5. Score 10 — mlops-be @ 2026-06-19T08:13:33.085Z

**Reasons:** cd-prefix to absolute/$/~, 5 && segments, unusual git sub: show, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && echo "=== files added by release vault (824de3382) ===" && git show --name-only 824de3382 2>/dev/null | tail -20 && echo "" && echo "=== files in af98f9099 (my vault) ===" && git show --name-only af98f9099 2>/dev/null | tail -20
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 5+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 6. Score 10 — mlops-be @ 2026-06-19T08:17:05.137Z

**Reasons:** cd-prefix to absolute/$/~, 5 && segments, unusual git sub: for-each-ref, unusual git sub: branch

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git log --oneline --graph fedc6c21c -8 2>/dev/null && echo "---" && git for-each-ref --format='%(refname:short) %(objectname:short) %(subject)' refs/heads/ | grep -i release | head -5 && echo "---" && git branch --contains fedc6c21c | head -5
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 5+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `branch, for-each-ref` that have no explicit `Bash(git branch *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 7. Score 10 — mlops-be @ 2026-06-19T08:22:37.350Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: show, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git show 20f171be3:tests/migrations/test_v058_matches_app_constants.py && echo "===IDS===" && git show 20f171be3:tests/migrations/test_migration_ids_unique.py
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 8. Score 10 — oi-observability-lib @ 2026-06-23T09:02:50.952Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, multi-line/loop, command-substitution

```bash
cd /Users/kabrosimov/Work/mlops-be/base && for sym in instrument_mlflow instrument_minio instrument_docker instrument_sendgrid instrument_helm instrument_openfeature instrument_pure_storage instrument_kubernetes instrument_mongo instrument_transaction instrument_client instrument_celery_metrics instrument_flask instrument_fastapi; do
  count=$(grep -rln "$sym" --include="*.py" . 2>/dev/null | wc -l | tr -d ' ')
  echo "$sym: $count files"
done
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. multi-line `for/do/done` or shell block — newlines are preserved in the command string; the head matches but subsequent segments and continuations are unmatched. contains `$(...)` command substitution — the harness treats this as part of the prefix string, breaking any straight glob match.

---

## 9. Score 9 — Work @ 2026-06-23T13:33:28.220Z

**Reasons:** env-prefix, multi-line/loop, command-substitution

```bash
DST=/Users/kabrosimov/Work/devbox-setup/roles/devbox/files/dot_claude/future_projects/comprehensive_analysis/data/settings-snapshots
for src in \
  /Users/kabrosimov/Work/devbox-setup/.claude/settings.json \
  /Users/kabrosimov/Work/devbox-setup/.claude/settings.local.json \
  /Users/kabrosimov/Work/oi-observability-lib/.claude/settings.json \
  /Users/kabrosimov/Work/mlops-be/.claude/settings.json \
  /Users/kabrosimov/Work/mlops-be/.claude/settings.local.json \
  /Users/kabrosimov/Work/mlops-be/base/.claude/settings.local.json \
  /Users/kabrosimov/Work/mlops-be/OICM-7708_debug_pvc_creation/.claude/settings.local.json \
  /Users/kabrosimov/Work/node-health-monitor/.claude/settings.local.json \
  /Users/kabrosimov/Work/oicm-grafana-dashboards/.claude/settings.local.json \
  /Users/kabrosimov/Work/oicm-grafana-dashboards/base/.claude/settings.local.json \
  /Users/kabrosimov/Work/oi-platform-installer/.claude/settings.local.json \
  /Users/kabrosimov/Work/oi-platform-installer/base/.claude/settings.local.json \
  /Users/kabrosimov/Work/linters-runner/.claude/settings.local.json \
  /Users/kabrosimov/Work/training-jobs/.claude/settings.local.json \
  /Users/kabrosimov/Work/oicm-release-dashboard/.claude/settings.local.json \
  /Users/kabrosimov/Work/oiai-work-notes/.claude/settings.local.json; do
  if [ -f "$src" ]; then
    proj=$(echo "$src" | sed 's|/Users/kabrosimov/Work/||' | tr '/' '_')
    cp "$src" "$DST/$proj"
  fi
done
ls -la "$DST/" | head -25
```

**Why the allow-list misses:** leads with `VAR=value cmd …` (e.g. `GOSUMDB=off go ...` or `ANSIBLE_LOCAL_TEMP=... ansible-playbook ...`) — `Bash(go mod tidy)` rule does not include the env-prefix in its prefix-match. multi-line `for/do/done` or shell block — newlines are preserved in the command string; the head matches but subsequent segments and continuations are unmatched. contains `$(...)` command substitution — the harness treats this as part of the prefix string, breaking any straight glob match.

---

## 10. Score 8 — mlops-be @ 2026-06-18T13:17:28.153Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: branch

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git branch -a | head -20 && echo "---" && git log --oneline -20
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `branch` that have no explicit `Bash(git branch *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 11. Score 8 — mlops-be @ 2026-06-18T13:17:42.305Z

**Reasons:** cd-prefix to absolute/$/~, 5 && segments, unusual git sub: merge-base

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" && git status && echo "---LOG---" && git log --oneline -5 && echo "---BASE---" && git merge-base HEAD b77c57a1f 2>/dev/null
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 5+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `merge-base` that have no explicit `Bash(git merge-base *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 12. Score 8 — mlops-be @ 2026-06-18T13:17:52.297Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" && git log --oneline af98f9099~1..HEAD && echo "---FILES---" && git show --stat af98f9099 | head -40
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 13. Score 8 — mlops-be @ 2026-06-18T13:19:41.923Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git show --stat 20f171be3 | head -30 && echo "---ALL FILES TOUCHED BY a661435ca..a3dfdd33d---" && git diff --stat 20f171be3..a3dfdd33d
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 14. Score 8 — mlops-be @ 2026-06-19T06:37:21.907Z

**Reasons:** cd-prefix to absolute/$/~, 2 && segments, unusual git sub: branch, unusual git sub: branch

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git branch backup/OICM-7329_migration_for_encrypting_existing_blueprints_pre_split a3dfdd33d && git branch --list 'backup/*'
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 2+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `branch` that have no explicit `Bash(git branch *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 15. Score 8 — mlops-be @ 2026-06-19T06:37:56.410Z

**Reasons:** cd-prefix to absolute/$/~, 2 && segments, multi-line/loop

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git checkout 20f171be3 -- \
  mlops-migrations/V058__encrypt_existing_blueprints.py \
  tests/migrations/__init__.py \
  tests/migrations/test_migration_ids_unique.py \
  tests/migrations/test_v058_matches_app_constants.py && git status --short
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 2+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. multi-line `for/do/done` or shell block — newlines are preserved in the command string; the head matches but subsequent segments and continuations are unmatched.

---

## 16. Score 8 — mlops-be @ 2026-06-19T08:31:52.732Z

**Reasons:** cd-prefix to absolute/$/~, 2 && segments, multi-line/loop

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && echo "=== app symbols required by drift test ===" && python -c "
import sys
sys.path.insert(0, '.')
try:
    from app.modules.vault.vault_key_registry import VAULT_KEY_SEGMENTS
    print(f'VAULT_KEY_SEGMENTS: OK ({len(VAULT_KEY_SEGMENTS)} entries)')
except Exception as e: print(f'VAULT_KEY_SEGMENTS: FAIL {type(e).__name__}: {e}')
try:
    from app.repositories.blueprints.SecretsBlueprint import SecretsBlueprint
    print('SecretsBlueprint: OK')
except Exception as e: print(f'SecretsBlueprint: FAIL {type(e).__name__}: {e}')
try:
    from app.shared.clients.vault.VaultKeyBuilder import VaultKeyBuilder
    print('VaultKeyBuilder: OK')
except Exception as e: print(f'VaultKeyBuilder: FAIL {type(e).__name__}: {e}')
try:
    from app.shared.clients.vault import VaultKeyBuilder as vkb_module
    print(f'_SEGMENT_RE: {vkb_module._SEGMENT_RE.pattern!r}')
except Exception as e: print(f'_SEGMENT_RE: FAIL {type(e).__name__}: {e}')
try:
    from app.modules.vault import VaultService as vsm
    print(f'_VAULT_CIPHERTEXT_PATTERN: {vsm._VAULT_CIPHERTEXT_PATTERN.pattern!r}')
except Exception as e: print(f'VaultService: FAIL {type(e).__name__}: {e}')
try:
    from app.repositories.blueprints.BlueprintBase import SECRET_FIELD_BY_TYPE
    print(f'SECRET_FIELD_BY_TYPE: {SECRET_FIELD_BY_TYPE}')
except Exception as e: print(f'SECRET_FIELD_BY_TYPE: FAIL {type(e).__name__}: {e}')
try:
    from app.entities.definitions import blueprint_secrets_entity_name
    print(f'blueprint_secrets_entity_name: {blueprint_secrets_entity_name!r}')
except Exception as e: print(f'blueprint_secrets_entity_name: FAIL {type(e).__name__}: {e}')
" 2>&1 | head -30
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 2+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. multi-line `for/do/done` or shell block — newlines are preserved in the command string; the head matches but subsequent segments and continuations are unmatched.

---

## 17. Score 8 — mlops-be-OICM-7329-migration-for-masking-encrypted-blueprints @ 2026-06-19T10:13:45.853Z

**Reasons:** cd-prefix to absolute/$/~, 3 && segments, unusual git sub: show

```bash
cd ~/Work/mlops-be/OICM-7329_migration_for_masking_encrypted_blueprints && ls mlops-migrations/ | sort | tail -15 && echo "---" && git show --stat c8df956c2 | head -20
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 3+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 18. Score 6 — mlops-be-OICM-7329-migration-for-masking-encrypted-blueprints @ 2026-06-18T12:22:22.470Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, unusual git sub: merge-base

```bash
cd ~/Work/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints && git log --oneline release-1.14.0..HEAD 2>/dev/null; echo "---branch parent---"; git merge-base HEAD release-1.14.0 2>/dev/null
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `merge-base` that have no explicit `Bash(git merge-base *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 19. Score 6 — mlops-be-OICM-7329-migration-for-masking-encrypted-blueprints @ 2026-06-18T12:22:23.452Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, unusual git sub: merge-base

```bash
cd ~/Work/mlops-be/OICM-7329_migration_for_masking_encrypted_blueprints && git log --oneline release-1.14.0..HEAD 2>/dev/null; echo "---branch parent of masking---"; git merge-base HEAD release-1.14.0 2>/dev/null
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `merge-base` that have no explicit `Bash(git merge-base *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 20. Score 6 — mlops-be @ 2026-06-18T13:17:20.205Z

**Reasons:** cd-prefix to absolute/$/~, 5 && segments

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git status && echo "---LOG---" && git log --oneline base/develop..HEAD 2>/dev/null | head -20 && echo "---BRANCH---" && git rev-parse --abbrev-ref HEAD
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 5+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user.

---

## 21. Score 6 — mlops-be @ 2026-06-18T13:25:30.876Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git show 20f171be3 -- docker/mlops/migrations/Dockerfile pyproject.toml
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 22. Score 6 — mlops-be @ 2026-06-18T13:27:11.237Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git show a661435ca -- docker/mlops/migrations/Dockerfile pyproject.toml
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 23. Score 6 — mlops-be @ 2026-06-18T13:27:45.069Z

**Reasons:** cd-prefix to absolute/$/~, 1 && segments, unusual git sub: show

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git show --name-only 20f171be3 | tail -10
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 1+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user. uses git subcommand(s) `show` that have no explicit `Bash(git show *)` allow rule — only `git add/status/diff/log/branch/blame/ls-files/ls-tree/rev-parse/stash/checkout -b/switch/remote/fetch/push/config --get/worktree list/commit` are allowed.

---

## 24. Score 6 — mlops-be @ 2026-06-19T06:38:55.586Z

**Reasons:** cd-prefix to absolute/$/~, 7 && segments

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git config --get commit.gpgsign && git config --get gpg.format && git config --get user.signingkey && echo "---" && ls -la ~/.ssh/ 2>/dev/null | head -10 && echo "---existing commits sig:---" && git log --show-signature -1 b77c57a1f 2>&1 | head -10
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 7+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user.

---

## 25. Score 6 — mlops-be @ 2026-06-19T07:53:40.445Z

**Reasons:** cd-prefix to absolute/$/~, 5 && segments

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git status && echo "---HEAD---" && git log --oneline -5 && echo "---STASH---" && git stash list
```

**Why the allow-list misses:** starts with `cd "$AION_AUTOPOIESEON/..."` or `cd "$HOME/..."` — the matcher sees the first segment as `cd ...` which matches `Bash(cd *)`, but only matches first segment; subsequent `&&`-chained segments are matched independently and prefix patterns like `Bash(git status *)` do not include the `cd` lead. contains 5+ `&&` chain segments — Claude Code splits on chain operators and matches each independently; any single segment that fails to match prompts the user.

---

