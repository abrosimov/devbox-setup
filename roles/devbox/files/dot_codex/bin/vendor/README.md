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
| Output Git blob SHA-1 | `5d7209b1db3763102aeb11ac88a13c55961732f6` (upstream plus the patches below) |
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
loopback-only sentinel credentials.

### Registration

`../../config.toml.j2` registers the same command on three events, with upstream's
status message:

```text
/opt/homebrew/opt/node@22/bin/node ~/.codex/bin/vendor/langfuse-codex/index.mjs
```

| Event | Timeout | Why |
| --- | --- | --- |
| `Stop` | 30 s, upstream's | the event upstream registers |
| `Interrupt` | 3 s | Codex fires no `Stop` for a turn that ends in `turn_aborted` |
| `SessionEnd` | 3 s | uploads a turn that no `Stop` or `Interrupt` finalised |

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
| `0002-one-hook-run-per-rollout.patch` | hold `<rollout>.langfuse.lock` from parse to the last sidecar mark; wait at most 10 s on `Stop` and 1 s on other events, then exit without exporting; take over a lock older than 60 s |

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
