#!/bin/bash
# PreToolUse hook: Enforce agent-based code creation
# Blocks direct Write on .go/.py files from main Claude
# Allows writes from subagents (they ARE the approved software engineer agents)

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Detect if running inside a subagent by checking transcript_path
# Subagent transcripts are stored in .../subagents/agent-*.jsonl
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
if [[ "$TRANSCRIPT_PATH" == *"/subagents/"* ]]; then
  cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
  exit 0
fi

# Check if this is a code file (only block for main Claude)
if [[ "$FILE_PATH" =~ \.(go|py)$ ]]; then
  cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct code file creation is blocked. Use /implement to create code files through the software engineer agent."
  }
}
EOF
else
  cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
fi
