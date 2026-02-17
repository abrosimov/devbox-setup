---
description: Create or validate an agent definition using the Agent Builder agent, with adversarial meta-review
---

You are orchestrating a **3-gate pipeline** for agent definition creation, validation, or refinement.

## Parse Arguments

Check what the user requested:
- `/build-agent <name>` → Create a new agent with this name
- `/build-agent validate <name>` → Validate an existing agent
- `/build-agent validate all` → Validate all agents
- `/build-agent refine <name>` → Refine an existing agent
- `/build-agent self-improve` → Agent Builder analyses and improves itself
- `/build-agent` (no args) → Ask user what they want to build

## Pipeline Overview

<pipeline>

### Create / Refine Mode (3-gate)

1. **Builder** → produces agent definition + self-validation + XML artifact block
2. **GATE 1** → user reviews builder output
3. **Meta-Reviewer** → adversarial challenge against grounded docs
4. **GATE 2** → user approves structural review (say `skip-content` to bypass Gate 3)
5. **Content Reviewer** → substance audit (code examples, versions, security, redundancy)
6. **GATE 3** → user approves final artifact

### Validate Mode (single pass)

1. **Builder** → runs validation protocol, reports findings
2. Present findings to user (no meta-review needed for validation-only)

### Self-Improve Mode (single pass)

1. **Builder** → analyses own definition, proposes improvements
2. Present proposals to user (meta-review after user approves changes)

</pipeline>

## Steps

### 1. Determine Mode

From the arguments, determine the mode:
- **Create**: User wants a new agent → 2-gate pipeline
- **Validate**: User wants to check existing agent(s) → single pass
- **Refine**: User wants to improve an existing agent → 2-gate pipeline
- **Self-improve**: Agent Builder improves its own definition → single pass

### 2. Run Agent Builder (Gate 1)

**For Create mode:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Create a new agent definition for: <name>. User context: <any additional details from conversation>.

Phase 0: Read grounding references first:
- skills/agent-builder/references/anthropic-agent-authoring.md
- skills/agent-builder/references/anthropic-prompt-engineering.md

Then: Read existing agents of the same archetype for pattern reference before drafting. Auto-fix Tier 1 issues. Emit the XML artifact block in your output for meta-review handoff."
)
```

**For Validate mode (single):**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Validate the agent definition at .claude/agents/<name>.md.

Phase 0: Read grounding references first:
- skills/agent-builder/references/anthropic-agent-authoring.md
- skills/agent-builder/references/anthropic-prompt-engineering.md

Run the full validation protocol and report findings."
)
```

**For Validate mode (all):**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Validate ALL agent definitions under .claude/agents/. Phase 0: Read grounding references first. Run the full validation protocol for each and produce a consolidated report."
)
```

**For Refine mode:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Refine the agent definition at .claude/agents/<name>.md. User context: <any feedback>.

Phase 0: Read grounding references first:
- skills/agent-builder/references/anthropic-agent-authoring.md
- skills/agent-builder/references/anthropic-prompt-engineering.md

Read the current definition, identify improvements, apply changes with rationale. Auto-fix Tier 1 issues. Emit the XML artifact block for meta-review handoff."
)
```

**For Self-improve mode:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Self-improvement mode. Read your own definition at .claude/agents/agent_builder.md and your skill at .claude/skills/agent-builder/SKILL.md. Read grounding references to check for drift. Propose improvements — present as options, do not modify without approval."
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
  prompt: "Review the agent definition at .claude/agents/<name>.md.

This artifact was produced by the Agent Builder. Run the full adversarial review protocol:
1. Ground yourself: Read skills/agent-builder/references/anthropic-agent-authoring.md and skills/agent-builder/references/anthropic-prompt-engineering.md
2. Structural challenge: Check frontmatter against Anthropic spec
3. Discoverability challenge: Simulate positive/negative/confusion triggers
4. Contradiction check: Cross-reference with existing agents and skills
5. Boundary stress test: Test stop conditions and scope
6. Prompt quality assessment: Evaluate body as system prompt

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

**[Awaiting your decision]** — Say **'continue'** to run content review, **'fix'** to send back to builder, **'skip-content'** to accept without content review, or provide specific instructions.
```

If user says 'skip-content', skip to step 6.
If user says 'fix', re-run builder with feedback.
If user says 'continue', proceed to step 5.

### 5. Run Content Reviewer (Gate 3)

```
Task(
  subagent_type: "content-reviewer",
  model: "opus",
  prompt: "Review the content substance of the agent definition at .claude/agents/<name>.md.

This artifact has passed structural meta-review. Now audit its content:
1. Collect context: Read the artifact and 2-3 referenced skills
2. Code example review: Verify syntax, API correctness, cross-skill compliance
3. External freshness check: WebSearch versions, deprecated APIs
4. Security and injection audit: Check examples for insecure patterns
5. Redundancy assessment: Check for duplication with neighbours and base-model filler
6. Completeness check: Verify happy/error/edge paths are covered

Meta-reviewer context:
<meta-review-context>
[Paste key findings from the meta-reviewer's output]
</meta-review-context>

Emit your full XML <audit-findings> report."
)
```

Present the content reviewer's findings:

```markdown
**Gate 3: Content Review**

[Content reviewer's summary and verdict]

**[Awaiting your decision]** — Say **'approve'** to accept, **'fix'** to send back to builder, or provide specific instructions.
```

### 6. Handle Skill Gaps

If the Agent Builder reports new skills are needed:

```markdown
The new agent needs these skills that don't exist yet:
- `<skill-1>`: <description>
- `<skill-2>`: <description>

Run `/build-skill <name>` for each, or say 'skip' to proceed without them.
```

### 7. After Completion

```markdown
Agent pipeline complete. Recommended next steps:
1. Review the definition at .claude/agents/<name>.md
2. Create any missing skills with `/build-skill`
3. Run `/validate-config` to verify system integrity
4. Run `/audit` for library-wide freshness and consistency checks
```
