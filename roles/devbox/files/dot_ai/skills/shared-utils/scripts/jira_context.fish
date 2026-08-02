#!/usr/bin/env fish
# Extract Jira context from git branch (Fish shell version)
#
# Usage:
#   source ./jira_context.fish
#   echo $JIRA_ISSUE
#
# Expects branch naming convention: JIRAPRJ-123_description_of_branch
#
# Sets variables:
#   BRANCH - full branch name
#   JIRA_ISSUE - extracted Jira key (first segment before underscore)
#   BRANCH_NAME - description part (everything after first underscore)

# Get current branch
set -g BRANCH (git branch --show-current 2>/dev/null)

if test -z "$BRANCH"
    echo "ERROR: Not in a git repository or no branch checked out" >&2
    exit 1
end

# Extract Jira issue from branch name
# Convention: JIRAPRJ-123_description → JIRAPRJ-123
set -g JIRA_ISSUE (string split -f1 '_' $BRANCH)

# Extract branch name (everything after first underscore)
# Convention: JIRAPRJ-123_description → description
set -g BRANCH_NAME (string split -m1 -f2 '_' $BRANCH)

# Validate Jira issue format (PROJECT-NUMBER)
if not string match -rq '^[A-Z]+-[0-9]+$' $JIRA_ISSUE
    echo "WARNING: Branch '$BRANCH' doesn't follow JIRAPRJ-123_description convention" >&2
    echo "JIRA_ISSUE may be invalid: $JIRA_ISSUE" >&2
end

# Export for use in current session
set -gx BRANCH $BRANCH
set -gx JIRA_ISSUE $JIRA_ISSUE
set -gx BRANCH_NAME $BRANCH_NAME

# Output for confirmation
echo "BRANCH=$BRANCH"
echo "JIRA_ISSUE=$JIRA_ISSUE"
echo "BRANCH_NAME=$BRANCH_NAME"
