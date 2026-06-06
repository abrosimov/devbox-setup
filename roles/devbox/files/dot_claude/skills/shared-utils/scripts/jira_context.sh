#!/bin/bash
# Extract Jira context from git branch
#
# Usage:
#   Bash:  source ./jira_context.sh && echo $JIRA_ISSUE
#   Fish:  set -x JIRA_ISSUE (./jira_context.sh | grep JIRA_ISSUE | cut -d= -f2)
#   Direct: ./jira_context.sh
#
# Expects branch naming convention: JIRAPRJ-123_description_of_branch
#
# Outputs:
#   BRANCH=feature_branch_name
#   JIRA_ISSUE=JIRAPRJ-123
#   BRANCH_NAME=description_of_branch

set -euo pipefail

# Get current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "")

if [[ -z "$BRANCH" ]]; then
    echo "ERROR: Not in a git repository or no branch checked out" >&2
    exit 1
fi

# Extract Jira issue from branch name
# Convention: JIRAPRJ-123_description → JIRAPRJ-123
JIRA_ISSUE=$(echo "$BRANCH" | cut -d'_' -f1)

# Extract branch name (everything after first underscore)
# Convention: JIRAPRJ-123_description → description
BRANCH_NAME=$(echo "$BRANCH" | cut -d'_' -f2-)

# Validate Jira issue format (PROJECT-NUMBER)
if [[ ! "$JIRA_ISSUE" =~ ^[A-Z]+-[0-9]+$ ]]; then
    echo "WARNING: Branch '$BRANCH' doesn't follow JIRAPRJ-123_description convention" >&2
    echo "JIRA_ISSUE may be invalid: $JIRA_ISSUE" >&2
fi

# Export for sourcing (bash)
export BRANCH
export JIRA_ISSUE
export BRANCH_NAME

# Output for direct execution or fish parsing
echo "BRANCH=${BRANCH}"
echo "JIRA_ISSUE=${JIRA_ISSUE}"
echo "BRANCH_NAME=${BRANCH_NAME}"
