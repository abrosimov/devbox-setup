#!/usr/bin/env bash
# Validation script to check Go code for common violations

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

violations=0

echo "🔍 Validating Go code for common violations..."
echo ""

# Check for functions returning pointer without error
echo "Checking for nil pointer returns without error..."
if git diff --cached --name-only | grep '\.go$' | xargs grep -n 'func.*\*[A-Z][a-Za-z]*)$' 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Found functions returning pointer without error - review manually${NC}"
    echo "   Rule: Functions that can return nil pointer MUST return error"
    echo ""
fi

# Check for mixed receiver types (more complex, requires parsing)
echo "Checking for mixed receiver types..."
for file in $(git diff --cached --name-only | grep '\.go$'); do
    if [ -f "$file" ]; then
        # Extract type names that have methods
        types=$(grep -oP '(?<=func \()[a-z] \*?[A-Z][a-zA-Z]+(?=\))' "$file" 2>/dev/null | awk '{print $2}' | sort -u || true)

        for type in $types; do
            # Check if this type has both pointer and value receivers
            has_pointer=$(grep -c "func ([a-z] \*${type})" "$file" 2>/dev/null || true)
            has_value=$(grep -c "func ([a-z] ${type})" "$file" 2>/dev/null || true)

            if [ "$has_pointer" -gt 0 ] && [ "$has_value" -gt 0 ]; then
                echo -e "${RED}❌ Type '$type' in $file has MIXED receivers (pointer and value)${NC}"
                echo "   Rule: If ANY method uses pointer receiver, ALL must use pointer"
                echo "   Found: $has_pointer pointer receiver(s) and $has_value value receiver(s)"
                echo ""
                violations=$((violations + 1))
            fi
        done
    fi
done

# Check for obvious nil returns without error handling
echo "Checking for 'return nil' without error context..."
if git diff --cached --name-only | grep '\.go$' | xargs grep -n 'return nil$' 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Found 'return nil' statements - ensure these are paired with errors${NC}"
    echo "   Rule: Returning nil pointer should be accompanied by error"
    echo ""
fi

# --- CRITICAL Security Patterns (never acceptable) ---

GO_FILES=$(git diff --cached --name-only | grep '\.go$' || true)

if [ -n "$GO_FILES" ]; then
    echo ""
    echo "🔒 Checking for CRITICAL security patterns..."
    echo ""

    # CRITICAL: Timing-unsafe token/secret comparison
    echo "Checking for timing-unsafe comparisons on secrets..."
    if echo "$GO_FILES" | xargs grep -n '== .*[Tt]oken\|== .*[Ss]ecret\|== .*[Kk]ey\|== .*[Hh]ash\|== .*[Pp]assword\|!= .*[Tt]oken\|!= .*[Ss]ecret' 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Possible timing-unsafe comparison on secret — use crypto/subtle.ConstantTimeCompare${NC}"
        echo ""
    fi

    # CRITICAL: math/rand for security
    echo "Checking for math/rand usage..."
    if echo "$GO_FILES" | xargs grep -n '"math/rand"' 2>/dev/null; then
        echo -e "${YELLOW}⚠️  math/rand imported — if used for tokens/keys/security, use crypto/rand instead${NC}"
        echo ""
    fi

    # CRITICAL: SQL string concatenation
    echo "Checking for SQL string concatenation..."
    if echo "$GO_FILES" | xargs grep -n 'fmt.Sprintf.*SELECT\|fmt.Sprintf.*INSERT\|fmt.Sprintf.*UPDATE\|fmt.Sprintf.*DELETE\|Sprintf.*WHERE' 2>/dev/null; then
        echo -e "${RED}❌ SQL string concatenation detected — use parameterised queries${NC}"
        echo ""
        violations=$((violations + 1))
    fi

    # CRITICAL: Command injection via shell
    echo "Checking for shell command injection..."
    if echo "$GO_FILES" | xargs grep -n 'exec.Command("sh"\|exec.Command("bash"\|exec.Command("/bin/sh"\|exec.Command("/bin/bash"' 2>/dev/null; then
        echo -e "${YELLOW}⚠️  exec.Command with shell — if args include user input, use argument list instead${NC}"
        echo ""
    fi
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $violations -eq 0 ]; then
    echo -e "${GREEN}✅ Validation passed${NC}"
    exit 0
else
    echo -e "${RED}❌ Found $violations violation(s)${NC}"
    echo ""
    echo "Fix violations or bypass with: git commit --no-verify"
    exit 1
fi
