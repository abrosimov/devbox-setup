---
description: Generate diverse solution options using DSS (Diverge-Synthesize-Select) protocol
---

You are orchestrating a DSS (Diverge-Synthesize-Select) session for structured option generation.

## What This Does

Routes design problems to the appropriate thinking agent with the DSS procedure enabled. The user asked for options, so the threshold in `diverge-synthesize-select` holds: the result is a decision card (T2 in `response-templates`) with 3–7 candidates, a boring baseline, at least one combination, synergies, trade-offs, and a recommendation. For architecture-level problems, one read-only advocate per candidate argues its case first, so every approach gets its best hearing rather than a strawman.

## Steps

### 1. Parse the User's Problem

The user provides a problem or question as argument: `$ARGUMENTS`

If no argument provided, ask:
> What design problem would you like to explore options for?

### 2. Resolve Context

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py 2>/dev/null) && RC=$? || RC=$?
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
| Implementation approach, work streams | `implementation-planner` | Stack-agnostic functional planning (detects Go/Python/frontend) |
| Mixed / unclear | `architect` | Safe default for broad technical decisions |

### 5. Advocate Round (architecture-level problems)

Run this step when the route is `architect` or `domain-expert`; for `designer` and `implementation-planner`, go straight to step 6. The main conversation runs it because subagents cannot start subagents of their own. The `diverge-synthesize-select` skill, section "Advocates", describes the pattern.

1. Frame the decision in one sentence, name the criteria, and pick 3–7 candidate approaches, each with an ID and a short name (`OPT-1 — extend the job table`). Include the boring baseline. Keep this light — a few reads at most; the advocates do the digging.
2. Launch one advocate per candidate **in a single message**, so they run in parallel. Advocates are read-only: use the `architect` agent type for technical candidates and the `Plan` agent type for domain interpretations.

```
Task(
  subagent_type: "architect" | "Plan",
  model: "opus",
  prompt: "ADVOCATE BRIEF — read-only; do not edit files or ask the user questions.

Decision: {one sentence}
Criteria: {list}
Your candidate: {OPT-n — name}
Rival candidates: {OPT-x — name, ...}
Sources: {upstream docs from Step 3, relevant code paths}

Make the strongest honest case for your candidate. Return candidates with trade-offs in this shape:
- Mechanism: how it works here, concretely
- Strongest case: where it beats the rivals, with evidence (path:line or link)
- Honest costs: what it makes harder and when it loses
- Combines with: which rival strengths it could absorb, and what would conflict"
)
```

3. Wait for every advocate. Until the last one returns, any update is one line: "k of n done; waiting for: <names>".
4. Pass all briefs to the specialist in step 6 under `ADVOCATE BRIEFS`.

### 6. Spawn the Agent

**IMPORTANT**: Always pass `model: "opus"` explicitly.

```
Task(
  subagent_type: "{selected-agent}",
  model: "opus",
  prompt: "DSS SESSION

Problem: {user's problem from $ARGUMENTS}

PROJECT_DIR: {determined in Step 2}
EXISTING DOCS: {list of available upstream artifacts from Step 3}
ADVOCATE BRIEFS: {briefs from Step 5, or 'none'}

INSTRUCTIONS:
1. Follow the `diverge-synthesize-select` skill. The user asked for options, so the threshold holds.
2. Read the upstream docs that matter for this problem.
3. If advocate briefs are present, treat them as evidence rather than verdicts: check what they cite, keep their IDs and names, and add any strong missing candidate with the next free ID.
4. Produce the decision card (T2 in `response-templates`): 3–7 candidates including a boring baseline and at least one combination; a table with mechanism, pros, cons, combines-with; synergies; trade-offs; a recommendation with its reason. End with the recommendation.
5. Write dss_output.json to PROJECT_DIR (decided_by: 'pending' until the user selects).

Return: { artifact_path: string, decision_card: string, recommendation: string }"
)
```

### 7. Present the Decision Card

When the agent returns, show its decision card as it stands (every candidate ID with its name), mention in one line where `dss_output.json` was saved, and finish with the recommendation and its reason. That is the end of the reply: the user answers with an ID, a combination, "more options" (appended with the next free IDs, never renumbered), or "different axes", and then `/techne-plan` or `/techne-implement` acts on the choice.
