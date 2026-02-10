---
description: Create or validate an agent definition using the Agent Builder agent
---

You are orchestrating the Agent Builder to create, validate, or refine an agent definition.

## Parse Arguments

Check what the user requested:
- `/build-agent <name>` → Create a new agent with this name
- `/build-agent validate <name>` → Validate an existing agent
- `/build-agent validate all` → Validate all agents
- `/build-agent refine <name>` → Refine an existing agent
- `/build-agent self-improve` → Agent Builder analyses and improves itself
- `/build-agent` (no args) → Ask user what they want to build

## Steps

### 1. Determine Mode

From the arguments, determine the mode:
- **Create**: User wants a new agent
- **Validate**: User wants to check existing agent(s)
- **Refine**: User wants to improve an existing agent
- **Self-improve**: Agent Builder improves its own definition

### 2. Run Agent Builder

Invoke the `agent-builder` agent with the appropriate prompt:

**For Create mode:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Create a new agent definition for: <name>. User context: <any additional details from conversation>. Read existing agents of the same archetype for pattern reference before drafting."
)
```

**For Validate mode (single):**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Validate the agent definition at .claude/agents/<name>.md. Run the full validation protocol and report findings."
)
```

**For Validate mode (all):**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Validate ALL agent definitions under .claude/agents/. Run the full validation protocol for each and produce a consolidated report."
)
```

**For Refine mode:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Refine the agent definition at .claude/agents/<name>.md. Read the current definition, identify improvements, apply changes with rationale."
)
```

**For Self-improve mode:**
```
Task(
  subagent_type: "agent-builder",
  model: "opus",
  prompt: "Self-improvement mode. Read your own definition at .claude/agents/agent_builder.md and your skill at .claude/skills/agent-builder/SKILL.md. Evaluate against current best practices (use WebSearch for latest Anthropic guidance). Propose improvements — present as options, do not modify without approval."
)
```

### 3. Handle Skill Gaps

If the Agent Builder reports new skills are needed:

1. Present the list to the user:
   ```
   The new agent needs these skills that don't exist yet:
   - `<skill-1>`: <description>
   - `<skill-2>`: <description>

   Run `/build-skill <name>` for each, or say 'skip' to proceed without them.
   ```

2. Wait for user decision before proceeding.

### 4. After Completion

Present the Agent Builder's output to the user. If a new agent was created, suggest:

```
Agent created. Recommended next steps:
1. Review the definition at .claude/agents/<name>.md
2. Create any missing skills with `/build-skill`
3. Run `/validate-config` to verify system integrity
```
