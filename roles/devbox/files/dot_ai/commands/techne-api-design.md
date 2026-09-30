---
description: Design API contracts (REST/OpenAPI or Protobuf/gRPC)
---

You are orchestrating the API design phase of a development workflow.

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

### 2. Check for Existing Plan

Look for documentation in `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`:
- `plan.md` - Implementation plan (primary input for API designer)
- `spec.md` - Product specification
- `domain_analysis.md` - Domain analysis

If a plan exists, the API designer will use it as primary input.
If no plan exists, the API designer will work from user requirements directly.

### 3. Detect API Format

Check the project for existing API contracts:
- If `*.proto` files or `buf.yaml` exist → **Protobuf/gRPC mode**
- Otherwise → **OpenAPI 3.1 mode** (default)

Pass the detected format to the agent.

### 4. Advocate Round (when the choice is architecture-level)

An API contract is consumed by both frontend and backend and is expensive to change once published, so it often meets the threshold in `diverge-synthesize-select`. Run this step when the design introduces a new resource or service, changes an existing contract incompatibly, spans several resources, or the user asked for options; otherwise skip to step 5. The main conversation runs it because subagents cannot start subagents of their own (skill section "Advocates").

1. Frame the contract decision in one sentence (for example "how clients page through and filter orders"), name the criteria, and pick 3–7 candidate shapes, each with an ID and a short name. Include the boring baseline — usually "extend the existing resources in the existing style".
2. Launch one read-only advocate per candidate **in a single message**, using the `architect` agent type (it has read-only tools):

```
Task(
  subagent_type: "architect",
  model: "opus",
  prompt: "ADVOCATE BRIEF — read-only; do not edit files or ask the user questions.

Decision: {one sentence}
Criteria: {list, e.g. minimal surface, consistency with existing contracts, evolvability, client ergonomics}
API_FORMAT: {detected format}
Your candidate: {OPT-n — name}
Rival candidates: {OPT-x — name, ...}
Sources: {plan.md / spec.md / domain_analysis.md paths, existing spec files}

Make the strongest honest case for your candidate. Return candidates with trade-offs in this shape:
- Mechanism: the resources, operations, and payload shape it implies
- Strongest case: where it beats the rivals, with evidence (path:line or link)
- Honest costs: what it makes harder for clients or servers, and when it loses
- Combines with: which rival strengths it could absorb, and what would conflict"
)
```

3. Wait for every advocate. Until the last one returns, any update is one line: "k of n done; waiting for: <names>".
4. Pass all briefs to the API designer under `ADVOCATE BRIEFS`.

### 5. Run API Designer Agent

Use the `api-designer` agent.

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly. The Task tool inherits the parent's model by default — without an explicit `model` parameter, the agent runs on the parent's model (often Sonnet), ignoring the agent frontmatter.

```
Task(
  subagent_type: "api-designer",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, API_FORMAT={detected format}\n\nADVOCATE BRIEFS: {briefs from step 4, or 'none'}\n\n{task description}"
)
```

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, API_FORMAT={detected format}`. When advocate briefs are present, the API designer weighs them as evidence and presents one decision card (T2 in `response-templates`) before writing the spec.

The agent will:
- Read existing documentation (plan, spec, domain analysis)
- Detect or confirm API format
- Design resources/services from requirements
- Define error strategy, pagination, filtering, versioning
- Negotiate design with user (challenge assumptions)
- Produce spec files (OpenAPI YAML or .proto files)
- Validate with Spectral or buf lint
- Create `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/api_design.md`

**Important**: The API designer is intentionally opinionated about minimal API surface area and will challenge unnecessary complexity. This is by design.

### 6. After Completion

When API design is complete, present the summary.

**Next step suggestion**:
> API design complete.
>
> **Next**: Run `/techne-implement` to begin backend implementation, or `/techne-design` for UI/UX design.
