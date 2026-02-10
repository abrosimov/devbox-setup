---
description: Create or validate a skill module using the Skill Builder agent, with adversarial meta-review
---

You are orchestrating a **2-gate pipeline** for skill module creation, validation, refinement, or audit.

## Parse Arguments

Check what the user requested:
- `/build-skill <name>` → Create a new skill with this name
- `/build-skill validate <name>` → Validate an existing skill
- `/build-skill validate all` → Validate all skills
- `/build-skill refine <name>` → Refine an existing skill
- `/build-skill audit` → Full library audit (overlaps, gaps, terminology)
- `/build-skill self-improve` → Skill Builder analyses and improves itself
- `/build-skill` (no args) → Ask user what they want to build

## Pipeline Overview

<pipeline>

### Create / Refine Mode (2-gate)

1. **Builder** → produces skill definition + self-validation + XML artifact block
2. **GATE 1** → user reviews builder output
3. **Meta-Reviewer** → adversarial challenge against grounded docs
4. **GATE 2** → user approves final artifact

### Validate / Audit Mode (single pass)

1. **Builder** → runs validation/audit protocol, reports findings
2. Present findings to user (no meta-review needed)

### Self-Improve Mode (single pass)

1. **Builder** → analyses own definition, proposes improvements
2. Present proposals to user

</pipeline>

## Steps

### 1. Determine Mode

From the arguments, determine the mode:
- **Create**: User wants a new skill → 2-gate pipeline
- **Validate**: User wants to check existing skill(s) → single pass
- **Refine**: User wants to improve an existing skill → 2-gate pipeline
- **Audit**: Full library audit → single pass
- **Self-improve**: Skill Builder improves its own definition → single pass

### 2. Run Skill Builder (Gate 1)

**For Create mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Create a new skill module for: <name>. User context: <any additional details from conversation>.

Phase 0: Read grounding reference first:
- skills/skill-builder/references/anthropic-skill-authoring.md

Then: Audit existing related skills for terminology and boundary consistency before drafting. Auto-fix Tier 1 issues. Emit the XML artifact block in your output for meta-review handoff."
)
```

**For Validate mode (single):**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Validate the skill at .claude/skills/<name>/SKILL.md.

Phase 0: Read grounding reference first:
- skills/skill-builder/references/anthropic-skill-authoring.md

Run the full validation protocol and report findings."
)
```

**For Validate mode (all):**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Validate ALL skills under .claude/skills/. Phase 0: Read grounding reference first. Run the full validation protocol for each and produce a consolidated report."
)
```

**For Refine mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Refine the skill at .claude/skills/<name>/SKILL.md. User context: <any feedback>.

Phase 0: Read grounding reference first:
- skills/skill-builder/references/anthropic-skill-authoring.md

Read the current definition, identify improvements, apply changes with rationale. Auto-fix Tier 1 issues. Emit the XML artifact block for meta-review handoff."
)
```

**For Audit mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Full library audit. Phase 0: Read grounding reference first. Inventory all skills under .claude/skills/. Check for: overlaps between skills, gaps (domains referenced by agents but not covered), terminology conflicts, orphaned skills (not referenced by any agent). Produce a comprehensive audit report."
)
```

**For Self-improve mode:**
```
Task(
  subagent_type: "skill-builder",
  model: "opus",
  prompt: "Self-improvement mode. Read your own agent definition at .claude/agents/skill_builder.md and your skill at .claude/skills/skill-builder/SKILL.md. Read grounding reference to check for drift. Propose improvements — present as options, do not modify without approval."
)
```

### 3. Gate 1: User Review

For create/refine modes, present the builder's output to the user:

```markdown
**Gate 1: Builder Output**

[Builder's summary and XML artifact block]

**[Awaiting your decision]** — Say **'continue'** to run meta-review, **'fix <instruction>'** to adjust, or **'skip-review'** to accept without meta-review.
```

If user says 'skip-review', skip to step 5.
If user says 'fix', re-run builder with feedback.
If user says 'continue', proceed to step 4.

### 4. Run Meta-Reviewer (Gate 2)

```
Task(
  subagent_type: "meta-reviewer",
  model: "opus",
  prompt: "Review the skill at .claude/skills/<name>/SKILL.md.

This artifact was produced by the Skill Builder. Run the full adversarial review protocol:
1. Ground yourself: Read skills/skill-builder/references/anthropic-skill-authoring.md
2. Structural challenge: Check frontmatter against Anthropic spec
3. Discoverability challenge: Simulate positive/negative/confusion triggers
4. Contradiction check: Cross-reference with existing skills and agents
5. Boundary stress test: Test scope and overlap
6. Progressive disclosure assessment: Is the 80/20 split correct?

Builder's self-assessment:
<builder-context>
[Paste the XML artifact block from the builder's output]
</builder-context>

Emit your full XML meta-review report."
)
```

Present the meta-reviewer's findings:

```markdown
**Gate 2: Meta-Review**

[Meta-reviewer's summary and verdict]

**[Awaiting your decision]** — Say **'approve'** to accept, **'fix'** to send back to builder, or provide specific instructions.
```

### 5. After Completion

**For new/refined skills:**
```markdown
Skill pipeline complete. Recommended next steps:
1. Review the skill at .claude/skills/<name>/SKILL.md
2. Add this skill to relevant agents' `skills:` field
3. Run `/validate-config` to verify system integrity
```

**For audits:**
```markdown
Audit complete. Review the findings and decide which to address.
Use `/build-skill refine <name>` to improve specific skills.
```
