---
description: Validate Claude Code configuration - check cross-references, skill existence, and frontmatter integrity
---

Run the configuration validator and present findings.

## Steps

1. Run the validator script against the Claude Code config root:

```bash
python3 ~/.claude/bin/validate-config.py --root .
```

If the working directory is not the `.claude/` root, adjust `--root` accordingly (e.g. `--root ~/.claude` or `--root roles/devbox/files/.claude`).

2. If the script reports **errors**, investigate each one:
   - `[SKILL_REF]` — agent references a skill that doesn't exist; check for typos or missing skill directories
   - `[AGENT_FIELD]` / `[SKILL_FIELD]` / `[CMD_FIELD]` — missing required frontmatter field
   - `[AGENT_MODEL]` — invalid model value (must be sonnet/opus/haiku)
   - `[JSON_INVALID]` — malformed JSON file
   - `[DOC_REF]` — broken markdown link in an agent file
   - `[GROUNDING]` — builder skill missing grounding reference file
   - `[META_PIPELINE]` — meta-reviewer or builder skill wiring issue
   - `[SKILL_FRONTMATTER]` / `[AGENT_FRONTMATTER]` / `[CMD_FRONTMATTER]` — missing or malformed `---` block

3. If the script reports **warnings**, note them:
   - `[SKILL_NAME_MISMATCH]` — skill `name` field doesn't match directory name
   - `[STALE]` — old-style doc reference pattern detected

4. Present the full report to the user. If errors exist, suggest specific fixes.

## Advanced Usage

```bash
# Run only specific checks
python3 ~/.claude/bin/validate-config.py --root . --check agents,skills

# Machine-readable output
python3 ~/.claude/bin/validate-config.py --root . --json
```

Available checks: `agents`, `skills`, `commands`, `json`, `references`, `stale`, `grounding`, `meta-pipeline`.
