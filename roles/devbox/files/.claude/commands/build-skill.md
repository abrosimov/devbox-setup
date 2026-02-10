---
description: Create or validate a skill module using the Skill Builder agent
---

You are orchestrating the Skill Builder to create, validate, refine, or audit skill modules.

## Parse Arguments

Check what the user requested:
- `/build-skill <name>` → Create a new skill with this name
- `/build-skill validate <name>` → Validate an existing skill
- `/build-skill validate all` → Validate all skills
- `/build-skill refine <name>` → Refine an existing skill
- `/build-skill audit` → Full library audit (overlaps, gaps, terminology)
- `/build-skill self-improve` → Skill Builder analyses and improves itself
- `/build-skill` (no args) → Ask user what they want to build

## Steps

### 1. Determine Mode

From the arguments, determine the mode:
- **Create**: User wants a new skill
- **Validate**: User wants to check existing skill(s)
- **Refine**: User wants to improve an existing skill
- **Audit**: Full library audit
- **Self-improve**: Skill Builder improves its own definition

### 2. Run Skill Builder

Invoke the `skill-builder` agent with the appropriate prompt:

**For Create mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Create a new skill module for: <name>. User context: <any additional details from conversation>. Audit existing related skills for terminology and boundary consistency before drafting."
)
```

**For Validate mode (single):**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Validate the skill at .claude/skills/<name>/SKILL.md. Run the full validation protocol and report findings."
)
```

**For Validate mode (all):**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Validate ALL skills under .claude/skills/. Run the full validation protocol for each and produce a consolidated report."
)
```

**For Refine mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Refine the skill at .claude/skills/<name>/SKILL.md. Read the current definition, identify improvements (token efficiency, description quality, progressive disclosure), apply changes with rationale."
)
```

**For Audit mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Full library audit. Inventory all skills under .claude/skills/. Check for: overlaps between skills, gaps (domains referenced by agents but not covered), terminology conflicts, orphaned skills (not referenced by any agent). Produce a comprehensive audit report."
)
```

**For Self-improve mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Self-improvement mode. Read your own agent definition at .claude/agents/skill_builder.md and your skill at .claude/skills/skill-builder/SKILL.md. Evaluate against current best practices (use WebSearch for latest Anthropic guidance on skill authoring). Propose improvements — present as options, do not modify without approval."
)
```

### 3. After Completion

Present the Skill Builder's output to the user.

**For new skills:**
```
Skill created. Recommended next steps:
1. Review the skill at .claude/skills/<name>/SKILL.md
2. Add this skill to relevant agents' `skills:` field
3. Run `/validate-config` to verify system integrity
```

**For audits:**
```
Audit complete. Review the findings and decide which to address.
Use `/build-skill refine <name>` to improve specific skills.
```
