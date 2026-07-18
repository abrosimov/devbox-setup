---
name: structured-output
description: >
  JSON schemas for structured agent output and the hybrid markdown+JSON pattern.
  Use when producing structured JSON output (`se_*_output.json`, `dss_output.json`)
  alongside the primary markdown deliverable.
---

# Structured Output

Most agents produce markdown only. Just **two** agents optionally emit a structured JSON contract alongside their markdown deliverable: the Software Engineer (`se_{lang}_output.json`) and the DSS protocol (`dss_output.json`). The JSON lets the immediate downstream consumer read typed fields without re-parsing prose; the markdown remains the authoritative source.

## Hybrid Output Pattern

When an agent emits structured output it produces **TWO** files:
- `{stage}.md` — the markdown (reasoning, rationale, human-readable) — **primary deliverable**
- `{stage}_output.json` — structured contract (typed fields for the downstream consumer) — **supplementary**

The markdown document is always the authoritative source. The JSON enables typed downstream consumption.

## Graceful Degradation Rule

Structured output is **OPTIONAL**. If `se_{lang}_output.json` doesn't exist, the downstream Test Writer and Code Reviewer agents fall back to reading the markdown file. Never fail because JSON is missing.

## Validation Rule

Agents that produce structured output should self-validate required fields before writing. If a required field can't be populated, set it to `null` with a comment in the markdown explaining why.

## Schema Files (Authoritative Source)

Machine-readable JSON Schema files live in `schemas/`:

| Schema | File | Used By |
|--------|------|---------|
| SE Output | `schemas/se_output.schema.json` | SE agents (Go, Python, Frontend), Test Writers, Code Reviewers |
| DSS Output | `schemas/dss_output.schema.json` | `/techne-options` command, DSS protocol |

These files are the **authoritative** schema definitions. The inline JSON examples below are derived from them. When in doubt, the schema file wins.

---

## Common Metadata Schema

Structured outputs include this metadata block:

```json
{
  "metadata": {
    "agent": "string (agent name)",
    "version": "string (schema version, e.g., 1.0)",
    "status": "enum: draft | awaiting_approval | approved | rejected",
    "jira_issue": "string",
    "branch_name": "string",
    "created_at": "string (ISO 8601)",
    "depends_on": ["array of stage names this agent read"],
    "produces_for": ["array of stage names that consume this"]
  }
}
```

---

## Stage-Specific Schemas

### DSS — `dss_output.json`

Written by the Diverge-Synthesize-Select protocol (invoked via `/techne-options` or when agents encounter Tier 3 Wide decisions). See `schemas/dss_output.schema.json` for the authoritative definition.

Top-level fields: `problem_statement`, `complexity` (tier, n_options, sub_factors), `strategy_axes` (2-5 orthogonal dimensions), `options` (N generated, each with axis position), `evaluation` (criteria, eliminated, top_candidates, synthesis), `selected` (choice, rationale, decided_by).

> **Downstream usage**: Implementation Planner and SE agents read `selected.choice` to know which approach was approved. Full option analysis persists in the JSON for audit.

### Software Engineer — `se_{agent_suffix}_output.json`

Filename convention: `se_go_output.json`, `se_python_output.json`, `se_frontend_output.json`. Each SE agent writes its own output file — no collisions during parallel execution. See `schemas/se_output.schema.json` for the authoritative definition.

Key fields: `metadata` (agent, language, role, invocation_id), `files_changed[]`, `requirements_implemented[]`, `domain_compliance`, `patterns_used[]`, `autonomous_decisions[]`, `deviations[]`, `verification_summary[]`, `verification_evidence[]`.

Required arrays (`files_changed`, `requirements_implemented`, `verification_evidence`) enforce `minItems: 1` — an agent that implements nothing or verifies nothing cannot produce valid output.

The `metadata.role` field captures what was built (api, cli, library, worker, frontend-web, etc.) — domain semantics, not architectural layer.

The `deviations[]` field replaces the former `work_log_*.md` narrative — structured plan deviation tracking instead of free-form prose.

> **Downstream usage**: Test Writer reads `requirements_implemented` + `verification_summary` to target untested areas. Code Reviewer reads `domain_compliance` + `autonomous_decisions` to audit DDD adherence and Tier 2 choices.

---

## Writing Structured Output

When an agent writes structured output, follow this pattern:

1. Complete the markdown deliverable first (primary)
2. Extract key data from the markdown into the JSON schema
3. Populate all metadata fields
4. Self-validate: check that required fields are non-null
5. Write the JSON file to `{PROJECT_DIR}/{stage}_output.json`
6. If a required field can't be populated, set it to `null` and add a note in the markdown

**This step is supplementary** — the markdown document is the primary deliverable. The JSON enables typed consumption by the immediate downstream agent.
