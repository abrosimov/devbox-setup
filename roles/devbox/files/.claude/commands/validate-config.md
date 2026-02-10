---
description: Validate Claude Code configuration - check cross-references, skill existence, and frontmatter integrity
---

You are a configuration validator for the Claude Code agent system. Run all checks and report findings.

## Steps

### 1. Inventory All Components

Scan the `.claude/` directory structure:

```bash
# List all agents
ls .claude/agents/*.md 2>/dev/null | grep -v _archived

# List all skill directories
ls -d .claude/skills/*/

# List all commands
ls .claude/commands/*.md

# List all docs
find .claude/docs -name '*.md' 2>/dev/null
```

### 2. Validate Agent Frontmatter

For each agent file, verify:

- [ ] Has valid `---` delimited frontmatter
- [ ] Has `name` field
- [ ] Has `description` field
- [ ] Has `tools` field
- [ ] Has `model` field (sonnet or opus)
- [ ] Has `skills` field
- [ ] If code-writing agent: has `permissionMode: acceptEdits`

### 3. Cross-Reference Check: Skills

For each agent's `skills:` list, verify every referenced skill exists as a directory under `.claude/skills/` with a valid `SKILL.md`:

```bash
# Extract skill names from agent frontmatter and check each exists
for agent in .claude/agents/*.md; do
  grep '^skills:' "$agent" | sed 's/skills: //' | tr ',' '\n' | tr -d ' ' | while read skill; do
    # Check by directory name first
    if [ ! -f ".claude/skills/$skill/SKILL.md" ]; then
      # Check by SKILL.md name field
      found=$(grep -rl "^name: $skill$" .claude/skills/*/SKILL.md 2>/dev/null)
      if [ -z "$found" ]; then
        echo "BROKEN: $agent references skill '$skill' — not found"
      fi
    fi
  done
done
```

### 4. Cross-Reference Check: Doc Paths

Search for doc references in agent bodies that point to non-existent files:

```bash
# Find references to docs/ paths
grep -rn 'docs/' .claude/agents/*.md | grep -v '_archived' | while read line; do
  path=$(echo "$line" | grep -oP 'docs/[a-zA-Z0-9_/.-]+\.md')
  if [ -n "$path" ] && [ ! -f ".claude/$path" ]; then
    echo "BROKEN DOC REF: $line"
  fi
done
```

### 5. Cross-Reference Check: Stale Patterns

Search for known stale reference patterns:

```bash
# Old-style doc references (pre-skill migration)
grep -rn 'go/go_' .claude/agents/*.md | grep -v _archived
grep -rn 'python/python_' .claude/agents/*.md | grep -v _archived

# Double-backtick formatting issues
grep -rn '``' .claude/agents/*.md | grep -v _archived
```

### 6. Skill Frontmatter Validation

For each skill, verify:

- [ ] Has valid `---` delimited frontmatter
- [ ] Has `name` field
- [ ] `name` field matches directory name (flag mismatches as warnings)
- [ ] Has `description` field

### 7. Command Frontmatter Validation

For each command, verify:

- [ ] Has valid `---` delimited frontmatter
- [ ] Has `description` field

### 8. Report

Present findings in this format:

```
## Configuration Validation Report

### Errors (must fix)
- [ ] [BROKEN SKILL REF] agent.md references 'skill-name' — skill not found
- [ ] [BROKEN DOC REF] agent.md:42 references 'docs/path.md' — file not found
- [ ] [MISSING FRONTMATTER] agent.md missing required field 'name'

### Warnings (should fix)
- [ ] [NAME MISMATCH] skills/shared/ has name: shared-utils (directory ≠ name)
- [ ] [STALE PATTERN] agent.md:55 uses old-style doc reference
- [ ] [FORMATTING] agent.md:23 has double-backtick issue

### Summary
- Agents checked: N
- Skills checked: N
- Commands checked: N
- Errors: N
- Warnings: N
```
