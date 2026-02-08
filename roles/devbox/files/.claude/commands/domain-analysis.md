---
description: Run domain expert to validate requirements and challenge assumptions
---

You are orchestrating the domain analysis phase of a development workflow.

## Steps

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to agent, do not re-compute.
Project directory: `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/` (see `config` skill)

### 2. Check for Existing Spec

Look for specification documents in `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`:
- `spec.md` - Main product specification (primary input)
- `research.md` - Research findings
- `decisions.md` - Decision log

If spec exists, the domain expert will validate it.
If no spec exists, the domain expert will work from user requirements directly.

### 3. Run Domain Expert Agent

Use the `domain-expert` agent.

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`

The agent will:
- Classify the problem using Cynefin framework
- Challenge all assumptions (especially "I assume..." statements)
- Identify constraints using Theory of Constraints
- Conduct deep research to validate claims
- Build a verified domain model
- Define quality metrics (what matters, not what's easy to measure)
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/domain_analysis.md`

**Important**: The domain expert is intentionally skeptical and will push back on unvalidated assumptions. This is by design - the goal is to catch issues before implementation.

### 4. Iterative Process

The domain expert may:
- Ask clarifying questions
- Challenge your assumptions
- Present contradicting evidence
- Require you to validate claims

This is an interactive process. Engage with the challenges - they improve the final output.

### 5. After Completion

When domain analysis is complete (all challenges resolved), present the summary.

**Next step suggestion**:
> Domain analysis complete.
>
> **Next**: Run `/plan` to create implementation plan from validated requirements.
>
> Say **'continue'** to proceed, or address any remaining open challenges.
