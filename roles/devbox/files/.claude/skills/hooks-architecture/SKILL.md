---
name: hooks-architecture
description: >
  Claude Code hooks system architecture and patterns. Triggers on: hooks, preToolUse, postToolUse, hook configuration, event lifecycle.
---

# Hooks Architecture

## Hook Event Types

Hooks intercept Claude Code lifecycle events.

| Event | When | Can Block | Use Case |
|-------|------|-----------|----------|
| **PreToolUse** | Before tool execution | Yes (exit 2) | Guard against destructive actions |
| **PostToolUse** | After tool execution | No | Format, lint, typecheck after edits |
| **PreCompact** | Before context compaction | No | Save session state |
| **SessionStart** | Session begins | No | Load project context |
| **SessionEnd** | Session ends | No | Save session state |
| **Notification** | Notification sent | No | Log notifications |
| **Stop** | Agent stops | No | Cleanup |

### PreToolUse

Runs before tool execution. Can block with `exit 2`.

**Example**: Prevent destructive git commands
```bash
#!/usr/bin/env bash
# bin/guard-git-force-push

if [[ "$CC_BASH_COMMAND" =~ "git push --force" ]]; then
    echo "ERROR: Force push blocked. Use --force-with-lease instead."
    exit 2  # Block tool execution
fi

exit 0  # Allow tool execution
```

**hooks.json**:
```json
{
  "preToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "command": "guard-git-force-push",
          "timeout": 5000
        }
      ]
    }
  ]
}
```

**Exit codes**:
- `0`: Allow tool execution
- `2`: Block tool execution (error shown to Claude)
- Other: Hook failure (doesn't block tool)

### PostToolUse

Runs after tool execution. Cannot block.

**Example**: Format files after edit
```bash
#!/usr/bin/env bash
# bin/post-edit-format

if [[ "$CC_TOOL_NAME" == "Edit" || "$CC_TOOL_NAME" == "Write" ]]; then
    # Extract file path from tool input
    file_path=$(echo "$CC_TOOL_INPUT" | jq -r '.file_path')

    if [[ "$file_path" =~ \.go$ ]]; then
        goimports -local $(head -1 go.mod | awk '{print $2}') -w "$file_path"
    elif [[ "$file_path" =~ \.py$ ]]; then
        ruff format "$file_path"
    fi
fi

exit 0
```

**hooks.json**:
```json
{
  "postToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "command": "post-edit-format",
          "async": true,
          "timeout": 10000
        }
      ]
    }
  ]
}
```

**async**: Runs in background (doesn't block next tool call).

### PreCompact

Runs before context compaction (when conversation grows too large).

**Example**: Save session state
```bash
#!/usr/bin/env bash
# bin/session-save

# Save git status, modified files, current branch
git status --short > ~/.claude/sessions/$SESSION_ID/git_status.txt
git branch --show-current > ~/.claude/sessions/$SESSION_ID/branch.txt

exit 0
```

**hooks.json**:
```json
{
  "preCompact": [
    {
      "hooks": [
        {
          "command": "session-save",
          "timeout": 5000
        }
      ]
    }
  ]
}
```

### SessionStart/SessionEnd

**SessionStart**: Runs when session begins.

**Example**: Load project-specific context
```bash
#!/usr/bin/env bash
# bin/session-start

# Print project README to context
if [[ -f README.md ]]; then
    echo "Project context loaded from README.md"
fi

exit 0
```

**SessionEnd**: Runs when session ends.

**Example**: Clean up temporary files
```bash
#!/usr/bin/env bash
# bin/session-end

# Remove temporary session files
rm -rf /tmp/claude-session-$SESSION_ID

exit 0
```

### Notification

Runs when notification is sent.

**Example**: Log notifications
```bash
#!/usr/bin/env bash
# bin/log-notification

echo "$(date): Notification sent" >> ~/.claude/notifications.log

exit 0
```

### Stop

Runs when agent stops.

**Example**: Save agent state
```bash
#!/usr/bin/env bash
# bin/agent-stop

echo "Agent stopped at $(date)" >> ~/.claude/agent.log

exit 0
```

## Hook Configuration

### hooks.json Structure

```json
{
  "preToolUse": [
    {
      "matcher": "Bash|Edit|Write",  // Tool name pattern (regex)
      "hooks": [
        {
          "command": "hook-script-name",  // Script in ~/.claude/bin/
          "timeout": 5000,                 // Milliseconds (default: 30000)
          "async": false,                  // Run in background (default: false)
          "once": false                    // Run only once per session (default: false)
        }
      ]
    }
  ],
  "postToolUse": [...],
  "preCompact": [...],
  "sessionStart": [...],
  "sessionEnd": [...],
  "notification": [...],
  "stop": [...]
}
```

### Matcher Patterns

Regular expression matching tool names.

**Examples**:
- `"Bash"` — matches only Bash tool
- `"Edit|Write"` — matches Edit or Write
- `".*"` — matches all tools
- `"^Edit$"` — exact match (Edit, not NotebookEdit)

### Hook Array

Multiple hooks can run for one event (executed in order).

```json
{
  "postToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {"command": "post-edit-format", "async": true},
        {"command": "post-edit-typecheck", "async": true},
        {"command": "post-edit-lint", "async": true}
      ]
    }
  ]
}
```

**Order matters**: Format → typecheck → lint.

### Timeout

Maximum execution time in milliseconds.

```json
{
  "command": "slow-hook",
  "timeout": 60000  // 60 seconds
}
```

**Default**: 30000 (30 seconds).

**Exceeded**: Hook killed, error logged (doesn't block tool in PostToolUse).

### Async

Run in background (PostToolUse only).

```json
{
  "command": "post-edit-format",
  "async": true  // Doesn't block next tool call
}
```

**When to use**: Slow operations (format, lint, typecheck) that don't need to block.

**When NOT to use**: PreToolUse (blocking is the point).

### Once

Run only once per session.

```json
{
  "command": "session-init",
  "once": true  // Only runs on first trigger
}
```

**Use case**: Expensive setup (load configuration, initialise cache).

## Hook Types

### Command Hooks

Shell command with environment variables.

```json
{
  "command": "my-hook-script"
}
```

**Looks for**: `~/.claude/bin/my-hook-script` (must be executable).

**Environment variables**:
- `$CC_TOOL_NAME`: Tool name (e.g., "Bash", "Edit")
- `$CC_TOOL_INPUT`: Tool input JSON (e.g., `{"file_path": "/path/to/file"}`)
- `$CC_BASH_COMMAND`: Bash command (only for Bash tool)
- `$TOOL_COUNT`: Total tool calls in session
- `$SESSION_ID`: Unique session identifier

**Example**:
```bash
#!/usr/bin/env bash
# bin/debug-hook

echo "Tool: $CC_TOOL_NAME"
echo "Input: $CC_TOOL_INPUT"
echo "Tool count: $TOOL_COUNT"

exit 0
```

### Prompt Hooks

LLM evaluation (not yet implemented in hooks.json, but conceptually available).

**Concept**: Pass tool input to LLM, decide whether to block.

```json
{
  "type": "prompt",
  "prompt": "Is this Bash command safe to run? Command: {{CC_BASH_COMMAND}}"
}
```

**Use case**: Complex safety checks (e.g., "does this SQL query drop tables?").

### Agent Hooks

Agentic verification (not yet implemented, future feature).

**Concept**: Spawn agent to verify action.

```json
{
  "type": "agent",
  "agent": "security-reviewer",
  "prompt": "Review this code change for security issues"
}
```

## Environment Variables

### Available in All Hooks

| Variable | Value | Example |
|----------|-------|---------|
| `$CC_TOOL_NAME` | Tool name | `"Bash"`, `"Edit"`, `"Write"` |
| `$CC_TOOL_INPUT` | Tool input (JSON) | `{"file_path": "/path/to/file", "old_string": "...", "new_string": "..."}` |
| `$TOOL_COUNT` | Total tool calls | `42` |
| `$SESSION_ID` | Unique session ID | `abc123` |

### Bash Tool Only

| Variable | Value | Example |
|----------|-------|---------|
| `$CC_BASH_COMMAND` | Command string | `git commit -m "message"` |

### Extracting from JSON

Use `jq` to parse `$CC_TOOL_INPUT`:

```bash
#!/usr/bin/env bash
# bin/extract-file-path

file_path=$(echo "$CC_TOOL_INPUT" | jq -r '.file_path')
echo "Editing: $file_path"

exit 0
```

## Patterns

### Guard Hooks (PreToolUse)

Block destructive actions.

**Example**: Prevent committing secrets
```bash
#!/usr/bin/env bash
# bin/guard-secrets

if [[ "$CC_BASH_COMMAND" =~ "git commit" ]]; then
    # Check staged files for secrets
    if git diff --cached | grep -E 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}'; then
        echo "ERROR: Secret detected in staged files"
        exit 2  # Block commit
    fi
fi

exit 0
```

**Example**: Prevent large file commits
```bash
#!/usr/bin/env bash
# bin/guard-large-files

if [[ "$CC_BASH_COMMAND" =~ "git add" ]]; then
    # Check for files >5MB
    if find . -type f -size +5M | grep -q .; then
        echo "ERROR: Large file detected (>5MB)"
        exit 2  # Block add
    fi
fi

exit 0
```

### Format-on-Save (PostToolUse)

Auto-format files after edit.

```bash
#!/usr/bin/env bash
# bin/post-edit-format

if [[ "$CC_TOOL_NAME" != "Edit" && "$CC_TOOL_NAME" != "Write" ]]; then
    exit 0  # Only run for Edit/Write
fi

file_path=$(echo "$CC_TOOL_INPUT" | jq -r '.file_path')

case "$file_path" in
    *.go)
        goimports -local $(head -1 go.mod | awk '{print $2}') -w "$file_path"
        ;;
    *.py)
        ruff format "$file_path"
        ;;
    *.ts|*.tsx|*.js|*.jsx)
        prettier --write "$file_path"
        ;;
esac

exit 0
```

**hooks.json**:
```json
{
  "postToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "command": "post-edit-format",
          "async": true
        }
      ]
    }
  ]
}
```

### Checkpoint Suggestion (PostToolUse)

Suggest checkpoint after N tool calls.

```bash
#!/usr/bin/env bash
# bin/suggest-checkpoint

# Suggest checkpoint every 50 tool calls
if (( TOOL_COUNT % 50 == 0 )); then
    echo "SUGGESTION: Consider creating a checkpoint (/checkpoint)"
fi

exit 0
```

**hooks.json**:
```json
{
  "postToolUse": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "command": "suggest-checkpoint",
          "async": true
        }
      ]
    }
  ]
}
```

### Session State Preservation (PreCompact, SessionEnd)

Save state before compaction or session end.

```bash
#!/usr/bin/env bash
# bin/session-save

session_dir="$HOME/.claude/sessions/$SESSION_ID"
mkdir -p "$session_dir"

# Save git state
git status --short > "$session_dir/git_status.txt"
git branch --show-current > "$session_dir/branch.txt"
git log -1 --format="%H %s" > "$session_dir/last_commit.txt"

# Save modified files
git diff --name-only > "$session_dir/modified_files.txt"

# Save session metadata
cat > "$session_dir/metadata.json" <<EOF
{
  "tool_count": $TOOL_COUNT,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "cwd": "$(pwd)"
}
EOF

exit 0
```

**hooks.json**:
```json
{
  "preCompact": [
    {
      "hooks": [
        {
          "command": "session-save",
          "timeout": 10000
        }
      ]
    }
  ],
  "sessionEnd": [
    {
      "hooks": [
        {
          "command": "session-save",
          "timeout": 10000
        }
      ]
    }
  ]
}
```

## Anti-Patterns

### Synchronous Hooks That Are Slow

**Problem**: Blocks Claude Code pipeline.

```json
// BAD: Slow synchronous hook
{
  "command": "run-all-tests",  // Takes 30 seconds
  "async": false
}
```

**Solution**: Make it async or move to separate workflow.

```json
// GOOD: Async hook
{
  "command": "run-all-tests",
  "async": true
}
```

### Hooks That Modify Files in PreToolUse

**Problem**: Confuses the tool (file changed before tool runs).

```bash
#!/usr/bin/env bash
# BAD: Modifies file in PreToolUse

file_path=$(echo "$CC_TOOL_INPUT" | jq -r '.file_path')
goimports -w "$file_path"  # Changes file before Edit tool runs

exit 0
```

**Solution**: Move to PostToolUse.

### Hooks Without Timeout

**Problem**: Can hang forever.

```json
// BAD: No timeout (default 30s may not be enough)
{
  "command": "slow-operation"
}
```

**Solution**: Set explicit timeout.

```json
// GOOD: Explicit timeout
{
  "command": "slow-operation",
  "timeout": 120000  // 2 minutes
}
```

### Hooks That Always Exit 2

**Problem**: Blocks all tool calls.

```bash
#!/usr/bin/env bash
# BAD: Always blocks

exit 2  # Blocks every tool call
```

**Solution**: Add conditional logic.

```bash
#!/usr/bin/env bash
# GOOD: Conditional blocking

if [[ "$CC_BASH_COMMAND" =~ "rm -rf /" ]]; then
    exit 2  # Block only dangerous commands
fi

exit 0
```

## Best Practises

1. **Fast PreToolUse hooks**: <100ms (blocks Claude Code)
2. **Async PostToolUse hooks**: Use async for slow operations (format, lint)
3. **Explicit timeouts**: Set timeout for all hooks (avoid hangs)
4. **Conditional blocking**: Only block truly dangerous actions (PreToolUse exit 2)
5. **Error handling**: Hooks should not crash (catch errors, exit gracefully)
6. **Logging**: Log to file (not stdout) for debugging
7. **Test hooks**: Run manually with env vars set (test blocking, timeout, async)
