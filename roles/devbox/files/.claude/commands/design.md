---
description: Create UI/UX design specification and design tokens
---

You are orchestrating the UI/UX design phase of a development workflow.

## Steps

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to agent, do not re-compute.
Project directory: `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/` (see `config` skill)

### 2. Check for Existing Documentation

Look for documentation in `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`:
- `spec.md` - Product specification (primary input)
- `domain_analysis.md` - Domain analysis (primary input)
- `plan.md` - Implementation plan (optional — if Designer runs after Planner)
- `api_design.md` - API design (optional — shows data shapes for UI)

If `spec.md` or `domain_analysis.md` exists, the designer will use them as primary input.
If `plan.md` exists, the designer reads it for additional context.
If API design exists, it provides data shapes and endpoint information for the UI.
If no documents exist, the designer will work from user requirements directly.

### 3. Run Designer Agent

Use the `designer` agent.

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly. The Task tool inherits the parent's model by default — without an explicit `model` parameter, the agent runs on the parent's model (often Sonnet), ignoring the agent frontmatter.

```
Task(
  subagent_type: "designer",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\n\n{task description}"
)
```

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`

The agent will:
- **Ask for a Figma URL** (if user has one) and save it to project metadata for downstream agents
- Read existing documentation (spec, domain analysis, and optionally plan, API design)
- Read existing design context from Figma (via MCP), Storybook (via MCP), and existing tokens
- **Create user flow diagrams in FigJam** (flowcharts for key user journeys)
- **Create component state diagrams in FigJam** (state machines for interactive components)
- Define design tokens in W3C format (from Figma variables if available)
- Design layout and responsive behaviour
- Specify components (props, variants, states, interactions, accessibility)
- **Present 3-5 design options** for user to choose from before developing full spec
- Develop the selected option into full design specification
- Generate design system rules and set up Code Connect (if Figma file provided)
- Iterate with user on feedback
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/design_system.tokens.json`
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/design.md` (includes FigJam diagram URLs)
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/design_output.json` (includes `figma_source` for downstream agents)

**Important**: The designer is intentionally opinionated about minimal component sets and will challenge unnecessary complexity. This is by design. The Figma URL (if provided) is persisted in `design_output.json` so that Frontend Engineer and Code Reviewer agents can access the design file directly.

### 4. After Completion

When design is complete, present the summary.

**Next step suggestion**:
> Design specification complete.
>
> **Next**: Frontend Engineer (when available) to implement from this spec.
>
> Say **'continue'** to proceed, or address any remaining open questions.
