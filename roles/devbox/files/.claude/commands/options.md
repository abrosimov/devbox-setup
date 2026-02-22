---
description: Generate diverse solution options using DSS (Diverge-Synthesize-Select) protocol
---

You are orchestrating a DSS (Diverge-Synthesize-Select) session for structured option generation.

## What This Does

Routes design problems to the appropriate thinking agent with the DSS protocol enabled. The agent generates genuinely diverse alternatives along orthogonal strategy axes, evaluates them, attempts synthesis, and presents structured choices.

## Steps

### 1. Parse the User's Problem

The user provides a problem or question as argument: `$ARGUMENTS`

If no argument provided, ask:
> What design problem would you like to explore options for?

### 2. Resolve Context

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context 2>/dev/null) && RC=$? || RC=$?
```

Extract `JIRA_ISSUE`, `BRANCH_NAME`, and `PROJECT_DIR` from the context. Use `config` skill paths for artifact placement.

### 3. Check for Existing Docs

Read any existing upstream artifacts to provide context to the agent:

| File | Purpose |
|------|---------|
| `spec.md` | Product specification |
| `domain_analysis.md` | Domain analysis |
| `plan.md` | Implementation plan |
| `design.md` | UI/UX design spec |

If found, include their paths in the agent prompt. Don't read the files yourself — let the agent read what it needs.

### 4. Route to Agent

Based on the problem type, select the most appropriate agent:

| Problem Pattern | Agent | Why |
|---|---|---|
| Architecture, system design, tech selection | `architect` | Cross-cutting technical analysis |
| Domain decisions, requirement trade-offs | `domain-expert` | Trust calculus, assumption validation |
| UI/UX direction, component strategy | `designer` | Visual/interaction design expertise |
| Implementation approach, code structure (Go) | `implementation-planner-go` | Language-specific planning |
| Implementation approach, code structure (Python) | `implementation-planner-python` | Language-specific planning |
| Mixed / unclear | `architect` | Safe default for broad technical decisions |

### 5. Spawn the Agent

**IMPORTANT**: Always pass `model: "opus"` explicitly.

```
Task(
  subagent_type: "{selected-agent}",
  model: "opus",
  prompt: "DSS SESSION

Problem: {user's problem from $ARGUMENTS}

PROJECT_DIR: {determined in Step 2}
EXISTING DOCS: {list of available upstream artifacts from Step 3}

INSTRUCTIONS:
1. Read the `diverge-synthesize-select` skill for the full DSS protocol
2. If upstream docs exist (spec.md, domain_analysis.md, plan.md, design.md), read the relevant ones for context
3. Execute the DSS protocol phases in order:
   - Phase 0: Calibrate N (score sub-factors, compute option count)
   - Phase 1: Identify strategy axes (2-5 orthogonal dimensions)
   - Phase 2: Diverge (generate N options, 3 lines each, no evaluation)
   - Phase 3: Evaluate (shuffle, score, eliminate, select top 3)
   - Phase 4: Synthesise (check compatibility of top strengths)
   - Phase 5: Present (strategy axes + all options summary + top 3 detailed + synthesis + recommendation)
4. End with [Awaiting your decision] offering: pick option, pick synthesis, custom combo, 'more options', 'different axes'
5. Write dss_output.json to PROJECT_DIR conforming to schemas/dss_output.schema.json (set decided_by: 'pending' until user selects)

Return: { artifact_path: string, summary: string, recommendation: string }"
)
```

### 6. Present Results and Offer Next Steps

When the agent returns:

1. Display the summary and recommendation
2. Show where `dss_output.json` was saved
3. Offer next steps:

> **DSS analysis complete.** Artifact saved to `{artifact_path}`.
>
> **Summary:** {summary}
>
> **Recommendation:** {recommendation}
>
> **Next steps:**
> - Pick an option number to proceed
> - Say **'synthesis'** to use the combined approach
> - Describe a **custom combination**
> - Say **'more options'** for additional alternatives
> - Say **'different axes'** to re-explore with new dimensions
> - Then use `/plan` or `/implement` to act on the chosen approach
