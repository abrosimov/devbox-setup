---
description: Design API contracts (REST/OpenAPI or Protobuf/gRPC)
---

You are orchestrating the API design phase of a development workflow.

## Steps

### 1. Compute Task Context (once)

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
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

### 4. Run API Designer Agent

Use the `api-designer` agent.

**IMPORTANT**: When invoking the Task tool, always pass `model: "opus"` explicitly. The Task tool inherits the parent's model by default — without an explicit `model` parameter, the agent runs on the parent's model (often Sonnet), ignoring the agent frontmatter.

```
Task(
  subagent_type: "api-designer",
  model: "opus",
  prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, API_FORMAT={detected format}\n\n{task description}"
)
```

**Include in agent prompt**: `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, API_FORMAT={detected format}`

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

### 5. After Completion

When API design is complete, present the summary.

**Next step suggestion**:
> API design complete.
>
> **Next**: Run `/implement` to begin backend implementation, or `/design` for UI/UX design.
>
> Say **'continue'** to proceed, or address any remaining open questions.
