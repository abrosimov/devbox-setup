---
description: Design database schema using database designer agent
---

You are orchestrating the schema design phase of a development workflow.

## CRITICAL: Verify User Approval Before Schema Design

**Before spawning the database designer agent, verify ONE of these conditions:**

1. User explicitly invoked `/schema` command (this counts as approval)
2. User said "yes", "go ahead", "proceed" after seeing a proposal
3. User selected a specific option from alternatives presented

**If user only asked for analysis/proposal/options → DO NOT proceed. Present your analysis and wait.**

## Parse Arguments

Check if user passed a database argument:
- `/schema postgres` or `/schema postgresql` → force **PostgreSQL** mode
- `/schema mysql` → force **MySQL** mode
- `/schema mongo` or `/schema mongodb` → force **MongoDB** mode
- `/schema cockroach` or `/schema cockroachdb` → force **CockroachDB** mode
- `/schema` (no argument) → auto-detect database

## Steps

### 1. Compute Task Context (once)

```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to agent, do not re-compute.

### 2. Check for Implementation Plan

Look for plan at `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md` (see `config` skill for configured path).

Also check for:
- `spec.md` — Product specification
- `domain_analysis.md` — Domain analysis
- `api_design.md` — API design (schema may need to support the API contract)

### 3. Detect Database (if not specified)

If user did not specify a database in the command arguments, check the project:

```bash
# Check for existing migrations
find . -path "*/migrations/*.sql" -o -path "*/alembic/*" -o -path "*/goose/*" 2>/dev/null | head -5

# Check docker-compose for database services
grep -l "postgres\|mysql\|mongo\|cockroach" docker-compose*.yml 2>/dev/null

# Check connection strings in config files
grep -r "postgresql://\|mysql://\|mongodb://\|cockroach://" --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.env" --include="*.json" 2>/dev/null | head -5

# Check Go dependencies
grep "pgx\|go-sql-driver/mysql\|mongo-driver\|cockroachdb" go.mod 2>/dev/null

# Check Python dependencies
grep "psycopg\|pymysql\|pymongo\|sqlalchemy.*cockroach" pyproject.toml requirements*.txt 2>/dev/null
```

Pass the detected database (or "auto-detect") to the agent.

### 4. Run Database Designer Agent

Use the `database-designer` agent:

```
Task(
    subagent_type: "database-designer",
    model: "opus",
    prompt: "Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, PROJECT_DIR={PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}\n\nDatabase: {detected_or_specified_db}\n\n{existing docs summary}\n\nDesign the database schema for this task."
)
```

The agent will:
- Read the implementation plan and other docs if they exist
- Detect or confirm the database type
- Design the schema with full rationale
- Write migration files
- Provide summary and suggest next step

### 5. After Completion

Present the agent's summary and suggested next step to the user.
Wait for user to say 'continue' or provide corrections.
