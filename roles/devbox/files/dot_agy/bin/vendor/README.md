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

### Why the Claude Code hook works for Antigravity CLI

Antigravity CLI (agy) exposes the same hook lifecycle events (Stop, Start,
PreToolUse, PostToolUse, PreCompact) and delivers the same stdin payload shape
(`session_id`, `transcript_path`, `cwd`, `hook_event_name`). Its JSONL transcript
format is structurally compatible: `entry.message.role`, `entry.message.content`
with typed content blocks (`{type: "text", text: "..."}`), and
`entry.message.model` — the same contract the Claude langfuse hook parses via
`get_user_or_assistant_role_from_row()` and `get_content_from_row()`.

The hook is an unmodified copy of the Claude Code vendor. Differences are handled
entirely through environment variables:

- `CC_LANGFUSE_STATE_DIR` → `~/.gemini/antigravity-cli/state` (isolates state
  from Claude Code's `~/.claude/state`)
- `CC_LANGFUSE_BASE_URL` / `CC_LANGFUSE_PUBLIC_KEY` / `CC_LANGFUSE_SECRET_KEY` →
  same loopback otelbox credentials

Token usage field names (`input_tokens` / `output_tokens`) and model names flow
through from the transcript as-is; the hook uses whatever the transcript provides.

### Updating

Follow the same procedure as `roles/devbox/files/dot_claude/bin/vendor/README.md`.
Keep both copies at the same upstream commit.
