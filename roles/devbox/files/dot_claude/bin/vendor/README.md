# Vendored upstream sources

Third-party code copied verbatim into this repository. Files here are **not** ours to
restyle: they are excluded from Ruff and Pyrefly (see `extend-exclude` / `project-excludes`
in the root `pyproject.toml`) so that upstream diffs stay reviewable byte-for-byte.

## `langfuse_hook.py`

| | |
|---|---|
| Upstream | <https://github.com/langfuse/claude-observability-plugin> |
| Commit | `b5b7cc364996467e856dc17575b5674f4799ad87` (2026-10-06) |
| Plugin version | `1.2.1` |
| Licence | MIT |
| SHA-256 | Git blob SHA-1 `cdd8f64f0b8e437a73442de3fb1c4e8c8a64f798` |
| Artifact pin | `langfuse-upstream.lock.json` |

### Why it is vendored rather than installed as a plugin

Upstream ships this hook with PEP 723 inline metadata (`langfuse>=4.7,<5`) and invokes it
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
hook is then invoked exactly like every other hook in the `hooks` block of
`settings.json` — through the pre-materialised interpreter, with no resolution at
invocation time.

Upstream's own `pyproject.toml` and `uv.lock` are not usable for this: they declare
`dependencies = []` with `package = false`, and the lock covers only the `dev` group for
upstream's pytest suite. The hook's real dependencies exist solely in the PEP 723 block.

### Configuration

The hook resolves credentials via `_core_opt()`, which prefers plain environment variables
over the plugin wizard channel, in this order:

1. `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL`
2. `CC_`-prefixed spellings of the same
3. `CLAUDE_PLUGIN_OPTION_*` (unavailable once the plugin is removed — unused here)

`settings.json.j2` sets the `CC_`-prefixed spellings, so removing the plugin changes
nothing about how the hook is configured. The personal profile also puts the operator's
real `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` into Claude's `env`
for the `langfuse` skill, and the SDK prefers `LANGFUSE_BASE_URL` over the host the hook
passes. The hook is therefore launched through `../langfuse_trace_hook.py`, which removes
those four names before running this file unmodified, so traces still go to the
`CC_LANGFUSE_*` loopback edge. `LANGFUSE_USER_ID` is the exception: it is
deployed unprefixed so that the shell rc (`devbox_shell.env`) and `settings.json.j2` can
carry one per-profile identity for every producer writing into the Langfuse project.

### Registration

`settings.json.j2` registers the hook (through `../langfuse_trace_hook.py`) on `Stop` and `SessionEnd` (as upstream does) and, as a
local addition, on `SessionStart` — a catch-up pass for sessions whose `Stop`/`SessionEnd`
never fired. The `SessionEnd` registration carries `"timeout": 60` because `SessionEnd`
hooks otherwise share a 1.5-second budget and the hook is killed mid-flush.

### Reproducible upstream source and patches

The committed `langfuse_hook.py` is the deployment artifact. Its source commit,
Git blob checksum, expected generated checksum and ordered patch list are recorded
in `langfuse-upstream.lock.json`. Ordinary provisioning stays offline.

Run `python3 scripts/langfuse-hook-source.py verify` to check the committed
artifact without network access. Run `python3 scripts/langfuse-hook-source.py
refresh` only when intentionally rebuilding it from the pinned upstream commit.
Refresh verifies the upstream blob, applies every listed patch with strict
`git apply --check --whitespace=error`, and checks the generated checksum.
A changed upstream or patch requires an explicit lock update and code review.
No network request is made from a Claude hook or its provisioning process.

The patch list makes delivery recoverable (design:
`docs/design/langfuse-durable-handoff.md`; operations:
`docs/runbooks/langfuse-replay.md`). Applied in this order:

| Patch | Change |
| --- | --- |
| `0001-durable-checkpoint.patch` | fsync the checkpoint file and its directory, and report a failed save |
| `0002-flush-before-checkpoint.patch` | advance the checkpoint only after the SDK flush completed |
| `0003-visible-delivery-errors.patch` | a lock timeout or delivery failure exits 1 instead of looking like success |
| `0004-propagate-emission-failures.patch` | a failed turn emission fails the firing instead of being skipped |
| `0005-replay-snapshot-identity.patch` | replay from a transcript snapshot keeps the original session's checkpoint key |
| `0006-durable-otlp-exporter.patch` | export through `durable_otel_exporter.py` to the fsynced local spool |
| `0007-discard-uncommitted-spans.patch` | a failed firing discards its staged spans, which replay re-emits |
| `0008-deterministic-observation-ids.patch` | derive every trace and span id from the transcript, so replay repeats them |

`durable_otel_exporter.py` sits beside the hook but is not upstream code: it is
this repository's spool exporter, kept here because the patched hook imports it
from its own directory. It is excluded from Ruff and Pyrefly with the rest of
`vendor/`. The tests that close the pre-merge gates (G1–G4) are listed in the
runbook's *Pre-merge verification* section.

### Updating

1. Fetch the new upstream revision and diff it against this copy.
2. Replace the file, then update the commit, SHA-256 and line count in the table above.
3. Re-check the PEP 723 block for dependency changes; mirror them into `../pyproject.toml`
   and regenerate the lock with `uv lock --project roles/devbox/files/dot_claude/bin`.
4. Run `make validate-claude` and `make test-claude-hooks`.
