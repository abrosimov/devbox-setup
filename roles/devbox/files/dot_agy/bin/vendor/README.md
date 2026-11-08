# Vendored upstream sources

Third-party code symlinked from `dot_claude/bin/vendor/`. Files here are **not** ours to
restyle: they are excluded from Ruff and Pyrefly (see `extend-exclude` / `project-excludes`
in the root `pyproject.toml`) so that upstream diffs stay reviewable byte-for-byte.

## `langfuse_hook.py`

A symlink to `../../../dot_claude/bin/vendor/langfuse_hook.py` — one vendored copy,
two consumers. The AGY bin synchronisation task explicitly sets `copy_links: true`
to dereference repository symlinks on deployment. The target machine receives a
regular file because the repository's relative source layout is not installed.

| | |
|---|---|
| Upstream | <https://github.com/langfuse/claude-observability-plugin> |
| Canonical copy | `roles/devbox/files/dot_claude/bin/vendor/langfuse_hook.py` |
| Licence | MIT |

## `durable_otel_exporter.py`

A symlink to `../../../dot_claude/bin/vendor/durable_otel_exporter.py`, deployed the
same way. The patched hook imports it from its own directory, so without it the hook
cannot create its Langfuse client.

### Why the hook is registered but disabled for Antigravity CLI

The `langfuse_hook` entry in `../../config/hooks.json.j2` stays `"enabled": false`,
because the Claude hook cannot read what agy gives it:

- **Payload.** agy sends camelCase fields (`conversationId`, `transcriptPath`) and no
  `hook_event_name`; the hook reads `session_id` / `transcript_path` and exits without
  reading anything.
- **Transcript.** agy's `transcript.jsonl` (under
  `~/.gemini/antigravity-cli/brain/<conversation>/.system_generated/logs/`) is a log of
  typed steps (`USER_INPUT`, `PLANNER_RESPONSE` with `thinking` and `tool_calls`,
  `RUN_COMMAND`, `VIEW_FILE`, ...) with no `message` and no role. The hook keeps only
  rows typed `user` / `assistant` or carrying `message.role`, so it finds no turn:
  every one of the 3,126 steps across 40 local transcripts is skipped. Tool calls carry
  no ids to pair them with their result steps, and the file is a rolling window rather
  than an append-only log.
- **Output.** agy's Stop contract expects a JSON object on stdout; the hook writes none.

Tracing agy needs a translator from its step log to turns, which has not been written.
The environment for that path is already set by the `agy` fish wrapper:
`CC_LANGFUSE_STATE_DIR` (`~/.gemini/antigravity-cli/state`, apart from Claude's),
the loopback `CC_LANGFUSE_*` credentials, and `CC_LANGFUSE_TRACE_TAGS=["engine:agy"]`.

### Updating

Update the canonical copy in `roles/devbox/files/dot_claude/bin/vendor/` — the
symlink picks up the change automatically.
