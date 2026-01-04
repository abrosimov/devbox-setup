#!/bin/bash
# PreToolUse hook: Require user confirmation before launching implementation agents
# This hook triggers the "ask" permission decision, prompting user in UI

# Read the tool input from stdin
INPUT=$(cat)

# Extract subagent_type from the Task tool input
SUBAGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)

# List of agent types that require explicit approval
APPROVAL_AGENTS=(
    "software-engineer-go"
    "software-engineer-python"
    "unit-test-writer-go"
    "unit-test-writer-python"
    "implementation-planner-go"
    "implementation-planner-python"
)

# Check if this agent type requires approval
REQUIRES_APPROVAL=false
for agent in "${APPROVAL_AGENTS[@]}"; do
    if [[ "$SUBAGENT_TYPE" == "$agent" ]]; then
        REQUIRES_APPROVAL=true
        break
    fi
done

if [[ "$REQUIRES_APPROVAL" == "true" ]]; then
    # Output JSON to request user confirmation
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "Launching $SUBAGENT_TYPE agent - confirm you approved this implementation?"
  }
}
EOF
else
    # Allow non-implementation agents to proceed
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
fi
