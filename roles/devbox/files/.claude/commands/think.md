---
description: Structured systems thinking using FPF (First Principles Framework)
---

You are orchestrating an FPF-guided systems thinking session.

## What This Does

Routes complex, non-code problems to the appropriate thinking agent with FPF (First Principles Framework) enabled. The agent uses FPF patterns from `~/.claude/docs/FPF-Spec.md` to structure analysis but responds in **plain language** — no framework jargon.

## Steps

### 1. Parse the User's Problem

The user provides a problem or question as argument: `$ARGUMENTS`

If no argument provided, ask:
> What complex problem would you like to think through?

### 2. Classify and Route

Based on the problem type, select the most appropriate agent:

| Problem Pattern | Agent | Why |
|---|---|---|
| "What should we build?", requirements, product framing | `technical-product-manager` | Project characterization, requirements as evidence-backed claims |
| "Is this true?", validate assumptions, challenge claims | `domain-expert` | Trust calculus (F-G-R), bias audit, epistemic debt detection |
| "How is this structured?", decompose, model relationships | `domain-modeller` | Holonic decomposition, bounded contexts, role taxonomy |
| "How should we design this?", architecture, trade-offs | `architect` | DRR, cross-scale consistency, evolutionary architecture |
| Mixed / unclear | `domain-expert` | Default: sceptical analysis is safe starting point |

### 3. Spawn the Agent

**IMPORTANT**: Always pass `model: "opus"` explicitly.

```
Task(
  subagent_type: "{selected-agent}",
  model: "opus",
  prompt: "FPF THINKING SESSION

Problem: {user's problem from $ARGUMENTS}

INSTRUCTIONS:
1. Read the `fpf-thinking` skill for the routing table and protocol
2. Identify which FPF sections are relevant using the routing table
3. Grep `~/.claude/docs/FPF-Spec.md` for those section headers, then Read targeted ranges
4. Apply the FPF patterns to structure your analysis
5. Respond in PLAIN LANGUAGE — no FPF terminology unless the user requests it
6. Produce concrete artifacts (see fpf-thinking skill: Artifact Recipes)
7. Present options as portfolios with trade-offs, not single answers

Use sequential thinking (mcp__sequentialthinking) for multi-step reasoning."
)
```

### 4. Present Results

When the agent returns, present its analysis to the user. If the analysis suggests follow-up in a different domain (e.g., domain expert recommends modelling), suggest the next agent:

> Analysis complete. The domain expert suggests the system structure needs formal decomposition.
>
> Say **'model it'** to run domain modeller, or ask follow-up questions.
