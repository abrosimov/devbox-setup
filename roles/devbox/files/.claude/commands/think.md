---
description: Structured systems thinking using FPF (First Principles Framework)
---

You are orchestrating an FPF-guided systems thinking session.

## What This Does

Routes complex, non-code problems to the appropriate thinking agent with FPF (First Principles Framework) enabled. The agent uses FPF patterns from `~/.claude/docs/FPF-Spec.md` to structure analysis but responds in **plain language** — no framework jargon.

**Key features:**
- Thoughts are streamed to console for real-time visibility
- Human-readable artifact is persisted (ticket-scoped or cross-cutting)
- Key insights stored in memory for cross-session recall
- Dialogue mode offered after analysis

## Steps

### 1. Parse the User's Problem

The user provides a problem or question as argument: `$ARGUMENTS`

If no argument provided, ask:
> What complex problem would you like to think through?

### 2. Detect Scope

Determine where the artifact should be written:

```bash
# Try to get ticket context
CONTEXT_JSON=$(~/.claude/bin/resolve-context 2>/dev/null) && RC=$? || RC=$?
```

| Condition | Scope | Artifact Path |
|-----------|-------|---------------|
| Problem mentions Jira ticket (e.g., "PROJ-123") | Ticket | `{PROJECT_DIR}/analysis.md` |
| `resolve-context` succeeds (RC=0) and problem relates to current work | Ticket | `{PROJECT_DIR}/analysis.md` |
| Problem is strategic/project-wide, mentions "overall", "strategy", "architecture" | Cross-cutting | `docs/decisions/NNN-<topic>.md` or `docs/design/<topic>.md` |
| Unclear | Ask user | "Is this analysis for the current ticket, or a project-wide decision?" |

### 3. Classify and Route Agent

Based on the problem type, select the most appropriate agent:

| Problem Pattern | Agent | Why |
|---|---|---|
| "What should we build?", requirements, product framing | `technical-product-manager` | Project characterization, requirements as evidence-backed claims |
| "Is this true?", validate assumptions, challenge claims | `domain-expert` | Trust calculus (F-G-R), bias audit, epistemic debt detection |
| "How is this structured?", decompose, model relationships | `domain-modeller` | Holonic decomposition, bounded contexts, role taxonomy |
| "How should we design this?", architecture, trade-offs | `architect` | DRR, cross-scale consistency, evolutionary architecture |
| Mixed / unclear | `domain-expert` | Default: sceptical analysis is safe starting point |

### 4. Spawn the Agent

**IMPORTANT**: Always pass `model: "opus"` explicitly.

```
Task(
  subagent_type: "{selected-agent}",
  model: "opus",
  prompt: "FPF THINKING SESSION

Problem: {user's problem from $ARGUMENTS}

ARTIFACT PATH: {determined in Step 2}
SCOPE: {ticket | cross-cutting}

INSTRUCTIONS:
1. Read the `fpf-thinking` skill for the routing table and protocol
2. Identify which FPF sections are relevant using the routing table
3. Grep `~/.claude/docs/FPF-Spec.md` for those section headers, then Read targeted ranges
4. Use sequential thinking (mcp__sequentialthinking) for multi-step reasoning
5. **STREAM EACH THOUGHT** — after each sequential thinking step, output a summary to console so the user can follow along
6. Apply the FPF patterns to structure your analysis
7. Respond in PLAIN LANGUAGE — no FPF terminology unless the user requests it
8. Produce concrete artifacts (see fpf-thinking skill: Artifact Recipes)
9. Present options as portfolios with trade-offs, not single answers

ARTIFACT GENERATION:
10. After completing analysis, write a human-readable artifact to ARTIFACT PATH
11. Follow the format in fpf-thinking skill: Artifact Persistence section
12. If cross-cutting ADR: ensure docs/decisions/ exists, use next sequential number (NNN)
13. If cross-cutting design: ensure docs/design/ exists

MEMORY INTEGRATION:
14. Store key insights in memory-upstream (see fpf-thinking skill)

Return: { artifact_path: string, summary: string, open_questions: string[] }"
)
```

### 5. Present Results and Offer Dialogue

When the agent returns:

1. Display the summary
2. Show where the artifact was saved
3. Offer refinement options:

> **Analysis complete.** Artifact saved to `{artifact_path}`.
>
> **Summary:** {summary}
>
> **Open questions:**
> {formatted list}
>
> **Next steps:**
> - Say **'refine <section>'** to dig deeper into a specific area
> - Say **'extend'** to continue the analysis
> - Say **'plan it'** to create an implementation plan
> - Say **'model it'** to run domain modeller (if structural decomposition needed)
> - Or ask follow-up questions
