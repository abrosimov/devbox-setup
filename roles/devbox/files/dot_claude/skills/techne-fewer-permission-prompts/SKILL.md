---
name: techne-fewer-permission-prompts
description: >
  Reduce Claude Code permission prompts by mining recent transcripts for read-only
  Bash and MCP tool calls, then merging a prioritised allowlist into the project
  `.claude/settings.json`. Use this fork in place of the bundled
  `fewer-permission-prompts` skill — it offloads JSONL parsing and command-head
  extraction to a deterministic Python script (sudo/env-prefix/wrapper-leader
  stripping, quote-aware pipe splitting), keeping classification and merge
  judgement in the prompt. Also use when the user mentions allowlists, permission
  prompts, settings.json permissions, or wants to cut interruption from approval
  dialogs.
---

# Fewer Permission Prompts (techne fork)

Look through my transcripts' MCP and bash tool calls, and based on those, make a prioritised list of patterns I should add to my permission allowlist to reduce permission prompts. Focus on read-only commands.

The format for permissions is: `Bash(foo*)`, `Bash(foo)`, `Bash(foo bar *)`, `mcp__slack__slack_read_thread`, etc.

## Steps

1. **Run the scanner.** Execute `${CLAUDE_SKILL_DIR}/scripts/scan_transcripts.py` with no flags. It merges two sources:

   - **Transcripts** — the 50 most recently-modified JSONL files under `~/.claude/projects/*/*.jsonl` (all Bash and MCP tool calls)
   - **Telemetry** — every shard under `~/.claude/state/missed_approvals/YYYY/MM/DD/HH.jsonl` written by the `bash_decision_gate` hook. This is the **high-signal** source: each record is a command that did NOT auto-approve and therefore prompted, i.e. a candidate for the allowlist.

   The scanner strips `sudo`/`timeout`/env-prefix/wrapper leaders, splits on quote-aware pipes/`&&`/`||`/`;`, and prints JSON on stdout:

   ```json
   {
     "scanned_files": 50,
     "scanned_telemetry": 14,
     "bash": [
       {"cmd": "git", "sub": "status", "count": 42, "sample": "git status --short"}
     ],
     "mcp": [
       {"name": "mcp__atlassian__getJiraIssue", "count": 7}
     ]
   }
   ```

   `bash` is sorted by count descending (top 60); `mcp` likewise (top 30). Counts are merged across both sources. Use this JSON as your input for steps 2–7. Pass `--pretty` only for human-readable debugging at the CLI — the skill itself consumes JSON. Pass `--no-telemetry` to scan transcripts only (useful when telemetry shards are stale).

2. **Filter to read-only.** Keep only commands that don't mutate state. Examples of read-only: `ls`, `cat`, `pwd`, `git status`, `git log`, `git diff`, `git show`, `git branch`, `rg`, `grep`, `find`, `head`, `tail`, `wc`, `file`, `which`, `echo`, `date`, `gh pr view`, `gh pr list`, `gh pr diff`, `gh issue view`, `gh issue list`, `gh run list`, `gh run view`, `gh api` (GET), `bun run typecheck`, `bun run lint`, `bun run test` (for tests that don't mutate), `docker ps`, `docker logs`, `kubectl get`, `kubectl describe`, `ps`, `top`, `df`, `du`, `env`, `printenv`, any MCP tool with `read`/`get`/`list`/`search`/`view` in its name.

   Drop anything that writes, deletes, renames, pushes, merges, installs, or runs a build/test that has side effects. When in doubt, leave it out.

   **Never allowlist a pattern that grants arbitrary code execution.** A wildcard rule for any of these (e.g. `Bash(python3:*)`) is equivalent to allowing arbitrary code execution. This list is not exhaustive — apply the same rule to anything in the same category:
   - Interpreters: `python`/`python3`, `node`, `bun`, `deno`, `ruby`, `perl`, `php`, `lua`, etc.
   - Shells: `bash`, `sh`, `zsh`, `fish`, `eval`, `exec`, `ssh`, etc.
   - Package runners: `npx`, `bunx`, `uvx`, `uv run`, etc.
   - Task-runner wildcards: `npm run *`, `yarn run *`, `pnpm run *`, `bun run *`, `make *`, `just *`, `cargo run *`, `go run *`, etc. — an exact `Bash(bun run typecheck)` is fine, `Bash(bun run *)` is not.
   - `gh api *`, `docker run`/`exec`, `kubectl exec`, `sudo`, and similar.

3. **Drop commands Claude Code already auto-allows.** These don't need an allowlist entry — they never prompt. If you see any of these in the transcripts, skip them; don't suggest them to the user.

   - **Always auto-allowed (any args):** `cal`, `uptime`, `cat`, `head`, `tail`, `wc`, `stat`, `strings`, `hexdump`, `od`, `nl`, `id`, `uname`, `free`, `df`, `du`, `locale`, `groups`, `nproc`, `basename`, `dirname`, `realpath`, `cut`, `paste`, `tr`, `column`, `tac`, `rev`, `fold`, `expand`, `unexpand`, `fmt`, `comm`, `cmp`, `numfmt`, `readlink`, `diff`, `true`, `false`, `sleep`, `which`, `type`, `expr`, `test`, `getconf`, `seq`, `tsort`, `pr`, `echo`, `printf`, `ls`, `cd`, `find`.
   - **Auto-allowed with zero args only:** `pwd`, `whoami`, `alias`.
   - **Auto-allowed exact forms:** `claude -h`, `claude --help`, `node -v`, `node --version`, `python --version`, `python3 --version`, `ip addr`.
   - **Auto-allowed with safe flags only (validated):** `xargs`, `file`, `sed` (read-only expressions), `sort`, `man`, `help`, `netstat`, `ps`, `base64`, `grep`, `egrep`, `fgrep`, `sha256sum`, `sha1sum`, `md5sum`, `tree`, `date`, `hostname`, `info`, `lsof`, `pgrep`, `tput`, `ss`, `fd`, `fdfind`, `aki`, `rg`, `jq`, `uniq`, `history`, `arch`, `ifconfig`, `pyright`.
   - **All git read-only subcommands:** `git status`, `git log`, `git diff`, `git show`, `git blame`, `git branch`, `git tag`, `git remote`, `git ls-files`, `git ls-remote`, `git config --get`, `git rev-parse`, `git describe`, `git stash list`, `git reflog`, `git shortlog`, `git cat-file`, `git for-each-ref`, `git worktree list`, etc.
   - **All gh read-only subcommands:** `gh pr view`, `gh pr list`, `gh pr diff`, `gh pr checks`, `gh pr status`, `gh issue view`, `gh issue list`, `gh issue status`, `gh run view`, `gh run list`, `gh workflow list`, `gh workflow view`, `gh repo view`, `gh release view`, `gh release list`, `gh api` (GET), `gh auth status`, etc.
   - **Docker read-only subcommands:** `docker ps`, `docker images`, `docker logs`, `docker inspect`.

4. **Pick the pattern form.** Use the narrowest pattern that still covers the observed usage:
   - Many variants → `Bash(git log *)` (note space before `*`).
   - Single exact invocation common → `Bash(foo)` no wildcard.
   - MCP: full tool name verbatim.
   - Never widen to arbitrary code execution.

5. **Prioritise.** Rank by count descending. Drop count < ~3. Cap top ~20.

6. **Present prioritised list** as a markdown table: rank, pattern, count, one-line notes.

7. **Merge into `.claude/settings.json`** in the current project. Preserve existing keys; de-duplicate; don't reorder.

8. **Report back.** What was added, what was already there, what was skipped and why.

Do not add anything to `permissions.deny` or `permissions.ask`. Do not touch any other settings field.
