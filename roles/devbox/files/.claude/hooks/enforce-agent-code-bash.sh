#!/bin/bash
# PreToolUse hook: Enforce agent-based code writing via Bash
# Blocks bash commands that write to .go/.py files from main Claude
# Allows from subagents (they ARE the approved software engineer agents)

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

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

# Patterns that write to files:
# - cat ... > file, cat << EOF > file
# - echo ... > file
# - printf ... > file
# - tee file
# - > file (redirect)
# Check if command writes to a .go or .py file
# Use -z for null-separated to handle multiline, and check common patterns
if echo "$COMMAND" | grep -qE '>\s*\S*\.(go|py)' || \
   echo "$COMMAND" | grep -qE 'tee\s+\S*\.(go|py)'; then
  cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Bash file writes to code files are blocked. Use /implement to create/modify code files through the software engineer agent."
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
