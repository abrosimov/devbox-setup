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
- `plan.md` - Implementation plan (primary input)
- `api_design.md` - API design (optional — shows data shapes for UI)
- `spec.md` - Product specification
- `domain_analysis.md` - Domain analysis

If a plan exists, the designer will use it as primary input.
If API design exists, it provides data shapes and endpoint information for the UI.
If no plan exists, the designer will work from user requirements directly.

### 3. Run Designer Agent

Use the `designer` agent.

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`

The agent will:
- Read existing documentation (plan, API design, spec, domain analysis)
- Check for existing design context (Figma MCP, Storybook MCP, existing tokens)
- Define design tokens in W3C format
- Design layout and responsive behaviour
- Specify components (props, variants, states, interactions, accessibility)
- Iterate with user on feedback
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/design_system.tokens.json`
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/design.md`

**Important**: The designer is intentionally opinionated about minimal component sets and will challenge unnecessary complexity. This is by design.

### 4. After Completion

When design is complete, present the summary.

**Next step suggestion**:
> Design specification complete.
>
> **Next**: Frontend Engineer (when available) to implement from this spec.
>
> Say **'continue'** to proceed, or address any remaining open questions.
