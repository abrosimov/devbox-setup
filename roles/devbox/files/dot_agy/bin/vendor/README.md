# Vendored upstream sources

Third-party code symlinked from `dot_claude/bin/vendor/`. Files here are **not** ours to
restyle: they are excluded from Ruff and Pyrefly (see `extend-exclude` / `project-excludes`
in the root `pyproject.toml`) so that upstream diffs stay reviewable byte-for-byte.

## `langfuse_hook.py`

A symlink to `../../../dot_claude/bin/vendor/langfuse_hook.py` — one vendored copy,
two consumers. `ansible.posix.synchronize` resolves symlinks on deploy, so the target
machine receives a regular file.

| | |
|---|---|
| Upstream | <https://github.com/langfuse/claude-observability-plugin> |
| Canonical copy | `roles/devbox/files/dot_claude/bin/vendor/langfuse_hook.py` |
| Licence | MIT |

### Why the Claude Code hook works for Antigravity CLI

Antigravity CLI (agy) exposes the same hook lifecycle events (Stop, Start,
PreToolUse, PostToolUse, PreCompact) and delivers the same stdin payload shape
(`session_id`, `transcript_path`, `cwd`, `hook_event_name`). Its JSONL transcript
format is structurally compatible: `entry.message.role`, `entry.message.content`
with typed content blocks (`{type: "text", text: "..."}`), and
`entry.message.model` — the same contract the Claude langfuse hook parses via
`get_user_or_assistant_role_from_row()` and `get_content_from_row()`.

Differences are handled entirely through environment variables:

- `CC_LANGFUSE_STATE_DIR` → `~/.gemini/antigravity-cli/state` (isolates state
  from Claude Code's `~/.claude/state`)
- `CC_LANGFUSE_BASE_URL` / `CC_LANGFUSE_PUBLIC_KEY` / `CC_LANGFUSE_SECRET_KEY` →
  same loopback otelbox credentials

### Updating

Update the canonical copy in `roles/devbox/files/dot_claude/bin/vendor/` — the
symlink picks up the change automatically.
