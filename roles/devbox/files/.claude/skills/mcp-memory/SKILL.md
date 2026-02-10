---
name: mcp-memory
description: >
  Memory MCP patterns for persistent knowledge graph across conversations. Covers
  entity creation, relation management, observation tracking, search, and naming
  conventions for upstream (TPM, domain, planners) and downstream (reviewers) scopes.
  Triggers on: memory, knowledge graph, persistent context, cross-session, entity,
  relation, observation, recall, remember.
---

# Memory MCP

Persistent knowledge graph using the Memory MCP server.

---

## Architecture: Per-Ticket Upstream, Project-Root Downstream

The system uses **two memory instances** with different scoping and persistence models:

| Instance | Scope | VCS | Path | Agents |
|----------|-------|-----|------|--------|
| **upstream** | Per Jira ticket | **Tracked** | `{PROJECT_DIR}/memory/upstream.jsonl` | TPM, Domain Expert, Planners |
| **downstream** | Whole project | **Gitignored** | `.claude/memory/downstream.jsonl` | Code Reviewers |

### Why this split?

**Upstream** stores domain knowledge, decisions, and validated assumptions for a specific feature. This lives alongside `spec.md`, `plan.md`, and other pipeline artefacts in the ticket directory. It's VCS-tracked because:
- Each ticket lives on its own branch → no merge conflicts
- Team members picking up a ticket inherit accumulated knowledge
- PRs show what the AI "learned" — auditable
- Knowledge has a natural lifecycle tied to the ticket

**Downstream** stores cross-ticket review findings (recurring bugs, module pain points). This is gitignored because:
- Reviewers learn patterns across many tickets — not scoped to one
- Review findings are per-developer working state
- Important patterns get captured in code review comments and PR history

### How it works

Wrapper scripts in `~/.claude/bin/` handle dynamic path resolution:
- `memory-upstream` reads the git branch, computes `PROJECT_DIR`, and mounts `{PROJECT_DIR}/memory/` into the Docker container
- `memory-downstream` always mounts `{GIT_ROOT}/.claude/memory/` into the container
- Both create directories and files if they don't exist
- On non-feature branches (main, develop), upstream falls back to `.claude/memory/`

---

## Available Tools

Replace `{scope}` with `memory-upstream` or `memory-downstream` depending on your agent.

| Tool | Purpose |
|------|---------|
| `mcp__{scope}__create_entities` | Create new entities in the knowledge graph |
| `mcp__{scope}__create_relations` | Create directed relations between entities |
| `mcp__{scope}__add_observations` | Add observations to existing entities |
| `mcp__{scope}__search_nodes` | Search entities by name or type |
| `mcp__{scope}__open_nodes` | Retrieve specific entities by name |
| `mcp__{scope}__delete_entities` | Remove entities from the graph |
| `mcp__{scope}__delete_relations` | Remove relations from the graph |
| `mcp__{scope}__delete_observations` | Remove specific observations from entities |

---

## When to Use

### Upstream Agents (TPM, Domain Expert, Planners)

**Store:**
- Validated domain concepts and their relationships
- Architectural decisions with rationale (especially rejected approaches)
- User personas and their goals (reusable across sessions on the same ticket)
- Recurring constraints and technical limitations
- Research findings that inform this feature

**Retrieve:**
- At session start — search for prior knowledge from earlier sessions on this ticket
- When encountering a familiar concept — check for existing domain models
- Before proposing an approach — check if it was previously rejected in this ticket

### Downstream Agents (Code Reviewers)

**Store:**
- Recurring code review findings (patterns of bugs seen 2+ times)
- Codebase pain points that appear across PRs
- Module-level anti-patterns observed over time

**Retrieve:**
- At review start — search for known issues in the affected module
- When encountering a suspicious pattern — check if it's a known codebase anti-pattern

---

## Entity Naming Conventions

### Upstream Entities

| Entity Type | Naming Pattern | Example |
|-------------|---------------|---------|
| `domain-concept` | `{concept-name}` | `order-lifecycle`, `user-authentication` |
| `persona` | `{persona-name}` | `dana-developer`, `alex-admin` |
| `decision` | `decision:{area}:{choice}` | `decision:pagination:cursor-based` |
| `rejected-approach` | `rejected:{area}:{approach}` | `rejected:auth:session-cookies` |
| `constraint` | `constraint:{description}` | `constraint:api-rate-limit-1000rpm` |
| `assumption` | `assumption:{description}` | `assumption:users-prefer-email-notifications` |

### Downstream Entities

| Entity Type | Naming Pattern | Example |
|-------------|---------------|---------|
| `module` | `module:{path}` | `module:internal/auth` |
| `recurring-issue` | `issue:{description}` | `issue:missing-error-wrapping-in-handlers` |
| `anti-pattern` | `antipattern:{description}` | `antipattern:bare-string-errors` |

### Relations

Use **active voice**, present tense:

| Relation | Example |
|----------|---------|
| `depends-on` | `order-lifecycle` → `depends-on` → `user-authentication` |
| `was-rejected-for` | `rejected:auth:session-cookies` → `was-rejected-for` → `decision:auth:jwt` |
| `affects` | `constraint:api-rate-limit` → `affects` → `module:internal/sync` |
| `has-recurring-issue` | `module:internal/handlers` → `has-recurring-issue` → `issue:missing-error-wrapping` |

---

## Usage Patterns

### Pattern 1: Start-of-Session Recall (All Agents)

At the start of every session, search for relevant prior knowledge:

```
1. search_nodes("current feature domain keywords")
2. If results found → open_nodes to get full context
3. Factor prior knowledge into your analysis
```

### Pattern 2: Decision Recording (Upstream)

After a significant decision is made:

```
1. create_entities([{name: "decision:pagination:cursor-based", entityType: "decision"}])
2. add_observations("decision:pagination:cursor-based", [
     "Chosen over offset-based for performance at scale (>1M rows)",
     "Trade-off: slightly worse developer ergonomics",
     "Date: 2026-02-10, Task: PROJ-123"
   ])
3. create_entities([{name: "rejected:pagination:offset-based", entityType: "rejected-approach"}])
4. create_relations([{
     from: "rejected:pagination:offset-based",
     to: "decision:pagination:cursor-based",
     relationType: "was-rejected-for"
   }])
```

### Pattern 3: Review Finding Accumulation (Downstream)

When a review reveals a recurring pattern:

```
1. search_nodes("error wrapping handlers")
2. If entity exists → add_observations with new instance
3. If new → create_entities + create_relations to affected module
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Storing session-specific context | Pollutes graph with transient data | Only store knowledge that applies across sessions |
| Storing entire specs or plans | Token waste on retrieval | Store key insights and decisions, link to files |
| Creating entities without observations | Empty nodes are useless | Always add at least one observation |
| Not searching before creating | Duplicate entities | Always `search_nodes` first |
| Storing implementation details | Couples memory to code that will change | Store domain concepts and decisions, not code patterns |

---

## Graceful Degradation

If `mcp__memory-upstream` or `mcp__memory-downstream` is not available (connection error, Docker not running, or not configured):
- **Skip** memory retrieval and storage
- **Proceed** with session-only context
- **Do not** block on MCP availability
- **Do not** warn the user unless they explicitly asked to use memory
