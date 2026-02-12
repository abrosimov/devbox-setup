#!/bin/bash
# Go Implementation Complexity Check
# Outputs metrics and recommends SONNET or OPUS model
#
# Usage: ./complexity_check.sh [plans_dir] [jira_issue]
# Example: ./complexity_check.sh ~/.claude/plans PROJ-123
#
# Exit codes:
#   0 - SONNET recommended (simple task)
#   1 - OPUS recommended (complex task)

set -euo pipefail

PLANS_DIR="${1:-}"
JIRA_ISSUE="${2:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Go Implementation Complexity Check ==="
echo ""

# Metric 1: Plan lines (if plan exists)
PLAN_LINES=0
if [[ -n "$PLANS_DIR" && -n "$JIRA_ISSUE" && -f "${PLANS_DIR}/${JIRA_ISSUE}/plan.md" ]]; then
    PLAN_LINES=$(wc -l < "${PLANS_DIR}/${JIRA_ISSUE}/plan.md" 2>/dev/null || echo 0)
    echo "Plan lines: ${PLAN_LINES}"
else
    echo "Plan lines: N/A (no plan found)"
fi

# Metric 2: Changed Go files (excluding tests)
CHANGED_FILES=$(git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | grep -v _test.go | wc -l | tr -d ' ' || echo 0)
echo "Changed Go files (non-test): ${CHANGED_FILES}"

# Metric 3: Concurrency patterns in changed files
CONCURRENCY_FILES=0
if [[ "$CHANGED_FILES" -gt 0 ]]; then
    CONCURRENCY_FILES=$(git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | \
        grep -v _test.go | \
        xargs grep -l "go func\|chan \|sync\.\|select {" 2>/dev/null | \
        wc -l | tr -d ' ' || echo 0)
fi
echo "Files with concurrency: ${CONCURRENCY_FILES}"

# Metric 4: Error handling sites
ERROR_SITES=0
if [[ "$CHANGED_FILES" -gt 0 ]]; then
    ERROR_SITES=$(git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' 2>/dev/null | \
        grep -v _test.go | \
        xargs grep -c "if err != nil\|return.*err" 2>/dev/null | \
        awk -F: '{sum+=$2} END {print sum}' || echo 0)
fi
echo "Error handling sites: ${ERROR_SITES}"

echo ""
echo "=== Thresholds ==="
echo "Plan > 200 lines: $([ "$PLAN_LINES" -gt 200 ] && echo 'YES' || echo 'no')"
echo "Files > 8: $([ "$CHANGED_FILES" -gt 8 ] && echo 'YES' || echo 'no')"
echo "Concurrency: $([ "$CONCURRENCY_FILES" -gt 0 ] && echo 'YES' || echo 'no')"
echo "Error sites > 20: $([ "$ERROR_SITES" -gt 20 ] && echo 'YES' || echo 'no')"

echo ""

# Decision
RECOMMEND_OPUS=0

if [[ "$PLAN_LINES" -gt 200 ]]; then
    RECOMMEND_OPUS=1
fi

if [[ "$CHANGED_FILES" -gt 8 ]]; then
    RECOMMEND_OPUS=1
fi

if [[ "$CONCURRENCY_FILES" -gt 0 ]]; then
    RECOMMEND_OPUS=1
fi

if [[ "$ERROR_SITES" -gt 20 ]]; then
    RECOMMEND_OPUS=1
fi

if [[ "$RECOMMEND_OPUS" -eq 1 ]]; then
    echo -e "${YELLOW}=== RECOMMENDATION: OPUS ===${NC}"
    echo "Complex task detected. Use: /implement opus"
    exit 1
else
    echo -e "${GREEN}=== RECOMMENDATION: SONNET ===${NC}"
    echo "Standard complexity. Proceeding with Sonnet."
    exit 0
fi
