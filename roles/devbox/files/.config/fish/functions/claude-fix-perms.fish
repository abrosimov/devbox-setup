function claude-fix-perms --description "Inject default permissions (mode, allow, deny) into .claude/settings.local.json"
    set -l file .claude/settings.local.json

    if not test -f $file
        echo "No $file found — nothing to fix"
        return 0
    end

    if jq -e '.permissions.allow' $file >/dev/null 2>&1
        echo "Permissions already configured in $file"
        jq -r '.permissions.defaultMode // "not set"' $file | read -l mode
        echo "  defaultMode: $mode"
        jq '.permissions.allow | length' $file | read -l allow_count
        jq '.permissions.deny | length' $file | read -l deny_count
        echo "  allow rules: $allow_count, deny rules: $deny_count"
        return 0
    end

    set -l perms '{
  "defaultMode": "acceptEdits",
  "deny": [
    "Bash(rm *)",
    "Bash(rm -*)",
    "Bash(curl *)",
    "Bash(wget *)",
    "Bash(sudo *)",
    "Bash(git commit *)",
    "Bash(git push *)",
    "Bash(git rebase *)",
    "Bash(git reset *)",
    "Bash(git merge *)",
    "Bash(git tag *)",
    "Bash(git rm *)",
    "Bash(git mv *)",
    "Bash(git clean *)",
    "Bash(git checkout -- *)",
    "Bash(cat *>*)",
    "Bash(echo *>*)",
    "Bash(kill *)",
    "Bash(killall *)",
    "Bash(docker rm *)",
    "Bash(docker rmi *)",
    "Bash(pip uninstall *)",
    "Bash(gh pr close *)",
    "Bash(gh pr merge *)",
    "Bash(gh issue close *)",
    "Edit(.env)",
    "Edit(.env.*)",
    "Edit(**/.env)",
    "Edit(**/.env.*)",
    "Edit(**/secrets/**)",
    "Edit(**/*.pem)",
    "Edit(**/*.key)",
    "Edit(**/credentials*)",
    "Write(.env)",
    "Write(.env.*)",
    "Write(**/.env)",
    "Write(**/.env.*)",
    "Write(**/secrets/**)",
    "Write(**/*.pem)",
    "Write(**/*.key)",
    "Write(**/credentials*)"
  ],
  "allow": [
    "Task",
    "Read",
    "Read(**)",
    "Edit",
    "Edit(**)",
    "Write",
    "Write(**)",
    "NotebookEdit",
    "WebSearch",
    "WebFetch",
    "mcp__*",
    "Bash(go test *)",
    "Bash(go build *)",
    "Bash(go run *)",
    "Bash(go mod *)",
    "Bash(go vet *)",
    "Bash(goimports *)",
    "Bash(golangci-lint *)",
    "Bash(mockery *)",
    "Bash(uv run *)",
    "Bash(uv sync *)",
    "Bash(uvx *)",
    "Bash(poetry run *)",
    "Bash(pytest *)",
    "Bash(ruff *)",
    "Bash(black *)",
    "Bash(mypy *)",
    "Bash(python *)",
    "Bash(python3 *)",
    "Bash(pip install *)",
    "Bash(pip list *)",
    "Bash(pnpm *)",
    "Bash(npx *)",
    "Bash(node *)",
    "Bash(jsonnet *)",
    "Bash(jsonnetfmt *)",
    "Bash(jb *)",
    "Bash(buf *)",
    "Bash(make *)",
    "Bash(docker build *)",
    "Bash(docker run *)",
    "Bash(docker compose *)",
    "Bash(docker ps *)",
    "Bash(docker images *)",
    "Bash(docker logs *)",
    "Bash(gh pr view *)",
    "Bash(gh pr list *)",
    "Bash(gh pr diff *)",
    "Bash(gh pr checks *)",
    "Bash(gh issue view *)",
    "Bash(gh issue list *)",
    "Bash(gh api *)",
    "Bash(gh run *)",
    "Bash(git status *)",
    "Bash(git status)",
    "Bash(git diff *)",
    "Bash(git diff)",
    "Bash(git log *)",
    "Bash(git show *)",
    "Bash(git branch *)",
    "Bash(git branch)",
    "Bash(git blame *)",
    "Bash(git ls-files *)",
    "Bash(git ls-files)",
    "Bash(git ls-tree *)",
    "Bash(git rev-parse *)",
    "Bash(git stash *)",
    "Bash(git checkout -b *)",
    "Bash(git switch *)",
    "Bash(git remote *)",
    "Bash(git fetch *)",
    "Bash(git config --get *)",
    "Bash(.claude/bin/*)",
    "Bash(ls *)",
    "Bash(ls)",
    "Bash(test *)",
    "Bash([ -f *)",
    "Bash([ -d *)",
    "Bash(mkdir *)",
    "Bash(wc *)",
    "Bash(stat *)",
    "Bash(file *)",
    "Bash(jq *)",
    "Bash(which *)",
    "Bash(pwd)",
    "Bash(head *)",
    "Bash(tail *)",
    "Bash(diff *)",
    "Bash(sort *)",
    "Bash(uniq *)",
    "Bash(cut *)",
    "Bash(tr *)",
    "Bash(awk *)",
    "Bash(sed *)",
    "Bash(xargs *)",
    "Bash(tee *)",
    "Bash(env *)",
    "Bash(date *)",
    "Bash(basename *)",
    "Bash(dirname *)"
  ]
}'

    jq --argjson perms "$perms" '.permissions = $perms' $file >$file.tmp
    and mv $file.tmp $file
    and begin
        jq '.permissions.allow | length' $file | read -l allow_count
        jq '.permissions.deny | length' $file | read -l deny_count
        echo "Injected default permissions into $file"
        echo "  defaultMode: acceptEdits"
        echo "  allow rules: $allow_count, deny rules: $deny_count"
    end
    or begin
        rm -f $file.tmp
        echo "Failed to update $file"
        return 1
    end
end
