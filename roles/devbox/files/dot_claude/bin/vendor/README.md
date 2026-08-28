# Vendored upstream sources

Third-party code copied verbatim into this repository. Files here are **not** ours to
restyle: they are excluded from Ruff and Pyrefly (see `extend-exclude` / `project-excludes`
in the root `pyproject.toml`) so that upstream diffs stay reviewable byte-for-byte.

## `langfuse_hook.py`

| | |
|---|---|
| Upstream | <https://github.com/langfuse/claude-observability-plugin> |
| Commit | `d06829810cce8a8a4f486e0afebd155e95ab9517` |
| Plugin version | `1.0.0` |
| Licence | MIT |
| SHA-256 | `fcde9003e315976f454300ccf73b5c91d71a16a1797dfc06c512aae1168ed743` |
| Lines | 3086 |

### Why it is vendored rather than installed as a plugin

Upstream ships this hook with PEP 723 inline metadata (`langfuse>=4.0,<5`) and invokes it
as `uv run --script`. That resolves dependencies **at hook-invocation time** into uv's
ephemeral environment cache. With `UV_CACHE_DIR=/tmp/claude/uv-cache` (set in
`settings.json` so that uv stays writable inside the Bash sandbox), the resulting
environment lives under `/tmp` — where macOS `/usr/libexec/tmp_cleaner`, run daily at
00:00 by `com.apple.tmp_cleaner`, deletes any regular file whose atime, mtime and ctime
are all older than three days.

The deletion is per-file, not per-package. Files Python actually opens keep a fresh atime
and survive; files that are only `stat()`ed — a package's `.py` source once a valid `.pyc`
exists, and `dist-info/METADATA` — rot and get removed. That leaves an environment uv still
considers installed, so it does not rebuild it; it opens the missing `METADATA`, fails with
`ENOENT`, and exits 2. Claude Code reports this as `Stop hook error: Hook script appears to
be missing`.

Vendoring moves the dependency into `../pyproject.toml` + `../uv.lock`, pinned and
materialised by Ansible into `~/.claude/bin/.venv` (`install_configs.yml`, Block 1b). The
hook is then invoked exactly like every other hook in `hooks.json` — through the
pre-materialised interpreter, with no resolution at invocation time.

Upstream's own `pyproject.toml` and `uv.lock` are not usable for this: they declare
`dependencies = []` with `package = false`, and the lock covers only the `dev` group for
upstream's pytest suite. The hook's real dependencies exist solely in the PEP 723 block.

### Configuration

The hook resolves credentials via `_core_opt()`, which prefers plain environment variables
over the plugin wizard channel, in this order:

1. `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL`
2. `CC_`-prefixed spellings of the same
3. `CLAUDE_PLUGIN_OPTION_*` (unavailable once the plugin is removed — unused here)

`settings.json` sets the `CC_`-prefixed spellings, so removing the plugin changes nothing
about how the hook is configured.

### Updating

1. Fetch the new upstream revision and diff it against this copy.
2. Replace the file, then update the commit, SHA-256 and line count in the table above.
3. Re-check the PEP 723 block for dependency changes; mirror them into `../pyproject.toml`
   and regenerate the lock with `uv lock --project roles/devbox/files/dot_claude/bin`.
4. Run `make validate-claude` and `make test-claude-hooks`.
