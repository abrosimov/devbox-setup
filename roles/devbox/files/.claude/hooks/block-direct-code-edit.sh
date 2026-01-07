#!/bin/bash
# PreToolUse hook: Block direct Edit on code files
# Forces code changes to go through software engineer agents via /implement

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Check if this is a code file
if [[ "$FILE_PATH" =~ \.(go|py)$ ]]; then
  cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct code edits are blocked. Use /implement to modify code files through the software engineer agent."
  }
}
EOF
else
  # Allow non-code files (configs, docs, etc.)
  cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
fi
