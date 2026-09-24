---
name: hooks-architecture
description: >
  Claude Code hooks: the settings.json hooks block, lifecycle events, matchers,
  exit codes, and JSON output. Use when configuring hooks, writing hook scripts,
  or debugging why a hook does not fire.
problem: "Claude Code hook scripts get authored ad hoc without a shared taxonomy of lifecycle events, exit codes, and blocking rules."
related: []
---

# Hooks Architecture

Grounded in the upstream reference: https://code.claude.com/docs/en/hooks

## Where Hooks Live

Hooks are declared under the top-level `hooks` key of a **settings** file. Claude Code
reads them from these locations only:

| Location | Scope |
|----------|-------|
| `~/.claude/settings.json` | All projects |
| `.claude/settings.json` | Single project |
| `.claude/settings.local.json` | Single project, gitignored |
| Managed policy settings | Organisation-wide |
| A plugin's `hooks/hooks.json` | While the plugin is enabled |
| Skill and subagent frontmatter | While that skill/subagent is active |

**A standalone `~/.claude/hooks.json` is not one of them.** Claude Code never reads such a
file — no parse error, no warning, the hooks simply never fire. In this repository
the hooks live in `roles/devbox/files/dot_claude/settings.json.j2`, deployed by
`scripts/ai-config apply claude` against the ownership manifest `settings.ai-config.json`.
Any new top-level settings key must be declared in that manifest or the reconciler drops it.

Shape:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/bin/.venv/bin/python ~/.claude/bin/bash_decision_gate.py"
          }
        ]
      }
    ]
  }
}
```

Event names are PascalCase and must match what **the installed version** dispatches.
Claude Code validates the `hooks` block and complains about a key it does not know, so
an event lifted from the published reference but absent from the running release breaks
the whole file rather than failing quietly. Check the binary, not the docs table:

```
strings ~/.local/share/claude/versions/<version> | grep -oE '\b<EventName>\b' | head
```

`make validate-claude` enforces the list via the `hook-events` check; re-derive that enum
in `bin/validate_config.py` after upgrading Claude Code.

## Event Catalogue

Verified against 2.1.246 — 31 events. Newer releases add more (`PreModelSwitch` and
`PostModelSwitch` are documented upstream but not dispatched by 2.1.246).
"Blocks" means exit code 2 (or a JSON decision) stops the action.

| Event | Matcher matches | Blocks |
|-------|-----------------|--------|
| `SessionStart` | `startup\|resume\|clear\|compact\|fork` | no |
| `SessionEnd` | `clear\|resume\|logout\|prompt_input_exit\|other` | no |
| `Setup` | `init\|maintenance` | no |
| `UserPromptSubmit` | — | yes |
| `UserPromptExpansion` | command names | yes |
| `PreToolUse` | tool names | yes |
| `PermissionRequest` | tool names | via JSON `decision` |
| `PermissionDenied` | tool names | no |
| `PostToolUse` | tool names | no |
| `PostToolUseFailure` | tool names | no |
| `PostToolBatch` | — | no |
| `Notification` | notification type | no |
| `MessageDisplay` | — | no |
| `SubagentStart` | agent type | no |
| `SubagentStop` | agent type | yes |
| `TaskCreated` / `TaskCompleted` | — | no |
| `Stop` | — | yes |
| `StopFailure` | error type (`rate_limit`, `overloaded`, …) | no |
| `TeammateIdle` | — | no |
| `InstructionsLoaded` | `session_start\|nested_traversal\|path_glob_match\|include\|compact` | no |
| `ConfigChange` | `user_settings\|project_settings\|local_settings\|policy_settings\|skills` | no |
| `CwdChanged` | — | no |
| `DirectoryAdded` | `slash_command\|register_repo_root` | no |
| `FileChanged` | literal filenames | no |
| `WorktreeCreate` / `WorktreeRemove` | — | any non-zero exit aborts |
| `PreCompact` / `PostCompact` | `manual\|auto` | no |
| `Elicitation` / `ElicitationResult` | MCP server names | no |

Matchers are regular expressions. `"Bash"`, `"Edit|Write"`, `".*"`, `"^Edit$"` (exact —
excludes `NotebookEdit`). Omitting `matcher` on a matcher-capable event runs the hook
unconditionally. Events with no matcher column entry take no `matcher` at all.

## Hook Entry Schema

`type` is required. The rest depends on it.

| Field | Applies to | Meaning |
|-------|-----------|---------|
| `type` | all | `command`, `http`, `mcp_tool`, `prompt`, or `agent` |
| `if` | tool events | Permission-rule filter, e.g. `"Bash(git *)"`, `"Edit(*.ts)"` |
| `timeout` | all | **Seconds.** Default 600 for `command`/`http`/`mcp_tool`, 30 for `prompt`, 60 for `agent`. Capped at 30 on `UserPromptSubmit` and at 10 on `MessageDisplay`. Not enforced when `async` is set |
| `statusMessage` | all | Custom spinner text while the hook runs |
| `once` | all | Removes the hook after one successful run — **honoured only in skill frontmatter**, ignored in settings files and agent frontmatter |
| `command` | command | Shell command. Without `args` the string goes to the shell as-is; with `args` it is resolved on `PATH` and spawned directly, no shell |
| `args` | command | Argument vector for exec form; each element is one argument verbatim |
| `async` | command | Run in the background without blocking. `timeout` is not enforced |
| `asyncRewake` | command | Background, but exit 2 wakes Claude and shows the hook's stderr as a system reminder |
| `shell` | command | `bash` or `powershell` |
| `url`, `headers`, `allowedEnvVars` | http | POST target; header values interpolate only env vars listed in `allowedEnvVars` |
| `server`, `tool`, `input` | mcp_tool | MCP server and tool to invoke; `input` supports `${path}` substitution from the hook's JSON input |
| `prompt`, `model` | prompt, agent | Prompt text with `$ARGUMENTS` standing for the hook input JSON |

`prompt` and `agent` hooks are implemented, not aspirational — use them when the decision
needs judgement rather than a pattern match.

## Input Contract

Command hooks receive a JSON object **on stdin**. Fields present on every event:

```json
{
  "session_id": "abc123",
  "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "scratchpad_dir": "/tmp/claude-1000/.../scratchpad",
  "permission_mode": "default",
  "effort": { "level": "high" },
  "hook_event_name": "PreToolUse"
}
```

`agent_id` and `agent_type` appear inside a subagent. Each event adds its own fields —
`PreToolUse` adds `tool_name`, `tool_input`, `tool_use_id`; `Stop` adds
`stop_hook_active`; `FileChanged` adds `file_path` and `change_type`.

**Read stdin. Do not reach for environment variables to learn about the tool call** —
there are no `CC_TOOL_NAME`, `CC_TOOL_INPUT`, `CC_BASH_COMMAND`, or `TOOL_COUNT`
variables. The documented environment is small:

| Variable | Meaning |
|----------|---------|
| `CLAUDE_PROJECT_DIR` | Project root where the session started |
| `CLAUDE_PLUGIN_ROOT` | Plugin installation directory (plugin hooks) |
| `CLAUDE_PLUGIN_DATA` | Plugin persistent data directory |
| `CLAUDE_CODE_REMOTE` | `"true"` in remote web environments, unset locally |
| `CLAUDE_EFFORT` | Current effort level |
| `CLAUDE_PLUGIN_OPTION_<KEY>` | Plugin configuration values |

`OTEL_*` exporter variables are scrubbed from hook subprocesses by default.

## Output Contract

### Exit codes

| Code | stdout | stderr | Effect |
|------|--------|--------|--------|
| `0` | Parsed as JSON when it starts with `{` and ends with `}`, else plain text | Debug log only — Claude never sees it | Success. On `UserPromptSubmit`, `UserPromptExpansion` and `SessionStart`, plain-text stdout becomes context Claude sees |
| `2` | Valid JSON fields are still read | Used as the blocking message when the JSON carries no reason | Blocks on blocking-capable events. Even `permissionDecision: "allow"` cannot override it |
| other | Parsed as JSON if it parses | First line shown in a `<hook name> hook error` notice | Non-blocking on most events; aborts `WorktreeCreate`/`WorktreeRemove` |

Exit 1 is a plain failure, not a policy block — use exit 2 to enforce policy.

On timeout the hook is cancelled and its output discarded, so no decision takes effect.
A `PreToolUse` timeout does not block; the call proceeds through the normal permission flow.

### JSON output

Top-level fields, valid on any event: `continue`, `stopReason`, `suppressOutput`,
`systemMessage` (shown to Claude as a system reminder), `terminalSequence` (ANSI escapes
for a bell, window title, or desktop notification), and `hookSpecificOutput`.

`hookSpecificOutput` always carries `hookEventName` plus the event's own fields:

| Event | Fields |
|-------|--------|
| `PreToolUse` | `permissionDecision` (`allow`/`deny`/`ask`), `permissionDecisionReason`, `updatedInput` |
| `PostToolUse`, `PostToolUseFailure` | `additionalContext` |
| `Stop`, `SubagentStop` | `additionalContext` |
| `PermissionRequest` | `decision` (`allow`/`deny`/`ask`) — exit 2 is not honoured here |
| `PermissionDenied` | `retry` |
| `UserPromptSubmit` | `updatedPrompt` |
| `UserPromptExpansion` | `expandedPrompt` |

The remaining events — `PreCompact`, `PostCompact`, `Notification`, `MessageDisplay`,
`ConfigChange`, `InstructionsLoaded`, `CwdChanged`, `FileChanged`, `DirectoryAdded`,
`TaskCreated`, `TaskCompleted`, `TeammateIdle`, `StopFailure`, worktree events — discard
`hookSpecificOutput`; only `systemMessage` and `terminalSequence` survive.

`additionalContext` and `systemMessage` are the only ways to put text in front of Claude.
Anything written to stderr on exit 0 reaches the debug log and nowhere else.

## Repository Conventions

**Pinned interpreter.** Every hook command names the deployed venv's interpreter outright:

```
~/.claude/bin/.venv/bin/python ~/.claude/bin/<script>.py
```

Never `uv run`, `uvx`, `npx`, or a bare `python3`. Those resolve dependencies at
invocation time into a cache under `/tmp`, which macOS erodes by atime after three days,
leaving a half-installed environment that fails on every tool call. The
`hook-hermeticity` check in `validate_config.py` fails the build on any such command.

**Ordering.** Hooks in one group run in order; groups run in declaration order. Put
blocking guards first and observers last, so a logger records the outcome the guards
settled on rather than the state before them.

**Logging.** `universal_logger.py <EventName>` is registered on all 33 events. It takes
the event name as `argv[1]`; the `hook-events` check fails the build when that argument
disagrees with the key it is registered under, because the log would otherwise attribute
events to the wrong name.

## Patterns

### Guard (PreToolUse)

Block by JSON decision rather than exit code — the reason then reaches the user verbatim.

```python
payload = json.load(sys.stdin)
command = payload.get("tool_input", {}).get("command", "")

if DESTRUCTIVE.search(command):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Force-push blocked; use --force-with-lease.",
            }
        },
        sys.stdout,
    )
sys.exit(0)
```

Live example: `bin/bash_decision_gate.py`.

### Post-edit check (PostToolUse)

Cannot block. Report findings through `additionalContext` so Claude has to answer for them.

```python
if issues:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"Lint issues:\n{issues}\nFix before continuing.",
            }
        },
        sys.stdout,
    )
```

Live examples: `bin/post_edit_lint.py`, `bin/post_edit_typecheck.py`.

### Completion gate (Stop)

`Stop` fires again after a hook forces continuation. Honour `stop_hook_active` or the
session loops forever.

```python
payload = json.load(sys.stdin)
if payload.get("stop_hook_active"):
    sys.exit(0)  # second pass — let the agent stop
```

Live example: `bin/stop_lint_gate.py`.

### Background observer

Anything that only records — loggers, telemetry, checkpoint hints — takes `async: true`
so it never sits in the tool-call path. Combine with `asyncRewake` only when the
background result must actually interrupt Claude.

## Anti-Patterns

**Treating `timeout` as milliseconds.** `"timeout": 5000` is 83 minutes, not 5 seconds.

**Expecting `once` to work in settings.json.** It is honoured only in skill frontmatter;
elsewhere the hook runs every time regardless.

**Reading tool details from the environment.** The tool name and input arrive on stdin.
A hook that keys off `$CC_TOOL_NAME` sees an empty string and silently does nothing.

**Exit 1 to block.** Non-blocking on most events. Use exit 2, or a JSON decision.

**Slow synchronous PreToolUse hooks.** They sit in front of every matching tool call.
Keep them well under a second, or make them `async` and accept that they cannot block.

**Mutating the target file in PreToolUse.** The tool then operates on content that no
longer matches what Claude decided to write. Do it in PostToolUse.

**Blocking unconditionally.** A guard that exits 2 on every invocation disables the tool.
Gate on a matched pattern and exit 0 otherwise.

## Validation

- `make validate-claude` — `hook-events` (canonical event names, logger argv agreement,
  coverage warnings) and `hook-hermeticity` (pinned interpreter, repo and plugin hooks).
- `make test-claude-hooks` — the `bin/` suite under the deployed-venv shape.
- `/hooks` in a live session lists what Claude Code actually loaded. If a hook you wrote
  is missing there, it is in the wrong file — check the locations table above.
