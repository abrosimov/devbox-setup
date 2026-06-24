# Comprehensive Permissions Friction Audit

> **Status:** read-only audit, no settings touched.
> **Author:** Claude (Opus 4.7) acting under user request.
> **Original brief (verbatim, Russian):** «Задача: обойти проекты внутри, посмотреть на настройки claude. Также обойти логи сессий и пр в $HOME/.claude/ и оценить настройки. Есть ощущение, что у нас/меня системная проблема с настройками permissions, и claude (в тч агенты) даже на банальный diff из TMPDIR просят разрешения. В общем, подготовь мне отчёт. Отсмотри доскональноы, выяви паттерны и проблемы, классифицируй их и для каждого класса найди 5-10 root causes. Потом я сделаю ревью документа и прикинем куда двигаться дальше.»
> **Date opened:** 2026-06-23
> **Date this revision:** 2026-06-24
> **Location of source-of-truth:** `roles/devbox/files/dot_claude/future_projects/comprehensive_analysis/` (this directory)

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Scope, data sources, methodology](#2-scope-data-sources-methodology)
3. [Numerical findings (the corpus speaks)](#3-numerical-findings-the-corpus-speaks)
4. [The seven classes of permission friction](#4-the-seven-classes-of-permission-friction)
   - [Class A — Allow-list patterns that miss real commands](#class-a--allow-list-patterns-that-miss-real-commands)
   - [Class B — "Always allow" → settings.local.json pollution](#class-b--always-allow--settingslocaljson-pollution)
   - [Class C — Hook architecture amplifies friction](#class-c--hook-architecture-amplifies-friction)
   - [Class D — Sandbox / permission boundary mismatches](#class-d--sandbox--permission-boundary-mismatches)
   - [Class E — CLAUDE.md and agent prompts induce friction-prone shapes](#class-e--claudemd-and-agent-prompts-induce-friction-prone-shapes)
   - [Class F — Project-scope leakage and stale rules](#class-f--project-scope-leakage-and-stale-rules)
   - [Class G — Sub-agent permission scope isolation](#class-g--sub-agent-permission-scope-isolation)
5. [Cross-cutting structural observations](#5-cross-cutting-structural-observations)
6. [Pattern summary (one-page view)](#6-pattern-summary-one-page-view)
7. [Suggested next-step directions](#7-suggested-next-step-directions)
8. [What was deliberately NOT touched](#8-what-was-deliberately-not-touched)
9. [Appendix: how to navigate the `data/` directory](#9-appendix-how-to-navigate-the-data-directory)

---

## 1. Executive summary

The user's intuition is correct: there is a **systemic permission-friction problem** in this Claude Code setup. But the mechanism is multi-layered and the popular explanations are partially wrong.

**The "diff in TMPDIR prompts for permission" complaint resolves to a TWO-layer cause:**

1. Layer one — `~/.claude/bin/pre-tmpdir-guard` hard-blocks (exit 2) any Bash command whose string contains the substring `/tmp/`, regardless of context. So `diff /tmp/a /tmp/b` (where the user expected sandbox auto-allow) gets `BLOCKED` by a PreToolUse hook, not by the permission system. The user perceives this as "asking for permission"; the harness surfaces both as "tool call blocked, model must react", and the model often re-issues the command, looking like a re-prompt.
2. Layer two — `$TMPDIR` on macOS expands to `/var/folders/.../T/`, NOT `/tmp/`. So the hook *doesn't* fire on `diff "$TMPDIR/a" "$TMPDIR/b"`. The agent's mental model "I'm using TMPDIR" is correct; the friction comes from the agent occasionally typing `/tmp/...` literally (because some env vars in the global settings — e.g. `GOMODCACHE=/tmp/claude/go-mod-cache` — point inside `/tmp/`, and the agent picks up on those paths).

**The "agents ask permission for `cd ... && git status && ...`" complaint resolves differently from the user's hypothesis:**

The user thought `CLAUDE.md` was the cause. CLAUDE.md is fine. The actual mechanism:

1. The matcher splits a compound command on `&&`/`||`/`|`/`;` and matches each segment independently. `cd "$AION_AUTOPOIESEON/..."` matches `Bash(cd *)`; `git status` matches `Bash(git status)`; `git diff --stat` matches `Bash(git diff *)`. **This form actually works now.** (See [trace 1](data/bash-command-samples/normalization-trace.md#trace-1--cd-aion_autopoiseon--git-status--git-diff---stat)).
2. The original complaint (dated 2026-06-19, [verbatim quote here](data/session-excerpts/user-complaints-verbatim.md#L111)) pre-dated the addition of `Bash(cd *)` to the global allow-list. The user added it, friction subsided for that exact pattern.
3. Friction then **migrated** to `git -C <path>` — because the user wrote a new shell-discipline rule in `USER_AUTHORITY_PROTOCOL.md:200` telling agents to prefer `git -C` over `cd && git`. But the allow-list has no `Bash(git -C *)` rule (and the deny rules for `git rebase`/`git reset` also don't cover `git -C * rebase`). So agents that follow the discipline rule pay a fresh prompt tax.

**The dominant cause of remaining friction, across 459 sampled bash commands:**

- **21.1 %** of commands fail a conservative simulation of the global allow-list. The real prompt rate is higher (the simulation is false-negative biased).
- **15.7 %** of commands begin with `cd <absolute-path>` — auto-allowed at segment 1 but each subsequent segment must independently match.
- **14.2 %** are chained with `&&`/`||`/`;` — each segment is matched independently.
- **4.4 %** carry an env-prefix (`GOSUMDB=off ...`, `ENV_NAME=local ...`, `ANSIBLE_LOCAL_TEMP=... ...`) — `permission-auto-approve` strips it correctly but its SAFE-list is too narrow.
- **2.0 %** are multi-line shell blocks (`for/do/done`, `if/then/fi`) — no normaliser can rescue these; every one prompts.

**The most surprising finding:**

When the user clicks "Always allow" in a prompt, Claude Code persists the **literal command string** to `.claude/settings.local.json`. Over time these files accumulate **shell-keyword fragments** (`Bash(fi)`, `Bash(done)`, `Bash(EOF)`, `Bash(then echo "Go")`) and **bare file paths** (`Bash(internal/fakedata/generator.go)`) as if they were commands. The `node-health-monitor` project has 132 lines of this. Worktrees inherit nothing from `base/`, so 40+ separate allow-lists drift independently across each user's checkouts.

**Quantified pain (from 25 most recent JSONL session transcripts):**

| Metric | Count |
|---|---:|
| User complaints about permissions, verbatim | **18** |
| Assistant acknowledgements of root cause | **12** |
| Raw JSONL records mentioning "permission" | **554** (capped sample of 200 in `data/`) |
| Bash commands sampled | **459** |
| Commands that miss the global allow-list (conservative) | **97** (21.1 %) |
| `.claude/settings.local.json` files across `~/Work/*` | **43** |
| Garbage shell-keyword rules across those files | **13** |
| Bare file-path "rules" stored as Bash patterns | **9** |
| Long literal command "rules" ≥120 chars (single-use) | **24** |
| Projects with committed `.claude/settings.json` (shared with team) | **3** |
| Worktrees observed with their own `.claude/settings.local.json` | **~40** |

---

## 2. Scope, data sources, methodology

### Scope

- **Global Claude Code config:** `~/.claude/{settings.json,hooks.json,bin/*}` — full read.
- **Per-project Claude Code config:** every `.claude/settings.json` and `.claude/settings.local.json` under `~/Work/*` and their worktrees (46 files across 36 projects).
- **Session transcripts:** 25 most recent `.jsonl` files under `~/.claude/projects/*/` covering roughly two months of activity. Each transcript is one Claude Code session, capturing every user message, every assistant message, every tool_use input, every tool_use result, and every permission-mode change.

### Out-of-scope (flagged for review, not analysed)

- The 8 Python test files under `~/.claude/bin/test_*.py` (the hooks have unit tests; correctness is not the issue, configuration is).
- Plugin LSP server configuration (`gopls`, `pyright`, `typescript` plugins).
- MCP server registration mechanics (covered in the project's CLAUDE.md, irrelevant here).
- `~/.claude/agents/`, `~/.claude/skills/`, `~/.claude/commands/` — interesting downstream effects but the friction we're investigating lives below them.

### Methodology

1. **Global config inventory.** Read `settings.json` (396 lines), `hooks.json` (234 lines), and every script in `bin/`.
2. **Per-project inventory.** `find ~/Work -maxdepth 5 -path '*/.claude/*' -name 'settings*.json'`. Snapshotted representative files to `data/settings-snapshots/`.
3. **Hooks snapshot.** Copied the five Bash-relevant hooks to `data/hooks-snapshots/`.
4. **Session log mining.** Spawned a sub-agent (general-purpose) to:
   - Extract verbatim user complaints (`type==user`, content matching `permission|разреш|prompt|спрашивает|ask|просит|кликаю|кликать|задолбал|раздражает|надоел`).
   - Extract verbatim assistant acknowledgements (`type==assistant`, content matching `allow rule|allowlist|permission|hook|sandbox|excludedCommands|cd .*&&|env-prefix|GOSUMDB`).
   - Extract 459 bash tool_use commands and classify by shape (bare, cd-prefix, env-prefix, chained, piped, redirected, multiline, heredoc).
   - Simulate the global allow-list against each command (conservative head-token match).
   - Trace 10 representative commands through the full pipeline (sandbox → tmpdir guard → toolchain guard → allow/deny → auto-approve hook → prompt).
5. **Cross-correlation.** Tied each user complaint to the matching technical mechanism via the trace evidence.

All raw evidence is in `data/`. Citations in the report use the form `data/<path>:line` or `<session-shortname> line N uuid <8 chars>`.

---

## 3. Numerical findings (the corpus speaks)

### 3.1 Shape distribution of 459 sampled bash commands

| Shape | Count | % of total | Friction risk |
|---|---:|---:|---|
| `redirected` (contains `>/dev/null`, `2>&1`, `> file`) | 152 | 33.1 % | Low — redirection itself doesn't break matching; head still matches. |
| `piped` (contains `\|`) | 93 | 20.3 % | Medium — segment 2 onwards must independently match. |
| `cd-prefix` (begins with `cd <abs> && ...`) | 72 | 15.7 % | Medium — first segment OK, rest depends. |
| `chained` (contains `&&`/`\|\|`/`;` outside `cd`) | 65 | 14.2 % | Medium — each segment matched. |
| `bare` (single command, no operators) | 49 | 10.7 % | Low — pure allow-list hit. |
| `env-prefix` (begins with `VAR=value ...`) | 19 | 4.1 % | **High** — `permission-auto-approve` strips it, but SAFE-list too narrow. |
| `multiline` (`for/do/done`, `if/then/fi`, embedded newlines) | 9 | 2.0 % | **Maximum** — never auto-allowed by any layer. |

> Source: `data/bash-command-samples/statistics.md`, `data/bash-command-samples/all-commands-classified.csv`.

### 3.2 Top base commands (first-segment token, env-prefix stripped)

| Base | Count | % |
|---|---:|---:|
| `grep` | 135 | 29.4 % |
| `cd` | 76 | 16.6 % |
| `ls` | 74 | 16.1 % |
| `git` | 56 | 12.2 % |
| `find` | 26 | 5.7 % |
| `cat` | 21 | 4.6 % |
| `rg` | 14 | 3.1 % |
| `uv` | 9 | 2.0 % |
| `../base/.venv/bin/python` | 7 | 1.5 % |
| `wc` | 6 | 1.3 % |

Note: `cd` appearing as a base-command 76 times means **16.6 % of bash calls start with `cd`** — the user's CLAUDE.md explicitly forbids this (`USER_AUTHORITY_PROTOCOL.md:200`), but the rule is widely violated. Either the rule isn't reaching agent contexts, or agents weigh it lower than convenience.

### 3.3 Top (base, sub) pairs

| Pair | Count |
|---|---:|
| `grep -n` | 52 |
| `grep -rn` | 45 |
| `cd "$AION_AUTOPOIESEON/mlops-be/OICM-7329_migration_for_encrypting_existing_blueprints"` | 39 |
| `cd ~/Work/mlops-be/OICM-7329_migration_for_masking_encrypted_blueprints` | 23 |
| `ls -la` | 17 |
| `git diff` | 17 |
| `grep -nE` | 12 |
| `rg -n` | 12 |
| `git status` | 10 |
| `uv run` | 9 |

Note: two `cd` invocations together account for **62 calls (13.5 %)** with identical absolute-path arguments. The agent is repeatedly re-`cd`-ing to the same worktree across separate Bash tool calls. This is wasted matcher work AND wasted user context — the second-most-frequent command in the corpus is just "cd into the worktree I'm already supposed to be in".

### 3.4 Specific patterns within commands

| Pattern | Count | % |
|---|---:|---:|
| `cd "$...` (env-var in quoted path) | 43 | 9.4 % |
| `&&` | 139 | 30.3 % |
| `2>&1` | 90 | 19.6 % |
| `\| head` | 233 | 50.8 % |
| `\| tail` | 37 | 8.1 % |
| `\| wc` | 6 | 1.3 % |
| `>/dev/null` | 211 | 46.0 % |
| `env-prefix` | 20 | 4.4 % |
| `$(...)` | 8 | 1.7 % |
| `heredoc <<` | 0 | 0.0 % |

The `| head` / `>/dev/null` numbers are striking: **half** of all bash calls are pipe-truncated, and **almost half** redirect stderr. This is good agent behaviour (managing context budget), but it inflates the pipe/redirect shape categories and means the allow-list MUST cope with multi-segment commands cleanly.

### 3.5 Allow-list miss simulation

Commands where the first segment's head token (after env-prefix stripping) does NOT appear in any base allow rule, OR where at least one chained segment's head does not match: **97 of 459 (21.1 %)**.

Caveats — the **real** miss rate is higher:

- The simulation accepts a head-match even when subcommand rules would still deny (e.g. `git rebase` would match `git` base but deny on `Bash(git rebase *)` — counted as allowed in the sim, blocked in reality).
- The matcher is prefix-based against the FULL command string, not just the head token. `go test ./...` matches `Bash(go test *)` cleanly, but `go test ./... && go vet ./...` is split into two segments by the matcher; both must independently match.
- Compound chains with `$(...)` substitution are not handled by the simulation but the harness's behaviour around `$(...)` is under-documented.

**Practical lower bound on prompt rate: 21 %.** Practical upper bound (from sampling user complaints): closer to 30-40 % for sessions with heavy git/multi-worktree activity.

---

## 4. The seven classes of permission friction

For each class: **symptoms** → **evidence** → **5-10 root causes** → **fix layer** (where any fix would live).

Per the user's request, each class has **at least 5 root causes**; most have more.

---

### Class A — Allow-list patterns that miss real commands

> The rule exists, but the matcher never reaches it because the actual command shape doesn't fit the rule. This is the largest single class.

#### Symptoms

- "I told it `git diff` was allowed but it asked again for `git show`."
- "Why does `go env GOMODCACHE` need approval?"
- "Bare `git branch -a` prompts even though `git branch` is in the list."

#### Evidence

- Top friction commands #2-#7 in `data/bash-command-samples/top-friction-commands.md` all share the pattern `cd <abs> && git <unusual-sub>`.
- Trace 4 in `data/bash-command-samples/normalization-trace.md` walks through `git -C <path>` end-to-end and confirms no rule matches.
- Trace 5 does the same for `go env`.
- User quote: "На каждый diff делать ask permissions? Серьезно? Агенту доступна TMPDIR и все равно он спрашивает разрешения" — `data/session-excerpts/user-complaints-verbatim.md:19`.
- Assistant acknowledgement: «В `.claude/settings.local.json` allowlist жёстко с префиксом `GOSUMDB=off` … Без префикса каждый `go mod tidy` / `go build` / `make generate` = новый prompt. Плюс там вообще нет `git diff`, `git status`, `git log`, `go doc` — поэтому агент стучится на любую diff-проверку.» — `data/session-excerpts/agent-acknowledgements.md:7`.

#### Root causes (10)

1. **Env-var prefix is never stripped at the matcher layer.** `GOSUMDB=off go mod tidy` doesn't match `Bash(go mod *)` because the matcher sees the literal `GOSUMDB=off ...` head. The user's most frequent Python test command is `ENV_NAME=local uv run pytest ...` — same problem at scale. **(`permission-auto-approve` does strip env-prefixes, but only as a fallback after the matcher already missed; see Class C.)**
2. **Globals enumerate Go subcommands but skip `env`, `list`, `doc`, `tool`, `version`.** The allow-list has `go test *`, `go build *`, `go mod *`, `go vet *`, `go run *`, `go get *`, `go install *`, `go generate *`, plus `go clean -cache` — but no `go env`, `go list`, `go doc`, `go tool *`, `go version`. Every `$(go env GOMODCACHE)` substitution prompts.
3. **Globals enumerate git subcommands incompletely.** Has `git status`/`status *`, `git diff`/`diff *`, `git log *`, `git show *` (good), `git branch`/`branch *`, `git blame *`, `git ls-files`, `git ls-tree`, `git rev-parse`, `git stash *`, `git checkout -b *`, `git switch *`, `git remote *`, `git fetch *`, `git config --get *`, `git worktree list`, `git commit *`, `git push *`. **Missing:** `git merge-base`, `git rev-list`, `git ls-remote`, `git for-each-ref`, `git show-ref`, `git rev-list`, `git describe`, `git tag` (read-only), `git reflog`, `git cat-file`, `git symbolic-ref`. Top-friction commands #3-#6 all hit these gaps with `git ls-remote`, `git for-each-ref`.
4. **`Bash(cmd)` vs `Bash(cmd *)` duplicates inconsistent.** `Bash(make)` AND `Bash(make *)` are both listed (good). But `Bash(date)` is there without `Bash(date *)`, so `date -u +"%Y..."` prompts. Some commands have only the exact form, some only the glob form, and the matcher does not generalise.
5. **Common read-only diagnostic tools entirely absent.** `diff -r`, `comm`, `column`, `paste`, `expand`, `hexdump`, `od`, `md5`, `shasum`, `tee`, `nproc`, `uptime`, `tar -t`, `unzip -l`, `column -t`, `ps`, `lsof` — every one is read-only-safe but every one prompts. (Some users add them to `settings.local.json` per-project, but globally they're missing.) The friction commands #11-#15 all hit at least one.
6. **`git -C <path>` form is uncovered.** When agents follow `USER_AUTHORITY_PROTOCOL.md:200`'s shell discipline rule ("use `git -C <path>` instead of `cd <path> && git`"), they hit the wall. The allow-list has `Bash(git status *)` but not `Bash(git -C *)`. Worse, the deny rules (`Bash(git rebase *)`, `Bash(git reset *)`) also miss `git -C * rebase` — making this an unsafe gap once you do add the allow. See `data/session-excerpts/agent-acknowledgements.md:145` for the agent's own diagnosis.
7. **Sandbox `excludedCommands: ["docker", "docker-compose", "podman", "git"]`** means git runs UN-sandboxed, so `autoAllowBashIfSandboxed` never fires for git. Every git command therefore depends entirely on the explicit allow-list — and with #3 and #6 above, that's a lot of misses. Git is 12.2 % of corpus (56 invocations).
8. **`Bash(.claude/bin/*)` is relative.** When `/techne-*` slash commands shell out to absolute paths (`~/.claude/bin/validate-config.py`), the matcher sees `/Users/kabrosimov/.claude/bin/validate-config.py` and the relative-pattern `Bash(.claude/bin/*)` doesn't match it.
9. **`Bash(fish -c 'proj wt *')` is over-literal.** Single-quote requirement is brittle. Any agent that uses double quotes or no quotes around the inner command body misses. The `proj wt` wrapper is the worktree-creation entrypoint; missing this means `claude --worktree` workflows hit prompts.
10. **No allow rules for the user's own scripts.** `Bash(./scripts/*.sh)`, `Bash(./tools/*)`, `Bash(./bin/*)` — none of these are in the global. Per-project users often add them to `settings.local.json` one at a time as friction accumulates.

#### Fix layer

Mostly global `~/.claude/settings.json`. A handful (#7) requires editing the `sandbox.excludedCommands` list. A handful (#10) is naturally per-project.

---

### Class B — "Always allow" → settings.local.json pollution

> When the user clicks "Always allow", the harness saves the **literal command** rather than generalising. Over time `settings.local.json` becomes a junkyard that doesn't prevent re-prompts.

#### Symptoms

- `settings.local.json` grows monotonically, hits 100+ rules.
- Re-prompts continue despite the bloat.
- Multi-line shell scripts produce nonsensical "rule" entries.

#### Evidence

`~/Work/node-health-monitor/.claude/settings.local.json` (132 lines, snapshot at `data/settings-snapshots/node-health-monitor_.claude_settings.local.json`):

```jsonc
"Bash(if [ -f \"go.mod\" ])",
"Bash(then echo \"Go\")",
"Bash(elif [ -f \"pyproject.toml\" ])",
"Bash([ -f \"requirements.txt\" ])",
"Bash(then echo \"Python\")",
"Bash(else echo \"Unknown\")",
"Bash(fi)",
"Bash(done)",
"Bash(do if ! grep -q \"//go:build integration\" \"$f\")",
"Bash(while read f)",
"Bash(while read file)",
"Bash(do)",
"Bash(then echo \"$f\")",
"Bash(EOF)",
"Bash(internal/fakedata/generator.go)",
"Bash(internal/fakedata/debug_test.go)",
"Bash(internal/health/checker_run_status.go)",
"Bash(internal/health/fake_data_marker.go)",
"Bash(internal/httpx/retryable_client_test.go)",
"Bash(internal/kube/config.go)",
"Bash(internal/kube/manager.go)",
"Bash(internal/kube/node.go)",
"Bash(internal/kube/node_test.go)",
"Bash(for file in internal/fakedata/generator.go internal/fakedata/debug_test.go internal/health/checker_run_status.go internal/health/fake_data_marker.go internal/httpx/retryable_client_test.go internal/kube/config.go internal/kube/manager.go internal/kube/node.go internal/kube/node_test.go)",
```

`~/Work/mlops-be/OICM-7708_debug_pvc_creation/.claude/settings.local.json` — 14 fully literal pytest invocations with hard-coded test files. Snapshot at `data/settings-snapshots/mlops-be_OICM-7708_debug_pvc_creation_.claude_settings.local.json`. Sample:

```jsonc
"Bash(ENV_NAME=local uv run pytest tests/app/shared/clients/kubernetes/v2/test_kubernetes_client.py tests/app/shared/clients/kubernetes/v2/test_KarmadaClient.py tests/app/shared/clients/nfs/pv_manager/test_nfs_pv_manager.py -q)",
"Bash(ENV_NAME=local uv run pytest tests/app/shared/clients/kubernetes/v2/test_kubernetes_client.py::TestKubernetesClient::test_should_raise_KubernetesClientError_when_delete_by_manifest_raises_ApiException tests/app/shared/clients/kubernetes/v2/test_kubernetes_client.py::TestKubernetesClient::test_should_fail_during_updating_custom_object)",
```

Across all 43 `settings.local.json` files: **13 shell-keyword fragments, 9 bare file-path rules, 24 literal commands ≥120 chars**.

#### Root causes (10)

1. **Multi-line shell scripts get tokenised, then each token offered as "Always allow".** A `for f in ...; do if ! grep -q ...; then echo "$f"; fi; done` becomes ~10 separate prompts. The user clicks through, and 10 useless `Bash(...)` rules persist. The harness has no "generalise this rule before persisting" step.
2. **Heredocs split into per-line tool calls.** `node-health-monitor`'s `Bash(EOF)` and `Bash(internal/fakedata/...)` file-path entries are heredoc contents stored as rules.
3. **Long literal commands stored unchanged.** The 470-char `ENV_NAME=... uv run pytest tests/foo/bar.py::TestX::test_y -v` rule never re-matches because the test selector changes every run.
4. **Env-var prefixes baked into persisted rule.** When the user clicks "Always allow" for `GOSUMDB=off go mod tidy`, the rule `Bash(GOSUMDB=off go mod tidy)` is added. Next time the agent runs `go mod tidy` without the prefix, it re-prompts. (Documented in agent ack at `data/session-excerpts/agent-acknowledgements.md:7`.)
5. **Worktree-local settings don't inherit from `base/`.** Every new `mlops-be/MLOPS-XXXX_*` worktree starts with an empty `settings.local.json`, so all the "always allows" the user accumulated in `base/` are useless. With ~30+ worktrees per project, this re-friction is multiplicative — and there's no migration when the user runs `proj wt add <branch>`.
6. **`Skill(...)`, `SlashCommand(...)`, `WebFetch(domain:...)` rules persisted alongside Bash rules.** Files mix all rule types. Some `Skill(plan)`, `Skill(implement)`, `Skill(review)` rules reference skills that have since been renamed (now `Skill(techne-plan)` etc.) — dead rules.
7. **One-off WebFetch domains lock in forever.** `WebFetch(domain:dev.to)`, `WebFetch(domain:bsonspec.org)`, `WebFetch(domain:dario.cat)` — one-time reference lookups locked into durable rules with no expiry.
8. **No deduplication / collapse.** Same file contains both `Bash(make:*)` and `Bash(make build:*)` — the second is redundant under the first. The harness never collapses.
9. **No size guardrail / warning.** `node-health-monitor` at 132 lines / ~120 rules has no warning. Reading/diffing this on every prompt evaluation is non-trivial.
10. **The user has built `techne-fewer-permission-prompts` skill to mitigate this**, but it only handles read-only Bash + MCP commands and runs reactively after the mess has already accumulated.

#### Fix layer

- Harness UX (out of scope — Anthropic's harness): "Always allow" should offer a generalisation step.
- Tooling (within scope): post-hoc cleanup script + `worktree-create` hook extension to seed `settings.local.json` from `base/`.
- Behaviour (within scope): teach agents to avoid multi-line / heredoc shell.

---

### Class C — Hook architecture amplifies friction

#### Symptoms

- "I'm told my tool was 'blocked', but I didn't see a prompt."
- Post-edit errors after every Edit.
- Stop hook re-asks model to fix issues at session end.

#### Evidence

11 PreToolUse + PostToolUse + Stop + PreCompact + SessionEnd hooks defined in `data/hooks-snapshots/global-hooks.json`. Hook scripts in `data/hooks-snapshots/`.

#### Root causes (10)

1. **`pre-tmpdir-guard` hard-blocks instead of redirecting.** Returns exit 2 on `/tmp/` substring in command string. The harness presents this to the model as a denial that the model must react to. The hook's stderr message ("Use `$root/tmp/` instead") is text the model has to read and re-issue; many models retry the same command first, triggering another deny. User-perceived loop = "permission prompts".
2. **`pre-tmpdir-guard` doesn't whitelist sandbox-writable subpaths.** Sandbox writable list includes `/tmp/claude`. The guard ignores this and blocks `/tmp/claude/foo` just as it blocks `/tmp/random`. Two layers disagree about the same path family.
3. **`pre-tmpdir-guard` operates on the literal command string.** If `$TMPDIR` is unresolved in the string it passes; if the agent expands `$TMPDIR` to `/var/folders/.../T/` (which is the macOS reality) it still passes. But if the agent expands `GOMODCACHE` to `/tmp/claude/go-mod-cache/...` it BLOCKS — because `/tmp/` is a substring. Inconsistent semantics depending on whether the agent quotes literals vs uses env vars.
4. **Multiple PreToolUse hooks chained on Bash matcher.** `pre-bash-toolchain-guard` → `pre-tmpdir-guard` → `pre_bash_safety_gate.py` → `pre-bash-boundary-wrap`. Any of them can block. Each invocation spawns a fresh interpreter; cumulative latency is non-trivial. Any one returning exit 2 looks identical to a permission denial to the model.
5. **`permission-auto-approve` SAFE list is narrow.** Lines 77-84 of the hook script cover only `go build/test/vet/mod/get/install/generate/run`, `goimports`, `golangci-lint`, `mockery`, `sqlc`, `uv *`, `uvx *`, `pytest*`, `ruff *`, `mypy *`, `python *`, `python3 *`, `npm *`, `npx *`, `pnpm *`, `node *`, `make *`, `cargo *`, `rustc *`. **Missing:** `ansible-playbook`, `ansible-lint`, `kubectl *`, `helm *`, `docker *`, `git show`, `git branch`, `git ls-remote`, `git for-each-ref`, `go env`, `go list`, `go doc`, `go version`, `go tool *`. Adding these would catch ~30-50 % of remaining prompts.
6. **`permission-auto-approve` env-prefix loop handles single-token VARs only.** Pattern `^[A-Z_][A-Z0-9_]*=[^[:space:]]*[[:space:]]*` matches `GOSUMDB=off ` but FAILS to strip `OICM_API__BASE_URL="https://oicm.dev.airgap1.lab/"` (the value contains `://` which is not "no-space"). Multi-value env-prefixes prevent the strip; the SAFE-list check then sees the raw env-prefix and falls through.
7. **`permission-auto-approve` rejects on shell metachars in NORMALIZED form.** After stripping `cd` and env-prefix, the check `case "$NORMALIZED" in *'&&'*|*'||'*|*'|'*|*';'*|*'$('*|*'`'*) ;;` falls through. So a chained command with `make test && make lint` (both SAFE bases) never gets auto-approved — even though both segments are individually safe.
8. **PostToolUse `post-edit-lint` and `post-edit-typecheck` blocking on failure.** They surface as "tool finished with error" after every edit. Not technically a permission prompt, but contributes to "Claude won't do anything without me clicking something" perception.
9. **`Stop`-hook `stop-lint-gate` can block session end.** Lint failure → model is re-prompted to fix → extra silent churn before the turn closes.
10. **No central hook-outcome telemetry.** No log says "hook X exited 2 on command Y" centrally. User can't answer "what fraction of my prompts come from hooks vs from missing allow rules?" without manually mining JSONL.
11. **`pre-plan-code-guard` blocks Edit/Write/MultiEdit unconditionally in plan mode.** If user is in plan mode and the agent tries to edit, this denies and surfaces as a tool failure. Reasonable in principle; surprising in practice if you forgot you were in plan mode.

#### Fix layer

Hook script edits + (for #5/#6/#7) extending `permission-auto-approve`.

---

### Class D — Sandbox / permission boundary mismatches

#### Symptoms

- "Sandbox-allowed paths still prompt."
- Git commands prompt even though they should be safe.
- "I added an MCP rule to the project but the sub-agent still can't use it."

#### Evidence

`~/.claude/settings.json:281-395` (sandbox config block). Snapshot at `data/settings-snapshots/global-settings.json`.

#### Root causes (9)

1. **Sandbox writable list ≠ permission allow scope.** Sandbox writable: `/dev/{stdout,stderr,null,tty,dtracehelper,autofs_nowait}`, `/tmp/claude`, `/private/tmp/claude`, `~/.npm/_logs`, `~/.claude/debug`, `.`, `$TMPDIR`. Perm allow has `Bash(cd *)` (any dir) and no path-scoped Bash rules. A command that the agent thinks should be fine fails at sandbox boundary even when perm-allowed, and vice versa.
2. **`excludedCommands: ["docker", "docker-compose", "podman", "git"]`** — these always run UN-sandboxed. Never get `autoAllowBashIfSandboxed` bypass. Combined with under-specified git allow rules (Class A #3), this is the single biggest source of git-related prompts.
3. **`enableWeakerNetworkIsolation: true`** in global, but project-level files don't inherit it. Some project sandboxes effectively re-enable strict isolation by overriding.
4. **`allowLocalBinding: true`** but no documented listener-port allow-list. Model may attempt `localhost:8080` and get prompted.
5. **macOS `$TMPDIR` vs `/tmp` confusion.** Sandbox writable lists `$TMPDIR` (`/var/folders/.../T/`) and `/tmp/claude` — but NOT generic `/tmp/foo`. `pre-tmpdir-guard` adds another layer that blocks any `/tmp/` substring including `/tmp/claude/...`. The two layers do not agree.
6. **`Read(~/.ssh/**)` deny rule duplicates sandbox's `read.denyOnly` list.** Defence in depth, but the user's settings document the same rule twice without acknowledging which actually fires (the sandbox's, which is checked first).
7. **No `Write(...)`/`Read(...)` allow-list** except `Read(//tmp/**)` in one project. User relies entirely on `defaultMode: acceptEdits` + deny rules. Removing acceptEdits (e.g. in a code review session) would produce a flood of prompts.
8. **MCP rules duplicated.** Global allows `mcp__*` (glob). Several projects redundantly re-allow `mcp__atlassian__getJiraIssue` etc. — dead code given the glob, but they're not removed.
9. **Sub-agent MCP scope drops main session's allows.** Evidence: `data/session-excerpts/user-complaints-verbatim.md:67-100` — Jira-agent sub-agent fails on `mcp__atlassian__*` calls despite the parent session having those approved. Two failed `task-notification` blocks with `<result>**Exploration blocked — permission denied on all Atlassian MCP calls.**</result>`. (See Class G for full treatment of this — promoted to its own class.)

#### Fix layer

`~/.claude/settings.json` sandbox section + per-project sandbox overrides.

---

### Class E — CLAUDE.md and agent prompts induce friction-prone shapes

> The user's hypothesis. Partially valid, with a twist: CLAUDE.md doesn't cause the friction directly, but its shell-discipline rule generates a *different* set of prompts than the one it eliminates.

#### Symptoms

- Agent generates `cd "$AION_AUTOPOIESEON/<proj>/<branch>" && git status && git log -3` — even though the rule says don't.
- Agent generates `git -C <path> show ...` — which has no allow rule.
- Multi-line shell loops appear in tool calls.

#### Evidence

- `USER_AUTHORITY_PROTOCOL.md` (deployed as `~/.claude/CLAUDE.md`), shell-discipline rule at line ~200: "Never prefix a command with `cd <path> &&`. To run a command in another directory, use the tool's path flag (`git -C <path>`, `make -C <path>`, `pytest --rootdir <path>`)."
- Top-friction commands #1-#7 in `data/bash-command-samples/top-friction-commands.md`: agent uses `cd "$AION_AUTOPOIESEON/..." && ...` despite the rule.
- Trace 4 in `data/bash-command-samples/normalization-trace.md`: `git -C <path>` form has NO allow rule.

#### Root causes (8)

1. **CLAUDE.md says "use `git -C`" but `git -C *` is not in the allow-list.** Self-defeating: the rule's prescribed form pays a permission tax.
2. **Agents still generate `cd <path> && cmd` despite the rule.** 16.6 % of bash calls start with `cd`. Either CLAUDE.md isn't reaching agent contexts (sub-agents in particular may not load it), or agents weight convenience over the rule.
3. **Agents wrap commands in shell-snippets for safety.** `if [ -f go.mod ]; then ...; elif [ -f pyproject.toml ]; then ...; fi` — see `node-health-monitor`'s persisted garbage entries. CLAUDE.md never explicitly tells them "avoid multi-line shell as Bash tool input — split into separate calls."
4. **Heredocs encouraged for commit messages.** The project's own commit instructions in CLAUDE.md show `git commit -m "$(cat <<'EOF' … EOF)"` — which gets tokenised by the harness and produces `Bash(EOF)` allow entries when "Always allow" fires.
5. **Sub-agents start with no shared permission cache.** Each `Agent` invocation runs with fresh state. Parent's "always allows" don't reach the child. Child re-prompts → user clicks → entry persisted in the **child's** scope (sub-agent has its own settings target) which the parent never sees.
6. **`/techne-*` slash-commands shell out to absolute paths.** Script call (e.g. `~/.claude/bin/validate-config.py`) needs its own allow rule; the absolute-path form doesn't match `Bash(.claude/bin/*)`. (See Class A #8.)
7. **Worktree convention forces re-priming.** `proj wt add <branch>` creates a fresh `.claude/settings.local.json` — user's docs explicitly say worktrees are siblings of `base/`, but settings don't hardlink/symlink to base.
8. **Agent definitions enumerate tool **classes** in frontmatter (`tools: [Bash, Read]`)**, but those are tool *types*, not per-pattern permissions. The Bash tool class being available doesn't mean a specific Bash command is permitted.

#### Fix layer

- CLAUDE.md text edit + `Bash(git -C *)` rule (with mirrored deny rules).
- Worktree-create hook to seed `settings.local.json` from `base/`.
- (Optional) sub-agent permission inheritance — out of harness scope but worth raising with Anthropic.

---

### Class F — Project-scope leakage and stale rules

#### Symptoms

- Committed `.claude/settings.json` files contain user-specific rules.
- Old skill names persisted in allow-lists that no longer exist.
- WebFetch domains pinned for one-off lookups.

#### Evidence

3 projects with committed `.claude/settings.json`: `devbox-setup`, `oi-observability-lib`, `mlops-be`. Snapshots at `data/settings-snapshots/`.

`mlops-be/.claude/settings.json` excerpt (committed, shared with team):

```jsonc
"Bash(ENV_NAME=local pytest:*)",
"Bash(ENV_NAME=local python -m pytest:*)",
"Bash(ENV_NAME=local uv run pytest:*)",
"Bash(ENV_NAME=local uv run --active pytest:*)",
"Bash(ENV_NAME=local uv run python -m pytest:*)",
// ...
"WebFetch(domain:auth.oicm.my-local)",
"WebFetch(domain:oicm.oicm.my-local)",
// ...
"Skill(implement)",   // stale name — now Skill(techne-implement)
```

#### Root causes (7)

1. **`mlops-be/.claude/settings.json` allows commands with embedded env-var prefixes** (`Bash(ENV_NAME=local uv run pytest:*)`). The team's workaround for the env-prefix problem. Works for `ENV_NAME=local` only — any other env value re-prompts. Lock-in.
2. **`oi-observability-lib/.claude/settings.json` and `devbox-setup/.claude/settings.json` both grant `Edit`, `Write`, `Read(**)` blanket** — fine for solo work, but committed to git, so they shape every team member's default policy. If a teammate has a stricter local policy, the project rule undercuts it.
3. **Stale `Skill(...)` references.** `Skill(plan)`, `Skill(implement)`, `Skill(review)`, `Skill(go-engineer)`, `Skill(go-style)`, `Skill(go-patterns)`, `Skill(full-cycle)` — most are OLD short-name form, not the current `techne-*` prefix. (See `data/session-excerpts/agent-acknowledgements.md:189` for the agent's own observation that bare names get shadowed by built-in skills.)
4. **`WebFetch(domain:auth.oicm.my-local)` etc. — local-only domains** persisted in committed rules: useless for anyone outside that user's environment.
5. **Each worktree's `settings.local.json` is born empty**, then accumulates. With ~10 worktrees per project × 4 projects ≈ 40 separate allow-lists drifting independently.
6. **No purge job.** Old worktree dirs (e.g. `MLOPS-7129_oicm_migrations…`) are still around with their old settings.local files even though the branch is long-merged. Removing the worktree leaves the file behind.
7. **`additionalDirectories` is per-worktree.** `oicm-grafana-dashboards/base/.claude/settings.local.json` lists `additionalDirectories: ["/Users/kabrosimov/Work/oiai-work-notes"]` — but only the `base/` worktree. Other worktrees re-prompt every time they need that dir.

#### Fix layer

- Tooling: cleanup script + lint rule for committed `.claude/settings.json` (detect user-specific patterns).
- Convention: never commit env-prefixed rules; never commit user-local domains.
- Tooling: a `proj wt rm` that also removes the worktree's `.claude/settings.local.json`.

---

### Class G — Sub-agent permission scope isolation

> **New class promoted from Class D.** Distinct mechanism: the harness treats sub-agents (`Task`/`Agent` tool invocations) as separate permission scopes that don't inherit from the parent session's allows.

#### Symptoms

- Sub-agent fails with "Permission to use ... has been denied" for an MCP tool that the parent session uses freely.
- Sub-agent reports "I cannot fetch the Jira issues" despite the user having authorised Atlassian MCP minutes earlier.

#### Evidence

`data/session-excerpts/user-complaints-verbatim.md:67-100` — verbatim sub-agent failure reports:

```
<result>The `mcp__atlassian__getJiraIssue` tool is blocked by user permissions. I cannot fetch the Jira issues, so I cannot produce the requested findings. The other Atlassian tools (search, remote links, etc.) will likely face the same denial since they were not pre-approved either.

I need explicit user permission to proceed. Specifically, I need approval to call:
- `mcp__atlassian__getJiraIssue` — to read OICM-8015, OICM-7662, MLOPS-3947 (description + comments)
- `mcp__atlassian__getJiraIssueRemoteIssueLinks` — to enumerate linked issues for each
- Possibly `mcp__atlassian__searchJiraIssuesUsingJql` — to find issuelinks via JQL
```

And in a follow-up retry:

```
<result>**Exploration blocked — permission denied on all Atlassian MCP calls.**

Despite the prompt asserting the `mcp__atlassian__*` tools were allowlisted, every call (`getAccessibleAtlassianResources`, `getJiraIssue` x3 for OICM-8015/OICM-7662/MLOPS-3947, `getJiraIssueRemoteIssueLinks` x3) was rejected by the harness with "Permission to use … has been denied". The MCP server is registered (tool schemas loaded fine via `ToolSearch`), but the policy layer refused every invocation. This is a permanent failure, not transient — retry would not help.
```

Agent acknowledgement (`data/session-excerpts/agent-acknowledgements.md:73`):

«Jira-агент уперся в permissions — sub-agent'у не разрешены `mcp__atlassian__*` вызовы (хотя в основной сессии всё подключено).»

#### Root causes (5)

1. **Sub-agents have their own permission scope.** Even with `mcp__*` (glob) in `~/.claude/settings.json`, the sub-agent's evaluator does not always inherit it. Mechanism is harness-internal; user-observable behaviour is denial.
2. **`/techne-*` agents declare `tools:` in frontmatter as tool *classes*, not specific MCP names.** So an agent definition with `tools: [Read, Write, mcp__atlassian]` may not match the harness's expected per-tool allow form.
3. **No telemetry on sub-agent permission denials.** The parent session sees a `<task-notification>` with `<status>completed</status>` and an embedded `<result>` describing denial — but the user has no way to "Always allow this for sub-agents" mid-flight.
4. **Each sub-agent's `Always allow` clicks go into the sub-agent's transient scope.** If the parent task spawns multiple agents in parallel, each accumulates separate scopes; none survives the task end.
5. **The user's debugging path is opaque.** When the parent session has `mcp__atlassian__*` working and the sub-agent fails, the user's first hypothesis is "MCP server is broken" — wasted debugging time.

#### Fix layer

Mostly harness UX (Anthropic side). Workaround within reach: ensure agent frontmatter `tools:` lists name MCP tools explicitly with their full names (`mcp__atlassian__getJiraIssue`, not `mcp__atlassian`).

---

## 5. Cross-cutting structural observations

These don't fit a single class but are worth surfacing.

1. **The `cd $abs && git ...` form ACTUALLY auto-allows now.** The user's original complaint pre-dates the `Bash(cd *)` rule. After that rule was added, this pattern is no longer the friction source. The user may remember the old pain and assume it persists. See Trace 1 in `data/bash-command-samples/normalization-trace.md` for proof.

2. **Friction has migrated, not disappeared.** The bulk now comes from:
   - missing `git -C *` rule (since CLAUDE.md tells agents to prefer this form);
   - missing minor git/go subcommands;
   - env-prefixed Python/Ansible commands;
   - multi-line shell loops (always prompt regardless);
   - sub-agent MCP scope drops.

3. **`grep` is 29.4 % of all bash calls (135 invocations).** The user has `Bash(grep *)` in the allow-list — these all auto-allow. But agents often pair grep with `$(...)` substitution (`grep ... $(go env GOMODCACHE)/...`) which complicates matching. Switching agents to the native `Grep` tool (which has a separate, fully-allowed permission class) would eliminate most of these.

4. **`| head` appears in 50.8 % of all commands.** Good agent behaviour for context budget. But it pushes 50 % of bash calls into the `piped`/`redirected` shape category.

5. **`cd` is the second-most-frequent base command.** 16.6 % of bash starts with `cd`. The shell-discipline rule says don't. Either the rule isn't reaching agents or they're ignoring it. Worth investigating WHICH agents emit `cd`-prefixed commands — sub-agents may have less context.

6. **The user has bundled tooling for this problem already** — `techne-fewer-permission-prompts` skill, `update-config` skill, `validate-config.py` script. But these are reactive (after-the-fact cleanup). The accumulation rate exceeds the cleanup rate.

7. **`/permissions` slash command exists in Claude Code** (mentioned in `<local-command-stdout>` in session logs). The user has never invoked it interactively in any of the 25 sessions sampled. Worth knowing it exists as an option.

8. **Project-committed `settings.json` files have grown user-specific.** `mlops-be/.claude/settings.json` has rules with `ENV_NAME=local` baked in, `auth.oicm.my-local` domains, and old skill names. These should arguably be in `settings.local.json` instead.

9. **The committed `settings.json` files use the colon-glob form** (`Bash(uv run pytest:*)`) while the user's global uses the space-glob form (`Bash(uv run *)`). Both work in current Claude Code, but it tells you the user has been hand-editing in both styles — minor source of cognitive overhead and a syntax-confusion landmine if Anthropic ever deprecates one form.

---

## 6. Pattern summary (one-page view)

| Class | Symptom user sees | Real cause | Fix layer |
|---|---|---|---|
| A | "I told it `git diff` was allowed but it asked for `git show`" | `Bash(git diff *)` doesn't cover `git show`, `git branch`, `git ls-remote`, `git merge-base` | global `settings.json` |
| A | `diff /tmp/x /tmp/y` blocked | `pre-tmpdir-guard` hook hard-blocks `/tmp/` substring | hook script |
| A | `go env GOMODCACHE` prompts | Allow-list lacks `Bash(go env *)`, `go list`, `go doc` | global `settings.json` |
| A | `GOSUMDB=off go mod tidy` prompts | env-prefix breaks naive matching; auto-approve hook strips it but SAFE list too narrow | hook script |
| B | Allow-list grows endlessly | "Always allow" persists literal command; no generalisation | harness UX + post-hoc cleanup tool |
| B | Worktrees re-ask the same things | `.claude/settings.local.json` is per-worktree, not inherited from `base/` | tooling: `proj wt add` should seed |
| B | `node-health-monitor/settings.local.json` has `Bash(fi)`, `Bash(done)` | Multi-line shell tokenised → garbage rules | behavioural: don't write multi-line shell |
| C | Edit succeeds but reports failure | PostToolUse lint/typecheck gates fail; surfaced as tool error | hook script |
| C | `make test && make lint` doesn't auto-allow | `permission-auto-approve` rejects on residual shell metachars after normalisation | hook script |
| D | git operations always prompt | `excludedCommands` removes git from sandbox auto-allow | global `settings.json` |
| D | Sandbox writable ≠ tmp guard | Two layers disagree about `/tmp/claude/` | unify guard + sandbox rules |
| E | Complex `cd "$VAR" && a && b` re-asks (LEGACY) | Pre-`Bash(cd *)` complaint; ACTUALLY auto-allows now | none — informational |
| E | `git -C <path>` prompts | New rule has no `Bash(git -C *)` | global `settings.json` + mirrored denies |
| F | Old skill rules persist | No cleanup job; rules survive renames | tooling |
| G | Sub-agent denied MCP that parent has | Scope isolation; agent frontmatter mismatches | agent frontmatter + harness |

---

## 7. Suggested next-step directions

> These are **options to weigh, not decisions**. For your review.

### Quick wins (1-2 hours each, low risk)

1. **Extend global `~/.claude/settings.json` allow-list.** Add: `Bash(go env *)`, `Bash(go list *)`, `Bash(go doc *)`, `Bash(go tool *)`, `Bash(go version *)`, `Bash(git show *)` (currently only `show`), `Bash(git merge-base *)`, `Bash(git rev-list *)`, `Bash(git ls-remote *)`, `Bash(git for-each-ref *)`, `Bash(git show-ref *)`, `Bash(git reflog *)`, `Bash(git cat-file *)`, `Bash(diff *)` (already present, verify), `Bash(comm *)`, `Bash(column *)`, `Bash(paste *)`, `Bash(hexdump *)`, `Bash(md5 *)`, `Bash(shasum *)`, `Bash(tee *)`, `Bash(nproc)`, `Bash(uptime)`, `Bash(tar -t *)`, `Bash(unzip -l *)`, `Bash(ps *)`. ~25 new rules. Coverage: ~30-40 % of remaining friction commands.

2. **Add `Bash(git -C *)` allow rule + mirrored denies.** New allow: `Bash(git -C *)`. New denies (paired): `Bash(git -C * rebase *)`, `Bash(git -C * reset *)`, `Bash(git -C * commit --amend *)`, `Bash(git -C * rm *)`, `Bash(git -C * mv *)`, `Bash(git -C * clean *)`, `Bash(git -C * checkout -- *)`, `Bash(git -C * push --force *)`. This makes the CLAUDE.md shell-discipline rule no longer self-defeating.

3. **Rewrite `pre-tmpdir-guard`.** Whitelist `$TMPDIR`-resolved paths and `/tmp/claude/...` before checking `/tmp/` substring. Concretely:
   - Pass through any command containing `/tmp/claude/` or `/tmp/claude-*/` (sandbox-writable).
   - Pass through any command whose only `/tmp/` reference is a sandbox-writable subpath.
   - Continue to block other `/tmp/` and `/var/tmp/` writes.

4. **Prune `sandbox.excludedCommands`.** Remove `git` (at least) so `git diff`, `git show`, `git log` can ride the `autoAllowBashIfSandboxed` shortcut. Keep `docker`, `docker-compose`, `podman` excluded (they need privileged operations the sandbox blocks).

### Medium wins (half-day each)

5. **Extend `permission-auto-approve`.**
   - Strip multiple env-prefixes including ones with `=` in the value (`KEY="https://..."`).
   - Strip common pipe suffixes (`| head`, `| tail`, `| wc -l`).
   - Strip redirect suffixes (`2>&1`, `> /dev/null`, `> file`).
   - Auto-approve segments-of-chains where every segment is in SAFE list (handle the `&&`/`|` rejection at end of script).
   - Extend SAFE list to: `ansible-playbook *`, `ansible-lint *`, `ansible *`, `kubectl *`, `helm *`, `docker compose *`, `docker inspect *`, `docker logs *`, `docker ps *`, `docker images *`, `go env *`, `go list *`, `go doc *`, `git show *`, `git branch *`, `git blame *`, `git ls-remote *`, `git for-each-ref *`.

6. **Write a one-shot cleanup script** that walks `~/Work/*/.claude/settings.local.json`:
   - Removes shell-keyword fragments (`Bash(fi)`, `Bash(done)`, `Bash(then echo ...)`, `Bash(do)`, `Bash(EOF)`, `Bash(else echo ...)`, etc.).
   - Removes bare file-path "rules" (entries matching `*/*.{go,py,ts,js,yml,yaml,json}` not preceded by a command).
   - Removes literal commands ≥120 chars (single-use).
   - Deduplicates redundant rules.
   - Removes stale skill names (`Skill(plan)`, `Skill(implement)` → `Skill(techne-plan)`, `Skill(techne-implement)` or just removes if unused).
   - Optional: schedule weekly via the `loop` skill.

7. **Patch the worktree-create hook** (`~/.claude/bin/worktree-create`) to copy `base/.claude/settings.local.json` to the new worktree if `base/` exists.

8. **Add a CLAUDE.md rule:** *"Never use multi-line `if/then/fi`, `for/do/done`, or heredocs as a single Bash tool call. Either split into multiple sequential Bash tool calls, or write a temporary script file (Write) then invoke it via Bash."* The rule should be in the "Cross-Cutting Rules" section so it's always loaded.

### Bigger investments (1-2 days each)

9. **Diagnostic instrumentation.** Add a PostToolUse Bash hook that logs `(timestamp, command, exit_code, hook_blocks, was_prompted)` to a CSV under `~/.claude/telemetry/permission-events.csv`. After 1 week of data, you can measure friction reduction empirically for each fix.

10. **A "settings.local.json policy" doc** in `roles/devbox/files/dot_claude/docs/` describing:
    - what belongs in committed `.claude/settings.json` vs local
    - rule patterns (colon-glob vs space-glob) — pick one
    - never commit env-prefixed rules, never commit user-local domains
    - max recommended size (50? 100?)
    - cleanup cadence

11. **Sub-agent permission inheritance** — out of immediate scope but worth raising with Anthropic. Document the current behaviour (Class G) and the desired behaviour ("sub-agent inherits parent's allow set unless explicitly stricter").

12. **Investigate whether `cd` is being generated by specific agents.** If sub-agents emit `cd` 60 % more than the main session, that's targetable. Per-agent rule reminder in agent frontmatter.

---

## 8. What was deliberately NOT touched

- No edits to any settings file, hook script, or agent definition. This is a read-only audit.
- No edits to CLAUDE.md / USER_AUTHORITY_PROTOCOL.md beyond the existing shell-discipline rule (which was added by the user in an earlier session, see `data/session-excerpts/agent-acknowledgements.md:119`).
- No edits to `roles/devbox/files/dot_claude/` ansible-managed files. The audit lives in `future_projects/comprehensive_analysis/`, which is documentation, not a deployable artefact.
- The hook scripts under `~/.claude/bin/` look well-engineered and have unit tests (`test_*.py` siblings). The friction here is *configuration*, not *correctness*.
- The `bin/permission-auto-approve` script is a focused 100-line shell script — easy to extend safely once you've decided which extensions are wanted.

---

## 9. Appendix: how to navigate the `data/` directory

```
comprehensive_analysis/
├── README.md                      ← this file
├── data/
│   ├── settings-snapshots/        ← snapshots of global + 14 representative project settings
│   │   ├── global-settings.json   ← ~/.claude/settings.json (396 lines)
│   │   ├── global-hooks.json      ← ~/.claude/hooks.json (234 lines)
│   │   ├── devbox-setup_.claude_settings.json
│   │   ├── devbox-setup_.claude_settings.local.json
│   │   ├── mlops-be_.claude_settings.json           ← env-prefix workaround example
│   │   ├── mlops-be_OICM-7708_debug_pvc_creation_.claude_settings.local.json   ← 14 literal pytest cmds
│   │   ├── node-health-monitor_.claude_settings.local.json                     ← 132 lines of garbage rules
│   │   ├── oicm-grafana-dashboards_base_.claude_settings.local.json
│   │   ├── oi-platform-installer_base_.claude_settings.local.json
│   │   └── ...
│   ├── hooks-snapshots/            ← 5 PreToolUse Bash-relevant hooks
│   │   ├── permission-auto-approve.sh
│   │   ├── pre-tmpdir-guard.sh
│   │   ├── pre-bash-toolchain-guard.sh
│   │   ├── pre-bash-boundary-wrap.sh
│   │   └── pre_bash_safety_gate.py
│   ├── session-excerpts/
│   │   ├── user-complaints-verbatim.md           ← 18 verbatim user complaints
│   │   ├── agent-acknowledgements.md             ← 12 assistant root-cause diagnoses
│   │   └── permission-related-records.jsonl      ← 200 raw JSONL records (capped from 554)
│   └── bash-command-samples/
│       ├── all-commands-classified.csv           ← 459 commands × {session,timestamp,shape,command}
│       ├── statistics.md                         ← summary tables
│       ├── top-friction-commands.md              ← 25 highest-friction commands with explanations
│       └── normalization-trace.md                ← 10 commands traced through full pipeline
```

### Quick recipes

- **Look up a user complaint by date:** open `data/session-excerpts/user-complaints-verbatim.md`, search for `2026-06-`.
- **See what the agent itself thinks the root cause is:** open `data/session-excerpts/agent-acknowledgements.md`.
- **Reproduce a friction case:** pick a command from `data/bash-command-samples/top-friction-commands.md`, follow the trace pattern in `data/bash-command-samples/normalization-trace.md`.
- **Validate a proposed fix:** before adding a rule, grep `data/bash-command-samples/all-commands-classified.csv` for commands that would now match.

### One-line summary of the data corpus

> 459 bash commands × 18 verbatim user complaints × 12 verbatim agent acknowledgements × 200 permission-related JSONL records × 43 per-project `settings.local.json` × 5 hook scripts × 1 global `settings.json` = enough evidence to triage the friction once and for all.

---

**[Awaiting your decision]** — Reply with which directions you want to pursue, or ask for deeper investigation on any specific class.
