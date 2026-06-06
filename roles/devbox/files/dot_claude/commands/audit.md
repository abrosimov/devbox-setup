---
description: Run library-wide audit of agent and skill definitions (freshness, consistency, or both)
---

You are orchestrating a **library-wide audit** of all agent and skill definitions.

## Parse Arguments

Check what the user requested:
- `/audit` → Run both freshness and consistency audits in parallel, merge reports
- `/audit freshness` → Freshness auditor only (external staleness)
- `/audit consistency` → Consistency checker only (internal coherence)
- `/audit fix` → Run both audits, then route findings to builders for remediation

## Steps

### 1. Determine Mode

From the arguments, determine the mode:
- **Full**: Both auditors in parallel → merged report
- **Freshness**: Freshness auditor only
- **Consistency**: Consistency checker only
- **Fix**: Both auditors → merge → route to builders

### 2. Run Auditors

**Full or Fix mode — parallel execution:**

Launch both auditors simultaneously:

```
Task(
  subagent_type: "freshness-auditor",
  model: "sonnet",
  prompt: "Run a full library-wide freshness audit.

Scan all agents under .claude/agents/ and all skills under .claude/skills/.
Follow your complete 7-phase audit protocol:
1. Inventory all artifacts with updated: dates
2. Library version audit (grep versions, WebSearch current)
3. Language version sync (Go, Python, TypeScript)
4. Deprecation scanner (check API calls in examples)
5. Best practice drift (compare against official guides)
6. Anthropic SDK freshness
7. Staleness scoring (sort by risk)

Emit your full XML <audit-findings> report."
)
```

```
Task(
  subagent_type: "consistency-checker",
  model: "sonnet",
  prompt: "Run a full library-wide consistency audit.

Scan all agents under .claude/agents/, skills under .claude/skills/, and commands under .claude/commands/.
Follow your complete 9-phase audit protocol:
1. Inventory and index (build component graph)
2. Terminology enforcement (per domain cluster)
3. Handoff chain integrity (trace every pipeline edge)
4. Engineer-reviewer alignment (per language)
5. Skill gap analysis
6. Orphaned content detection
7. Coverage map (per-language matrix)
8. Duplication finder
9. Progressive disclosure audit

Emit your full XML <audit-findings> report."
)
```

**Freshness mode — single auditor:**

Launch only the freshness auditor (same prompt as above).

**Consistency mode — single auditor:**

Launch only the consistency checker (same prompt as above).

### 3. Merge Reports

For full and fix modes, combine both XML reports into a merged summary:

```markdown
## Library Audit Report

### Freshness Audit
[Freshness auditor's summary and verdict]

### Consistency Audit
[Consistency checker's summary and verdict]

### Combined Findings
**Critical**: {N freshness} + {N consistency} = {N total}
**Important**: {N freshness} + {N consistency} = {N total}
**Suggestions**: {N freshness} + {N consistency} = {N total}

### Staleness Report (from Freshness Auditor)
[Top 10 highest-risk artifacts]

### Coverage Map (from Consistency Checker)
[Per-language chain completeness matrix]
```

### 4. Fix Mode — Route to Builders

If mode is **fix**, process findings after merging:

<fix-routing>

**Sort findings by target path, then by severity (critical first).**

For each artifact with findings:

1. **Batch all findings for that artifact** into a single `<audit-context>` block
2. **Route based on path**:
   - `agents/*.md` → Agent Builder (refine mode)
   - `skills/*/SKILL.md` → Skill Builder (refine mode)
   - `commands/*.md` → Present to user (no auto-builder for commands)
3. **Process critical-severity artifacts first**

**Agent fix:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Refine the agent definition at .claude/agents/<name>.md based on audit findings.

Phase 0: Read grounding references first:
- skills/agent-builder/references/anthropic-agent-authoring.md
- skills/agent-builder/references/anthropic-prompt-engineering.md

<audit-context>
[All findings for this artifact from both auditors]
</audit-context>

Address each finding. Auto-fix Tier 1 issues. Present Tier 2+ changes for approval."
)
```

**Skill fix:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Refine the skill at .claude/skills/<name>/SKILL.md based on audit findings.

Phase 0: Read grounding reference first:
- skills/skill-builder/references/anthropic-skill-authoring.md

<audit-context>
[All findings for this artifact from both auditors]
</audit-context>

Address each finding. Auto-fix Tier 1 issues. Present Tier 2+ changes for approval."
)
```

**Command findings:**
```markdown
The following command files have audit findings that require manual attention:

- `commands/<name>.md`:
  - {finding 1}
  - {finding 2}

Commands do not have an auto-builder. Please review and edit manually.
```

**Gate each fix**: Present the builder's output to the user before proceeding to the next artifact.

```markdown
**Fix applied to** `{artifact path}`

[Builder's summary of changes]

**[Awaiting your decision]** — Say **'continue'** to fix next artifact, **'skip'** to skip this one, or **'stop'** to end fix mode.
```

</fix-routing>

### 5. After Completion

**For full/freshness/consistency modes:**
```markdown
Audit complete.

**Freshness**: {verdict} ({N critical}, {N important}, {N suggestions})
**Consistency**: {verdict} ({N critical}, {N important}, {N suggestions})

To fix findings automatically: `/audit fix`
To fix specific artifacts: `/build-agent refine <name>` or `/build-skill refine <name>`
To verify after fixes: `/validate-config`
```

**For fix mode:**
```markdown
Audit fix cycle complete.

**Artifacts processed**: {N}
**Findings addressed**: {N critical}, {N important}
**Skipped**: {N}

Recommended: Run `/validate-config` to verify system integrity after changes.
```
