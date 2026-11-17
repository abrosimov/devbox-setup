# Vendored upstream sources

Third-party code built from a pinned upstream commit and committed here. Files under
`langfuse-codex/` are build output and are never edited by hand.

## `langfuse-codex/index.mjs`

| | |
|---|---|
| Upstream | <https://github.com/langfuse/codex-observability-plugin> (`plugins/tracing`) |
| Commit | `e1d02be28e6bacbfe350a1bc1ccf861e54edee17` (2026-10-28) |
| Plugin version | `0.4.3` |
| Licence | MIT (`langfuse-codex/LICENSE`, copied from the upstream root) |
| Upstream Git tree SHA-1 | `dc624bae569783627507f292490e079820029938` |
| Build toolchain | Node 22, pnpm 9.5.0 |
| Output Git blob SHA-1 | `395b46b039f93463a4771897bc44715ddea6aa03` (upstream plus the patches below) |
| Artifact pin | `langfuse-codex-upstream.lock.json` (authoritative when this table disagrees) |

### Why it is vendored rather than installed as a plugin

Upstream stopped committing its build output (`plugins/tracing/dist/` has been
gitignored since `1db5c0f`), so a marketplace install at a recent commit has no hook
to run. The plugin's own hook also starts a bare `node`, which resolves through `PATH`
at invocation time and fails the `HOOK_HERMETICITY` check in
`dot_claude/bin/validate_config.py`. Vendoring the bundle lets the hook run like every
other Codex hook here: declared in `../../config.toml.j2`, deployed by the
"Sync Codex bin directory" task, and run by a pinned interpreter.

The bundle is self-contained: tsdown inlines every runtime dependency (Langfuse SDK,
OpenTelemetry, zod) and leaves only Node built-ins external, so nothing is installed on
the machine that runs it.

### Configuration

The hook reads `~/.codex/langfuse.json`, rendered from `../../langfuse.json.j2`, with
loopback-only sentinel credentials. Its keys and base URL come only from that file and
the `LANGFUSE_CODEX_*` variables, so an inherited `LANGFUSE_*` environment or a
repository's `.codex/langfuse.json` cannot redirect traces away from the loopback edge.

### Registration

`../../config.toml.j2` registers the same command on four events, with upstream's
status message:

```text
/opt/homebrew/opt/node@22/bin/node ~/.codex/bin/vendor/langfuse-codex/index.mjs
```

| Event | Timeout | Why |
| --- | --- | --- |
| `Stop` | 30 s, upstream's | the event upstream registers |
| `Interrupt` | 3 s | Codex fires no `Stop` for a turn that ends in `turn_aborted` |
| `SessionEnd` | 3 s | uploads a turn that no `Stop` or `Interrupt` finalised |
| `SubagentStop` | 30 s | uploads a subagent turn that ran after its spawning turn was exported |

Codex clamps `Interrupt` and `SessionEnd` hooks to 3 seconds and warns on load when a
longer timeout is declared, so the declared value is the one that applies.

`/opt/homebrew/opt/node@22` is the keg of the `node@22` Homebrew formula in
`defaults/main/packages.yml`. It is keg-only, so this path is stable whatever `node` on
`PATH` resolves to. Codex records hook trust by command hash, so any change to this
command needs trust granted again; `scripts/codex-hook-trust.py` does that at the end
of `install_codex_configs.yml`.

### Reproducible upstream source and patches

`langfuse-codex-upstream.lock.json` records the upstream commit, the Git tree SHA-1 of
that commit, the Node major and pnpm version the build runs under, the path of the build
output inside the upstream tree, its expected Git blob SHA-1, and an ordered list of
`git apply` patches under `patches/`. Ordinary provisioning stays offline. Applied in
this order:

| Patch | Change |
| --- | --- |
| `0001-export-interrupted-and-ended-turns.patch` | on `Interrupt`, export the hook's turn as final and aborted before `turn_aborted` reaches the rollout; on `SessionEnd`, export every turn with an id not yet in the sidecar |
| `0002-one-hook-run-per-rollout.patch` | hold `<rollout>.langfuse.lock` from parse to the last sidecar mark; wait at most 10 s on `Stop` (and, from `0003`, `SubagentStop`) and 1 s on other events, then exit without exporting; take over a lock older than 60 s |
| `0003-export-subagent-turns-after-the-spawning-turn.patch` | on `SubagentStop`, export the child rollout's unexported final turns under its spawning turn's `spawn_agent` span, with the ids that turn's export draws; child turns nested with their spawning turn are recorded in the child's sidecar under the child's lock, so neither path exports a turn twice |
| `0004-trace-tool-items-nested-in-code-mode.patch` | read the shell, MCP, patch and extension calls that Codex 0.162 and later report only as `item_completed` items: an item completed while a code-mode `exec` call is open becomes a child tool observation of that call, named `exec_command`, `<server>.<tool>`, `apply_patch` or the extension kind, with the item's own start and end; a `failed` or `declined` item is `ERROR` with the exit code or MCP error as its status message, without marking `exec`; an item sharing a model-visible call's id enriches that call; any other item attaches to the turn root. Child ids are drawn after every step, so existing observation ids are unchanged |
| `0005-record-usage-of-every-model-response.patch` | put each model response's token usage on exactly one generation: from its `token_usage_record` (one per response, compaction calls included) once the rollout writes them, otherwise from each `token_count` whose cumulative total moved, so a re-emitted `token_count` counts once; a response whose output the rollout does not show (encrypted reasoning only, no items, a compaction) becomes a generation carrying only its usage; every generation records `codex.response_id`. Usage-only generations are drawn after every other observation of their turn, and the `SubagentStop` replay skips them, so existing observation ids are unchanged |
| `0006-answer-each-turn-with-its-final-answer.patch` | set a turn's output to its final answer: the `last_agent_message` of `task_complete`, else the last `AgentMessage` item with `phase` `final_answer`, else the earlier choice of the last `agent_message` event or the last step's text. Codex no longer writes `agent_message` events, and the final step's text carries the `<oai-mem-citation>` block appended to the answer (and, when one response holds both, the commentary before it). An interrupted turn takes its `final_answer` item when it has one. No span is added, so observation ids are unchanged |
| `0007-attribute-subagent-turns-to-their-agent.patch` | give every subagent turn root, nested or attached on `SubagentStop`, the child's `codex.agent_role`, `codex.agent_path`, `codex.agent_nickname`, `codex.depth` and `codex.parent_thread_id` from its `session_meta` (top-level fields, else `source.subagent.thread_spawn`); tag a top-level turn's trace `subagent:<role>` once per distinct role among the subagents it announced, read from each child's `session_meta`, with the same tags on the attributes a later `SubagentStop` export propagates; give a model-visible call that a `SubAgentActivity` item of kind `interacted` shares its id with (`send_message`, `followup_task`) `codex.target_thread_id` and `codex.target_agent_path`. No span is added, so observation ids are unchanged |
| `0008-describe-each-turn-with-its-place-and-timing.patch` | give every turn root, main or subagent, nested or attached on `SubagentStop`, the keys the Claude hook records: `codex.turn_number` (1-based among the thread's own turns, so a forked child's replayed ancestor turns are not counted), `codex.cwd` (the turn's `turn_context`, else `session_meta`), `codex.project` (the last component of that cwd, as the Claude hook derives it), `codex.git_branch` and `codex.git_commit` (`session_meta.git`), `codex.transcript_path` (the rollout's file name, the Claude hook's short form) and `codex.duration_ms` (`task_complete` or `turn_aborted`). When `task_complete` reports `time_to_first_token_ms`, which Codex measures from the turn's start, the turn's first generation starts at the turn's start and records `completionStartTime` at start plus that time. No span is added, so observation ids are unchanged |
| `0009-take-credentials-only-from-the-global-config.patch` | take `public_key`, `secret_key` and `base_url` only from `~/.codex/langfuse.json` and `LANGFUSE_CODEX_PUBLIC_KEY`, `LANGFUSE_CODEX_SECRET_KEY` and `LANGFUSE_CODEX_BASE_URL`: the standard `LANGFUSE_*` variables no longer set them, and a project's `<cwd>/.codex/langfuse.json` can still set every other option but not these three. Upstream let either one override the global file, so an inherited environment or an opened repository could send traces past the loopback edge. Observation ids are unchanged |

The input hash is the Git tree SHA-1 of the whole upstream tree, computed from the
fetched files exactly as `git write-tree` would. It equals `<commit>^{tree}` upstream,
so it can be checked independently:

```sh
gh api repos/langfuse/codex-observability-plugin/git/commits/<commit> --jq .tree.sha
```

Run `python3 scripts/langfuse-codex-plugin-source.py verify` to check the committed
bundle without network access. `refresh` rebuilds it, and needs `node` (the pinned
major) and `pnpm` (the pinned version) on `PATH`. It:

1. downloads the upstream tarball at the pinned commit and checks its tree SHA-1;
2. applies every listed patch with strict `git apply --check --whitespace=error`;
3. runs `pnpm install --frozen-lockfile`, `pnpm run build` and `pnpm exec vitest run`
   (the upstream test suite) in a temporary directory;
4. checks the built bundle against the locked blob SHA-1 and writes `index.mjs` and
   `LICENSE`.

CI runs `refresh` in the `validate` job and fails on any difference from the committed
files. A changed upstream or patch requires an explicit lock update and code review.

### Updating

1. Find the new upstream release's full commit SHA and read the upstream diff from the
   pinned commit, including `plugins/tracing/hooks/hooks.json` (events, timeout) and
   `plugins/tracing/src/config.ts` (configuration keys).
2. In `langfuse-codex-upstream.lock.json`, set `version` and `commit`. If upstream
   changed `packageManager` or its Node target, update `pnpm_version` or `node_major`.
3. Run `python3 scripts/langfuse-codex-plugin-source.py refresh --print-hashes`. It
   builds at that commit with every listed patch and prints `upstream_tree_sha1` and
   `output_git_blob_sha1` without enforcing either or writing anything. A patch that no
   longer applies stops it here: rebase that patch onto the new upstream before going on.
4. Copy both printed values into the lock, then run `refresh`, which enforces them and
   rewrites `langfuse-codex/index.mjs` and `langfuse-codex/LICENSE`, and `verify`.
5. Mirror any upstream change to the hook registration into `../../config.toml.j2`, and
   any configuration-key change into `../../langfuse.json.j2`. A change of Node major
   also changes the `node@<major>` formula in `defaults/main/packages.yml` and the hook
   command.
6. For a behaviour change, add a patch against the upstream tree, append it to
   `patches` in the lock, and repeat steps 3 and 4.
7. Update the table above, then run `make validate-claude`, `make test-scripts` and
   `make test-deploy`.
