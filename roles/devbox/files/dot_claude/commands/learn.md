---
description: Extract a reusable pattern from the current session into a learned skill
---

You are extracting a valuable pattern from the current session and saving it as a reusable skill.

## When to Use

Run `/learn` after you've solved a non-trivial problem. Good candidates:

- **Error resolution patterns** — error → root cause → fix (especially non-obvious ones)
- **Debugging techniques** — steps that weren't immediately obvious
- **Workarounds** — library quirks, API limitations, platform-specific issues
- **Project conventions** — architecture decisions, naming patterns, tool usage
- **Performance insights** — optimisation techniques discovered during profiling

**Not worth learning:**
- Trivial fixes (typos, obvious syntax errors)
- One-time issues (service outage, transient failures)
- Well-documented patterns (already in existing skills)

## Steps

### 1. Identify the Pattern

Review the current conversation and identify the most valuable insight. Ask yourself:
- "Would this save time if I encountered it again?"
- "Is this specific enough to be actionable?"
- "Is this general enough to apply across projects?"

If nothing stands out, tell the user:

> No strong patterns to extract from this session. `/learn` works best after solving non-obvious problems.

### 2. Draft the Skill

Generate a label (kebab-case, descriptive): e.g. `sqlc-enum-handling`, `vite-hmr-docker-fix`, `pytest-fixture-scope-gotcha`

Draft the skill content:

```markdown
# {Descriptive Pattern Name}
**Extracted**: {YYYY-MM-DD}
**Context**: {When this pattern applies — 1 line}

## Problem
{What went wrong or was difficult — 2-3 sentences}

## Solution
{The key insight and how to fix it — be specific and actionable}

## Example
{Minimal code example or command showing the fix}

## When to Use
{Trigger conditions — when should Claude apply this pattern}

## When NOT to Use
{Exclusions — avoid false positives}
```

### 3. Confirm with User

Present the draft to the user:

```markdown
> **Pattern extracted**: {name}
>
> {1-line summary of what it captures}
>
> Save to `~/.claude/skills/learned/{label}.md`?
```

**Wait for explicit approval.** Do not save without it.

### 4. Save the Skill

After user approves:

```bash
mkdir -p ~/.claude/skills/learned
```

Write the skill file using the Write tool to `~/.claude/skills/learned/{label}.md`.

**Do NOT add YAML frontmatter** — learned skills are lightweight knowledge snippets, not full skill modules. They're picked up by file scanning, not the skill registry.

### 5. Confirm

```markdown
> Pattern **{name}** saved to `~/.claude/skills/learned/{label}.md`.
>
> It will be available in future sessions when Claude scans the learned skills directory.
```

## Managing Learned Skills

Users can:
- Read/edit skills directly in `~/.claude/skills/learned/`
- Delete skills that are no longer useful
- Promote a learned skill to a full skill module via `/build-skill`
