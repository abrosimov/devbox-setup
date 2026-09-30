---
description: Run domain expert to validate requirements and challenge assumptions
---

You are orchestrating the domain analysis phase of a development workflow.

## Steps

### 1. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py)
RC=$?
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

Store these values — pass to agent, do not re-compute.
Project directory: `{PROJECT_DIR}` (from resolve-context JSON)

### 2. Check for Existing Spec

Look for specification documents in `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`:
- `spec.md` - Main product specification (primary input)
- `research.md` - Research findings
- `decisions.md` - Decision log

If spec exists, the domain expert will validate it.
If no spec exists, the domain expert will work from user requirements directly.

### 2b. Advocate Round (when interpretations compete)

Run this step when the spec or the user's request admits several materially different readings of the domain — who the actors are, what the core entity is, where a lifecycle starts and ends — and the choice meets the threshold in `diverge-synthesize-select` (two or three unknowns could change the outcome, or the user asked for options). Otherwise skip to step 3. The main conversation runs it because subagents cannot start subagents of their own (skill section "Advocates"). The same step applies before launching `domain-modeller` in step 5 when candidate context maps or aggregate boundaries compete.

1. Frame the question in one sentence, name the criteria (fit with evidence, simplicity, what it lets the business do), and pick 3–7 candidate interpretations or models, each with an ID and a short name. Include the boring baseline — the most literal reading of the spec.
2. Launch one read-only advocate per candidate **in a single message**, using the `Plan` agent type (it has read-only tools):

```
Task(
  subagent_type: "Plan",
  model: "opus",
  prompt: "ADVOCATE BRIEF — read-only; do not edit files or ask the user questions.

Question: {one sentence}
Criteria: {list}
Your candidate: {OPT-n — name}
Rival candidates: {OPT-x — name, ...}
Sources: {spec.md / research.md / domain_analysis.md paths, relevant code paths}

Make the strongest honest case for your candidate. Return candidates with trade-offs in this shape:
- Mechanism: what the domain looks like under this reading (actors, entities, lifecycle)
- Strongest case: the evidence that supports it (path:line, quote, or link)
- Honest costs: what it leaves unexplained or makes harder, and when it loses
- Combines with: which rival readings it could absorb, and what would conflict"
)
```

3. Wait for every advocate. Until the last one returns, any update is one line: "k of n done; waiting for: <names>".
4. Pass all briefs to the agent under `ADVOCATE BRIEFS`; it weighs them as evidence and presents one decision card (T2 in `response-templates`).

### 3. Run Domain Expert Agent

Use the `domain-expert` agent.

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly. The Task tool inherits the parent's model by default — without an explicit `model` parameter, the agent runs on the parent's model (often Sonnet), ignoring the agent frontmatter.

```
Task(
  subagent_type: "domain-expert",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}\n\nADVOCATE BRIEFS: {briefs from step 2b, or 'none'}\n\n{task description}"
)
```

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`

The agent will:
- Classify the problem using Cynefin framework
- Challenge all assumptions (especially "I assume..." statements)
- Identify constraints using Theory of Constraints
- Conduct deep research to validate claims
- Build a discovery model (entities, relationships, invariants)
- Discover domain events (past tense), commands (imperative), and actors
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

When domain analysis is complete (all challenges resolved), check `domain_analysis.md` for complexity:
- **Cynefin = `clear` AND < 5 entities** → skip Domain Modeller, go to `/techne-plan`
- **Otherwise** → recommend Domain Modeller for formal DDD

**Next step suggestion (complex domain)**:
> Domain analysis complete. Discovery model has N entities, M events, K commands.
>
> **Next**: Run `domain-modeller` agent to formalise bounded contexts, aggregates, and context map (with an advocate round first, as in step 2b, if candidate boundaries compete).
>
> If formal modelling is not worth it for this domain, `/techne-plan` works from the analysis alone.

**Next step suggestion (simple domain)**:
> Domain analysis complete. Simple domain (Cynefin: Clear, N entities) — formal DDD modelling skipped.
>
> **Next**: Run `/techne-plan` to create implementation plan from validated requirements.
