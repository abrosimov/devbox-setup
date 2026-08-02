#!/usr/bin/env bash
# Classify implementation risk from an optional plan and the current branch diff.

set -euo pipefail

go_skill_plan_file="${1:-}"
go_skill_base_ref="${2:-}"

if [[ -n "$go_skill_plan_file" && ! -f "$go_skill_plan_file" ]]; then
    echo "Plan file does not exist: $go_skill_plan_file" >&2
    exit 2
fi

go_skill_plan_lines=0
if [[ -n "$go_skill_plan_file" ]]; then
    go_skill_plan_lines=$(wc -l < "$go_skill_plan_file" | tr -d ' ')
fi

if [[ -z "$go_skill_base_ref" ]]; then
    if go_skill_origin_head=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null); then
        go_skill_base_ref="$go_skill_origin_head"
    elif git rev-parse --verify --quiet main >/dev/null; then
        go_skill_base_ref="main"
    elif git rev-parse --verify --quiet master >/dev/null; then
        go_skill_base_ref="master"
    fi
fi

go_skill_changed_files=""
if [[ -n "$go_skill_base_ref" ]] && git merge-base "$go_skill_base_ref" HEAD >/dev/null 2>&1; then
    go_skill_changed_files=$(git diff --name-only "$go_skill_base_ref"...HEAD -- '*.go' | sed '/_test\.go$/d')
else
    go_skill_base_ref="unavailable"
fi

go_skill_file_count=$(printf '%s\n' "$go_skill_changed_files" | sed '/^$/d' | wc -l | tr -d ' ')
go_skill_concurrency_files=0
go_skill_error_sites=0

while IFS= read -r go_skill_file; do
    [[ -n "$go_skill_file" && -f "$go_skill_file" ]] || continue

    if grep -Eq 'go[[:space:]]+func|chan[[:space:]]|sync\.|select[[:space:]]*\{' "$go_skill_file"; then
        go_skill_concurrency_files=$((go_skill_concurrency_files + 1))
    fi

    go_skill_file_error_sites=$(grep -Ec 'if[[:space:]]+err[[:space:]]*!=[[:space:]]*nil|return.*err' "$go_skill_file" || true)
    go_skill_error_sites=$((go_skill_error_sites + go_skill_file_error_sites))
done <<EOF
$go_skill_changed_files
EOF

go_skill_complexity="standard"
go_skill_reasons=""

if [[ "$go_skill_plan_lines" -gt 200 ]]; then
    go_skill_complexity="high"
    go_skill_reasons="${go_skill_reasons} plan-over-200-lines;"
fi
if [[ "$go_skill_file_count" -gt 8 ]]; then
    go_skill_complexity="high"
    go_skill_reasons="${go_skill_reasons} more-than-8-go-files;"
fi
if [[ "$go_skill_concurrency_files" -gt 0 ]]; then
    go_skill_complexity="high"
    go_skill_reasons="${go_skill_reasons} concurrency;"
fi
if [[ "$go_skill_error_sites" -gt 20 ]]; then
    go_skill_complexity="high"
    go_skill_reasons="${go_skill_reasons} more-than-20-error-sites;"
fi

go_skill_reasons="${go_skill_reasons# }"
go_skill_reasons="${go_skill_reasons%;}"
if [[ -z "$go_skill_reasons" ]]; then
    go_skill_reasons="none"
fi

echo "COMPLEXITY=$go_skill_complexity"
echo "BASE_REF=$go_skill_base_ref"
echo "PLAN_LINES=$go_skill_plan_lines"
echo "CHANGED_GO_FILES=$go_skill_file_count"
echo "CONCURRENCY_FILES=$go_skill_concurrency_files"
echo "ERROR_SITES=$go_skill_error_sites"
echo "REASONS=$go_skill_reasons"
