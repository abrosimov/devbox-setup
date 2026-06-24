# Normalisation trace — what happens to friction commands

For 10 representative friction commands sampled from the 459-command corpus, we trace step-by-step how each layer of the harness pipeline evaluates them. The pipeline order is:

1. **Sandbox** (`~/.claude/settings.json` `sandbox`) — allows/denies based on writable dirs and `excludedCommands`. Sandboxed commands that pass `autoAllowBashIfSandboxed` skip prompts.
2. **`pre-tmpdir-guard`** (`~/.claude/bin/pre-tmpdir-guard`) — blocks (exit 2) any Bash command whose string matches `*/tmp/*` or `*/var/tmp/*`.
3. **`pre-bash-toolchain-guard`** (`~/.claude/bin/pre-bash-toolchain-guard`) — blocks (exit 2) `go fmt`/`gofmt`, `pip install`, manual `python -m venv`, bare `pytest`/`mypy`/`pylint` in uv/poetry projects, and frontend package-manager mismatches.
4. **Allow/deny rules** (`~/.claude/settings.json` `permissions.{allow,deny}`) — prefix-glob match against each segment of the compound command.
5. **`permission-auto-approve`** (`~/.claude/bin/permission-auto-approve`) — PermissionRequest hook, last line of defence. Strips `cd <path> &&` prefix and leading `VAR=value` env-prefix, then checks against an internal SAFE list (`go build/test/vet/mod/...`, `uv *`, `pytest*`, `make`, `npm/pnpm/npx/node`, etc.). Only auto-approves if normalised form contains no `&&`/`||`/`|`/`;`/`$(`/`` ` ``.
6. **User prompt** — final fallthrough.

For each trace, we cite the allow-list rule names from `~/.claude/settings.json`.

---

## Trace 1 — `cd "$AION_AUTOPOIESEON/..." && git status && git diff --stat`

**Original command:**

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && git status && git diff --stat
```

1. **Sandbox:** `git` is in `excludedCommands` → command runs **unsandboxed**, so `autoAllowBashIfSandboxed` does not fire.
2. **`pre-tmpdir-guard`:** no `/tmp/` substring → passes.
3. **`pre-bash-toolchain-guard`:** not a blocked pattern (not pip install, not bare pytest in uv) → passes.
4. **Allow rules:** harness splits on `&&` into 3 segments. Segment 1 `cd "$AION_AUTOPOIESEON/..."` matches `Bash(cd *)`. Segment 2 `git status` matches `Bash(git status)`. Segment 3 `git diff --stat` matches `Bash(git diff *)`. **All segments match → auto-allowed.**
5. **`permission-auto-approve`:** not invoked (already allowed by rules).
6. **Final:** **auto-allowed.**

**Note:** despite the user perception that `cd $AION_AUTOPOIESEON/... && git status` always prompts, this exact 3-segment form *should* now auto-allow given the current allow-list. The complaint at `devbox-setup` line 3 (2026-06-19) almost certainly fired against an earlier allow-list snapshot that did not yet contain `Bash(cd *)`. The Shell-discipline rule added later (`USER_AUTHORITY_PROTOCOL.md:200`) explicitly tells the agent to prefer `git -C <path>` instead — which then escapes the allow-list because `Bash(git -C *)` is NOT in the rule set (see Trace 4).

---

## Trace 2 — env-prefix `GOSUMDB=off go mod tidy`

**Original command:**

```bash
GOSUMDB=off go mod tidy
```

1. **Sandbox:** `go` not in `excludedCommands` → runs in sandbox. `proxy.golang.org`, `sum.golang.org` in `allowedDomains` so network is fine. `GOSUMDB=off` is therefore redundant but not harmful. `autoAllowBashIfSandboxed: true` should fire here.
2. **`pre-tmpdir-guard`:** passes (no /tmp/).
3. **`pre-bash-toolchain-guard`:** passes (not blocked).
4. **Allow rules:** the full command string starts with `GOSUMDB=off go mod tidy`, NOT `go mod tidy`. The matcher is prefix-based against literal text — `Bash(go mod *)` does NOT match a string starting with `GOSUMDB=off`. **Allow-list miss.**
5. **`permission-auto-approve`:** strips env-prefix → normalised is `go mod tidy`. The script's NORMALIZED case matches `go\ mod*` → SAFE. No shell metacharacters → **auto-approved.**
6. **Final:** **auto-allowed by hook** (assuming sandbox allow didn't already approve it at step 1).

**Note:** this is the recurring complaint at `oicm-grafana-dashboards-base` line 43 (2026-06-23). Per the agent's own diagnosis in the line-87 assistant ack, the project's `.claude/settings.local.json` actually pinned the entry as `Bash(GOSUMDB=off go mod tidy)` literally, which would auto-allow only that exact env-prefix form. Any *different* env-prefixed go-command (e.g. `GOSUMDB=off go vet ./...`) would not match. The user's complaint is correct in spirit but the *mechanism* is the local allow-list being overly specific, plus sandbox sometimes opting not to bypass on macOS.

---

## Trace 3 — command substitution `grep -n "..." $(go env GOMODCACHE)/...`

**Original command:**

```bash
grep -n "^func (builder \*PanelBuilder)" $(go env GOMODCACHE)/github.com/grafana/grafana-foundation-sdk/go@v0.0.12/barchart/panel_builder_gen.go 2>&1 | tail -40
```

1. **Sandbox:** `grep` and `go` both inside sandbox-allowed list. Runs sandboxed.
2. **`pre-tmpdir-guard`:** `$(go env GOMODCACHE)` expands at runtime to `/tmp/claude/go-mod-cache` (per `~/.claude/settings.json:env.GOMODCACHE`). But the guard inspects the **raw command string** before expansion — the string contains literally `$(go env GOMODCACHE)`, not `/tmp/`. So the guard **does not block**. *However* — if the agent ever pre-expands or types `/tmp/claude/go-mod-cache/...` literally, the guard fires.
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** segment 1 (before `|`) is `grep -n "..." $(go env GOMODCACHE)/...`. The matcher compares this against `Bash(grep *)` → glob `*` matches anything, so this matches. Segment 2 `tail -40` matches `Bash(tail *)`. **Both match → auto-allowed.**
5. **`permission-auto-approve`:** not invoked.
6. **Final:** **auto-allowed.**

**Note:** the user's perception of being prompted (`oicm-grafana-dashboards-base` line 3, 2026-06-23) suggests the harness in fact *does* prompt for this form. Likely culprits: (a) older Claude Code version had less generous `Bash(grep *)` matching that broke on quoted args; (b) the `2>&1` redirection or the `|` pipe causes the matcher to evaluate each side and the `$(...)` substitution component is treated as an extra "command" needing its own allow rule. The matcher's behaviour around `$(...)` is under-documented.

---

## Trace 4 — `git -C <path>` form

**Original command:**

```bash
git -C "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" show "af98f9099:pyproject.toml"
```

1. **Sandbox:** `git` in `excludedCommands` → runs **unsandboxed**.
2. **`pre-tmpdir-guard`:** passes.
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** the full command is `git -C "$AION..." show "..."`. None of the existing rules (`Bash(git status *)`, `Bash(git diff *)`, `Bash(git show *)`, etc.) start with the prefix `git -C` — they start with `git <sub>`. **No rule match → prompt.**
5. **`permission-auto-approve`:** the script's normalisation only strips `cd <path> &&`, not `git -C <path>` patterns. Falls through.
6. **Final:** **prompted.**

**Note:** explicitly diagnosed by the agent at `devbox-setup` line 89 (2026-06-19). The fix would be to either (a) add `Bash(git -C *)` to the allow-list along with mirrored deny rules (`Bash(git -C * rebase *)`, `Bash(git -C * reset *)`, etc.), or (b) drop the discipline rule and accept the `cd && git` form.

---

## Trace 5 — `go env GOMODCACHE`

**Original command:**

```bash
go env GOMODCACHE
```

1. **Sandbox:** `go` not in `excludedCommands` → sandboxed. Read-only command, no network. Should auto-allow via `autoAllowBashIfSandboxed`.
2. **`pre-tmpdir-guard`:** passes.
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** the existing `go`-family rules are `Bash(go test *)`, `Bash(go build *)`, `Bash(go run *)`, `Bash(go mod *)`, `Bash(go get *)`, `Bash(go install *)`, `Bash(go generate *)`, `Bash(go vet *)`, `Bash(go clean -cache)`. **No rule for `go env`** → in pure allow-rule terms, miss.
5. **`permission-auto-approve`:** SAFE list does not include `go env*` — only the 9 `go ...` subcommands above. Falls through.
6. **Final:** depends on `autoAllowBashIfSandboxed` interpretation. If sandbox skip applies → auto-allowed; otherwise → **prompted.**

**Note:** affects every command that uses `$(go env GOMODCACHE)` as an inline argument. Same applies to `go doc`, `go list`, `go version` — all read-only but unallowed.

---

## Trace 6 — multi-line shell loop

**Original command:**

```bash
cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints" && \
  for f in .gitlab-ci.yml docker/mlops/all/docker-compose-mt.yml docker/mlops/all/migration-tests/kube/config; do \
    h1=$(git show "a3dfdd33d:$f" 2>/dev/null | shasum | awk '{print $1}'); \
    h2=$(git -C "$AION_AUTOPOIESEON/mlops-be/OICM-7329_add_vault_to_migrations" show "af98f9099:$f" 2>/dev/null | shasum | awk '{print $1}'); \
    if [ "$h1" = "$h2" ]; then echo "SAME  $f"; else echo "DIFF  $f  mig=$h1  vault=$h2"; fi; \
  done
```

1. **Sandbox:** contains `git` → unsandboxed.
2. **`pre-tmpdir-guard`:** passes.
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** matcher splits on `&&`/`;`/`|`. Inside the loop body, the harness sees segments `h1=$(git show ...)` (NOT a bare command — it's a var assignment that calls `git show` inside `$(...)`), `git -C ... show ...` (no rule), `if [ "$h1" = "$h2" ]; then echo ...` (no `if`-block allow rule), `done` (parsed as a stand-alone bare word). **At least 3-4 segments unmatched → prompt.**
5. **`permission-auto-approve`:** the normaliser checks for `&&`/`||`/`|`/`;`/`$(`/`` ` ``  and falls through if any are present. **Falls through.**
6. **Final:** **prompted.**

**Note:** confirms why multi-line shell scripts always prompt. The user observed similar friction at `oicm-grafana-dashboards-base` line 80. The fix is structural: discourage the agent from writing multi-line shell at all; instead, use a write-then-bash pattern or split into separate sequential bash tool calls.

---

## Trace 7 — bare `go doc` inside `$(...)`

**Original command:**

```bash
grep -n "Orientation\|Stacking\|XTickLabelRotation" $(go env GOMODCACHE)/github.com/grafana/grafana-foundation-sdk/go@v0.0.12/barchart/panel_builder_gen.go 2>&1 | tail -40
```

(Same shape as Trace 3 but distinct command.)

1. **Sandbox:** sandboxed.
2. **`pre-tmpdir-guard`:** passes (literal `$(go env GOMODCACHE)`, no `/tmp/` substring).
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** first segment matches `Bash(grep *)`, second segment `tail -40` matches `Bash(tail *)`. *But* the inner `$(go env GOMODCACHE)` may be treated as a separate command — there is no allow rule for `go env`. Behaviour depends on whether the harness recursively splits on `$(...)`.
5. **`permission-auto-approve`:** falls through (`$(` present).
6. **Final:** **prompted or auto-allowed depending on substitution handling.**

---

## Trace 8 — env-prefix `ANSIBLE_LOCAL_TEMP=... ansible-playbook ...`

**Original command:**

```bash
ANSIBLE_LOCAL_TEMP="$TMPDIR/ansible-tmp" ansible-playbook --syntax-check playbooks/main.yml
```

1. **Sandbox:** `ansible-playbook` runs sandboxed.
2. **`pre-tmpdir-guard`:** the literal string contains `$TMPDIR/ansible-tmp` — does NOT match `/tmp/` or `/var/tmp/` substrings (the env var is unresolved in the string). **Passes.** If the command were `ANSIBLE_LOCAL_TEMP=/tmp/foo ansible-playbook ...` it would **block.**
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** the rule is `Bash(ansible-playbook *)`. The command starts with `ANSIBLE_LOCAL_TEMP=...`, not `ansible-playbook`. **No prefix match → miss.**
5. **`permission-auto-approve`:** strips env-prefix → normalised is `ansible-playbook --syntax-check playbooks/main.yml`. The SAFE list in the script (lines 77-84) does NOT include `ansible-playbook*`. **Falls through.**
6. **Final:** **prompted.**

**Note:** this is the canonical hermetic-cleanup case from `devbox-setup` line 11 (2026-06-19). The agent's fix moved the temp dir into `./.devbox/ansible/tmp/` via `ansible.cfg`, eliminating the need for the env-prefix entirely. The deeper lesson: `permission-auto-approve`'s SAFE list is too narrow (missing `ansible-playbook`, `ansible-lint`, `kubectl`, `helm`, and many others).

---

## Trace 9 — heredoc with `git commit`

**Original command:**

```bash
git commit -m "$(cat <<'EOF'
Commit message body
EOF
)"
```

1. **Sandbox:** `git` in `excludedCommands` → unsandboxed.
2. **`pre-tmpdir-guard`:** passes.
3. **`pre-bash-toolchain-guard`:** passes.
4. **Allow rules:** the full multi-line command starts with `git commit -m "$(cat <<'EOF'...`. `Bash(git commit *)` is in the allow-list, but the heredoc body spans multiple lines and contains `cat <<` — the matcher's handling of heredocs is unclear, but realistically the entire 4-line string is one tool input and the prefix `git commit *` matches the literal first 12 chars. Likely **matches.**
5. **`permission-auto-approve`:** not invoked.
6. **Final:** **auto-allowed.**

**Note:** this is the standard commit-via-HEREDOC pattern from the system prompt's commit instructions. It works *because* the allow-list is generous on `git commit *`. If it failed, every commit would prompt.

---

## Trace 10 — `python3 -c "..."` for ad-hoc one-liners

**Original command:**

```bash
python3 -c 'from app.shared.clients.vault.VaultKeyBuilder import VaultKeyBuilder; print("VaultKeyBuilder: OK")'
```

1. **Sandbox:** `python3` runs sandboxed.
2. **`pre-tmpdir-guard`:** passes (depending on script content).
3. **`pre-bash-toolchain-guard`:** the regex `'python '[!-]*` (line 91 of the script) matches `python <file>` but the `[!-]` glob excludes `-c`. **Passes.** *But* if the cwd has `uv.lock`, **blocks** — the script `case` matches `python <file>` only, not `python -c`. So this case passes the guard. **Passes.**
4. **Allow rules:** `Bash(python3 *)` matches. **Auto-allowed.**
5. **`permission-auto-approve`:** not invoked.
6. **Final:** **auto-allowed.**

**Note:** This is the smoke-test pattern used in the mlops-be vault session. It works fine because `Bash(python3 *)` is broad. The catch: `python3 -c '...'` is essentially arbitrary code execution; the allow-list trades safety for friction here. The toolchain-guard would block `python script.py` in a uv project but happily allows `python3 -c '<script body>'`.

---

## Cross-cutting findings from the traces

1. **`cd $abs && git ...` form actually works now** — the user's original complaint pre-dated the `Bash(cd *)` rule. The friction migrated to `git -C` once the `Shell discipline` rule kicked in.
2. **`permission-auto-approve`'s normaliser strips `cd` and env-prefix correctly**, but its SAFE list is missing `ansible-playbook`, `kubectl`, `helm`, `go env/doc/list`, `git show/branch/blame`, and `docker compose/inspect/logs/ps/images`. Adding those would catch ~30-50% of the remaining prompts.
3. **Multi-line shell scripts always prompt** — no normaliser can rescue them. The fix is behavioural (write file + bash exec instead of multi-line inline).
4. **`pre-tmpdir-guard`'s `/tmp/` substring matching is overzealous** but does NOT fire on `$TMPDIR` (unresolved env var stays as literal). It would fire if the agent ever expanded the path in its mind and typed `/tmp/claude/...` literally — which it does occasionally for the `GOMODCACHE` path.
5. **Sandbox `excludedCommands: [docker, docker-compose, podman, git]`** means every git command pays the unsandboxed cost (no `autoAllowBashIfSandboxed` bypass). Combined with the allow-list-only path, git is the heaviest contributor to prompts at 56 invocations (12% of corpus).
