---
name: structured-output
description: >
  JSON schemas for structured agent output, hybrid output pattern, pipeline state tracking,
  and decision logging. Enables automated pipeline coordination and downstream agent consumption.
  Triggers on: structured output, JSON schema, pipeline state, decision log, output contract.
---

# Structured Output

Defines the "common language" for agent pipeline coordination. Each agent produces structured JSON alongside its existing markdown deliverables.

## Hybrid Output Pattern

Each agent produces **TWO** files:
- `{stage}.md` — existing markdown (reasoning, rationale, human-readable) — **primary deliverable**
- `{stage}_output.json` — structured contract (metadata + typed fields for downstream agents) — **supplementary**

The markdown document is always the authoritative source. The JSON enables automated pipeline tracking and downstream agent consumption.

## Graceful Degradation Rule

Structured output is **OPTIONAL**. If `{stage}_output.json` doesn't exist, downstream agents fall back to reading the markdown file. Never fail because JSON is missing.

## Validation Rule

Agents that produce structured output should self-validate required fields before writing. If a required field can't be populated, set it to `null` with a comment in the markdown explaining why.

## Schema Files (Authoritative Source)

Machine-readable JSON Schema files live in `schemas/`:

| Schema | File | Used By |
|--------|------|---------|
| SE Output | `schemas/se_output.schema.json` | SE agents (Go, Python, Frontend), Test Writers, Code Reviewers |
| Stream Completion | `schemas/stream_completion.schema.json` | Stream executors (Phase 4 DAG) |
| Execution DAG | `schemas/execution_dag.schema.json` | Full-cycle orchestrator |
| Pipeline State | `schemas/pipeline_state.schema.json` | Full-cycle orchestrator |
| DSS Output | `schemas/dss_output.schema.json` | `/options` command, DSS protocol |
| Progress Plan | `schemas/progress_plan.schema.json` | TPM (init), Impl Planner (refine) |
| Progress Agent | `schemas/progress_agent.schema.json` | All pipeline agents |

These files are the **authoritative** schema definitions. The inline JSON examples below are derived from them. When in doubt, the schema file wins.

## Programmatic Validation

Agent output is verified by `bin/validate-pipeline-output` — a deterministic script, not LLM self-assessment:

```bash
# Validate stream completion output
bin/validate-pipeline-output --schema stream_completion --file backend_completion.json

# Full validation: schema + reality check + build + tests
bin/validate-pipeline-output --full --file backend_completion.json --lang go

# Validate DAG integrity (cycles, dangling edges, required fields)
bin/validate-pipeline-output --dag-check --file execution_dag.json
```

Exit codes map to specific failure types:

| Code | Meaning | Orchestrator Action |
|------|---------|-------------------|
| 0 | Passed | Advance pipeline |
| 1 | Schema violation | Retry: "Output JSON malformed" |
| 2 | Reality mismatch | Retry: "Claimed files don't exist" |
| 3 | Build failure | Retry: "Code doesn't compile: {error}" |
| 4 | Test failure | Retry: "Tests fail: {error}" |
| 5 | DAG integrity | Rebuild DAG |

---

## Common Metadata Schema

All agent outputs include this metadata block:

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

### TPM — `spec_output.json`

```json
{
  "metadata": { "agent": "technical-product-manager", "version": "1.0", "..." : "..." },
  "personas": [
    { "name": "string", "context": "string", "goal": "string", "current_pain": "string" }
  ],
  "goals": ["string"],
  "functional_requirements": [
    { "id": "FR-001", "name": "string", "description": "string", "persona_goal": "string", "examples": [], "boundary": "string" }
  ],
  "non_functional_requirements": [
    { "category": "string (performance | reliability | security | compatibility)", "target": "string", "notes": "string" }
  ],
  "out_of_scope": ["string"],
  "open_questions": ["string"]
}
```

### Domain Expert — `domain_output.json`

```json
{
  "metadata": { "agent": "domain-expert", "version": "1.1", "..." : "..." },
  "assumptions": [
    { "id": "A1", "claim": "string", "status": "validated | invalidated | needs_validation", "evidence": "string", "risk_if_wrong": "string" }
  ],
  "discovery_model": {
    "entities": [
      { "name": "string", "description": "string", "key_attributes": ["string"], "constraints": ["string"] }
    ],
    "relationships": [
      { "from": "string", "to": "string", "type": "string", "cardinality": "string" }
    ],
    "invariants": ["string"]
  },
  "discovery_events": [
    { "name": "string (past tense)", "description": "string", "trigger": "string" }
  ],
  "discovery_commands": [
    { "name": "string (imperative)", "actor": "string", "triggers_event": "string" }
  ],
  "discovery_actors": [
    { "name": "string", "type": "human | system", "description": "string" }
  ],
  "constraints": [
    { "name": "string", "type": "technical | organisational | external", "impact": "string", "addressed_by_spec": "boolean" }
  ],
  "risks": [
    { "description": "string", "likelihood": "high | medium | low", "impact": "high | medium | low", "mitigation": "string" }
  ],
  "cynefin_classification": "clear | complicated | complex | chaotic | confused"
}
```

### Domain Modeller — `domain_model.json`

Summary of top-level fields:

```json
{
  "metadata": { "agent": "domain-modeller", "version": "1.0", "..." : "..." },
  "ubiquitous_language": [
    { "term": "string", "definition": "string", "bounded_context": "string", "aliases": ["string"] }
  ],
  "bounded_contexts": [
    {
      "name": "string",
      "subdomain_type": "core | supporting | generic",
      "domain_vision": "string",
      "aggregates": [
        {
          "name": "string",
          "root": { "name": "string", "type": "entity", "identity_field": "string", "fields": [] },
          "entities": [],
          "value_objects": [],
          "invariants": [{ "id": "INV-N", "predicate": "string", "description": "string", "severity": "critical | warning" }],
          "commands": [{ "name": "string", "actor": "string", "preconditions": [], "postconditions": [], "emits": [] }],
          "domain_events": [{ "name": "string", "fields": [], "triggered_by": "string" }],
          "state_machine": { "states": [], "initial": "string", "terminal": [], "transitions": [] }
        }
      ]
    }
  ],
  "context_map": {
    "relationships": [
      { "upstream": "string", "downstream": "string", "pattern": "string", "implementation": "string" }
    ]
  },
  "system_constraints": [
    { "name": "string", "type": "technical | organisational | external | regulatory", "description": "string", "impact": "string", "affected_contexts": ["string"], "mitigation": "string | null" }
  ],
  "risks": [
    { "description": "string", "likelihood": "high | medium | low", "impact": "high | medium | low", "mitigation": "string", "affected_contexts": ["string"] }
  ],
  "system_design_bridge": {
    "service_mapping": [
      { "bounded_context": "string", "suggested_service": "string", "communication": [], "data_store_hint": "string" }
    ]
  },
  "verification": {
    "aggregate_roots_exist": "boolean",
    "value_objects_immutable": "boolean",
    "events_past_tense": "boolean",
    "commands_have_preconditions": "boolean",
    "invariants_have_predicates": "boolean",
    "context_map_symmetric": "boolean",
    "glossary_complete": "boolean",
    "state_machines_complete": "boolean"
  }
}
```

### Implementation Planner — `plan_output.json`

```json
{
  "metadata": { "agent": "implementation-planner-*", "version": "1.1", "..." : "..." },
  "requirements": [
    {
      "id": "FR-001",
      "description": "string",
      "agent_hint": "enum: backend | frontend | fullstack | database | api | observability | null",
      "acceptance_criteria": ["string"],
      "error_cases": [
        { "condition": "string", "expected_behaviour": "string" }
      ]
    }
  ],
  "business_rules": [
    { "id": "BR-1", "description": "string" }
  ],
  "integration_points": [
    { "system": "string", "purpose": "string", "notes": "string" }
  ],
  "implementation_order": ["string (FR IDs in suggested order — kept for backward compatibility)"],
  "work_streams": [
    {
      "id": "WS-1",
      "name": "string (e.g., Data Layer, API Contract, Backend Logic, Frontend UI)",
      "agent": "string (e.g., database-designer, api-designer, software-engineer-go, software-engineer-frontend)",
      "command": "string (e.g., /schema, /api-design, /implement)",
      "requirements": ["string (FR/NFR IDs assigned to this stream)"],
      "depends_on": ["string (WS IDs that must complete before this stream starts)"],
      "blocks": ["string (WS IDs that cannot start until this stream completes)"]
    }
  ],
  "parallelism_groups": [
    {
      "group": "number (execution order — lower runs first)",
      "streams": ["string (WS IDs that can run concurrently within this group)"],
      "gate_after": "string (pipeline gate ID after this group, e.g., G3) | null"
    }
  ],
  "test_scenarios": [
    { "area": "string", "scenario": "string", "inputs": "string", "expected_outcome": "string" }
  ]
}
```

### Designer — `design_output.json`

```json
{
  "metadata": { "agent": "designer", "version": "1.1", "..." : "..." },
  "figma_source": {
    "url": "string (full Figma URL provided by user, null if none)",
    "file_key": "string (extracted from URL, null if none)",
    "node_id": "string (extracted from URL, null if none)"
  },
  "figma_artifacts": {
    "user_flow_url": "string (FigJam user flow diagram URL, null if not created)",
    "state_diagrams": [
      { "component": "string (component name)", "url": "string (FigJam URL)" }
    ],
    "sequence_diagrams": [
      { "interaction": "string (interaction name)", "url": "string (FigJam URL)" }
    ]
  },
  "options": [
    {
      "name": "string",
      "summary": "string",
      "trade_offs": { "pros": ["string"], "cons": ["string"] },
      "complexity": "low | medium | high",
      "components_count": "number",
      "tokens_count": "number"
    }
  ],
  "selected_option": "string (option name, null if awaiting decision)",
  "components": [
    { "name": "string", "purpose": "string", "props_count": "number", "variants": ["string"], "is_existing": "boolean" }
  ],
  "tokens_summary": {
    "colour_count": "number",
    "spacing_count": "number",
    "typography_count": "number",
    "total": "number"
  },
  "accessibility_plan": {
    "wcag_level": "AA | AAA",
    "keyboard_nav": "boolean",
    "screen_reader": "boolean",
    "colour_contrast_verified": "boolean"
  }
}
```

> **Downstream usage**: Frontend Engineer and Code Reviewer agents read `figma_source` to access the Figma file directly via `get_design_context` and `get_screenshot` for implementation verification.

### DSS — `dss_output.json`

Written by the Diverge-Synthesize-Select protocol (invoked via `/options` or when agents encounter Tier 3 Wide decisions). See `schemas/dss_output.schema.json` for the authoritative definition.

Top-level fields: `problem_statement`, `complexity` (tier, n_options, sub_factors), `strategy_axes` (2-5 orthogonal dimensions), `options` (N generated, each with axis position), `evaluation` (criteria, eliminated, top_candidates, synthesis), `selected` (choice, rationale, decided_by).

> **Downstream usage**: Implementation Planner and SE agents read `selected.choice` to know which approach was approved. Full option analysis persists in the JSON for audit.

### API Designer — `api_design_output.json`

```json
{
  "metadata": { "agent": "api-designer", "version": "1.0", "..." : "..." },
  "format": "openapi | protobuf",
  "resources": [
    {
      "name": "string",
      "operations": ["string (e.g., list, get, create, update, delete)"],
      "relationships": ["string (e.g., belongs_to:Customer, has_many:Items)"]
    }
  ],
  "error_strategy": {
    "format": "rfc9457 | grpc_status",
    "common_errors": [
      { "error": "string", "status_code": "string", "description": "string" }
    ]
  },
  "pagination": { "type": "cursor | offset | page_token", "default_page_size": "number" },
  "spec_file_path": "string (relative path to api_spec.yaml or .proto files)"
}
```

### Software Engineer — `se_{agent_suffix}_output.json`

Filename convention: `se_go_output.json`, `se_python_output.json`, `se_frontend_output.json`. Each SE agent writes its own output file — no collisions during parallel execution. See `schemas/se_output.schema.json` for the authoritative definition.

Key fields: `metadata` (agent, language, role, invocation_id), `files_changed[]`, `requirements_implemented[]`, `domain_compliance`, `patterns_used[]`, `autonomous_decisions[]`, `deviations[]`, `verification_summary[]`, `verification_evidence[]`.

Required arrays (`files_changed`, `requirements_implemented`, `verification_evidence`) enforce `minItems: 1` — an agent that implements nothing or verifies nothing cannot produce valid output.

The `metadata.role` field captures what was built (api, cli, library, worker, frontend-web, etc.) — domain semantics, not architectural layer.

The `deviations[]` field replaces the former `work_log_*.md` narrative — structured plan deviation tracking instead of free-form prose.

> **Downstream usage**: Test Writer reads `requirements_implemented` + `verification_summary` to target untested areas. Code Reviewer reads `domain_compliance` + `autonomous_decisions` to audit DDD adherence and Tier 2 choices.

### Stream Completion — `{stream}_completion.json`

Written by stream executors at the end of Phase 4 DAG execution. Validated by `bin/validate-pipeline-output --full`. See `schemas/stream_completion.schema.json` for authoritative definition.

```json
{
  "stream": "string (stream identifier, e.g., 'backend', 'frontend')",
  "status": "enum: complete | partial | blocked | failed",
  "steps": [
    {
      "name": "enum: se | commit_impl | test | commit_test",
      "status": "enum: passed | failed | skipped",
      "error": "string (required if status=failed)",
      "output_file": "string (path to step output, e.g., se_{lang}_output.json)"
    }
  ],
  "git_sha": "string (HEAD SHA after completion, pattern: ^[a-f0-9]{7,40}$)",
  "files_modified": ["string (relative paths of modified files)"],
  "output_files": ["string (paths to structured output JSONs)"],
  "build_passed": "boolean (language-specific build check result)",
  "tests_passed": "boolean",
  "tests_total": "integer",
  "tests_failed": "integer",
  "attempt": "integer (1 = first try, 2+ = retry)",
  "started_at": "string (ISO 8601)",
  "completed_at": "string (ISO 8601)"
}
```

**Invariants enforced by schema:**
- If `status=complete`: no step may have `status=failed`, and `build_passed` must be `true`
- If `status=failed`: at least one step must have `status=failed` with a non-empty `error`
- `git_sha` must match `^[a-f0-9]{7,40}$` pattern

> **Downstream usage**: Orchestrator validates with `bin/validate-pipeline-output --full`. Exit code determines whether to advance DAG, retry, or escalate.

---

## Pipeline State Schema — `pipeline_state.json`

Tracks pipeline progress across the full development cycle.

```json
{
  "pipeline_id": "JIRA-123_feature-name",
  "feature_type": "ui | backend | fullstack",
  "stages": {
    "tpm": { "status": "completed | in_progress | pending | skipped", "output": "spec.md", "approved_at": "ISO 8601 | null" },
    "domain_expert": { "status": "...", "output": "domain_analysis.md", "approved_at": null },
    "domain_modeller": { "status": "...", "output": "domain_model.md", "approved_at": null },
    "designer": { "status": "...", "output": "design.md", "selected_option": "string | null", "figma_source": { "url": "string | null", "file_key": "string | null" }, "figma_artifacts": { "user_flow_url": "string | null", "state_diagram_count": "number" }, "approved_at": null },
    "impl_planner": { "status": "...", "output": "plan.md", "approved_at": null },
    "database_designer": { "status": "...", "output": "schema_design.md", "approved_at": null },
    "api_designer": { "status": "...", "output": "api_design.md", "approved_at": null },
    "software_engineer_backend": { "status": "...", "approved_at": null },
    "software_engineer_frontend": { "status": "...", "approved_at": null },
    "test_writer": { "status": "...", "approved_at": null },
    "code_reviewer": { "status": "...", "approved_at": null },
    "observability_engineer": { "status": "...", "approved_at": null }
  },
  "current_gate": "G1 | G2 | G3 | G4 | none",
  "decisions": []
}
```

### Stage Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not yet started |
| `in_progress` | Agent currently running |
| `completed` | Agent finished, output available |
| `skipped` | Stage not applicable for this feature type |

---

## Decision Log Schema — `decisions.json`

Records user decisions at pipeline gates and key decision points.

```json
{
  "decisions": [
    {
      "id": "D1",
      "gate": "G2",
      "stage": "designer",
      "question": "Which design direction?",
      "options_presented": ["Minimalist", "Dashboard", "Wizard"],
      "chosen": "Dashboard",
      "rationale": "User preference for information density",
      "decided_by": "user",
      "timestamp": "ISO 8601"
    }
  ]
}
```

---

## Progress Spine (Supplementary Tracking)

Progress tracking is **distinct from** structured output:

| Aspect | Structured Output (`*_output.json`) | Progress (`progress/*.json`) |
|--------|--------------------------------------|-------------------------------|
| **Purpose** | Final deliverable contract | Live status tracking |
| **Written** | Once, at agent completion | Incrementally during work |
| **Schema** | Stage-specific (spec, plan, design...) | `progress_plan` + `progress_agent` |
| **Read by** | Downstream agents | Orchestrator + `/status` command |
| **Required?** | Yes (pipeline mode) | Optional (graceful degradation) |

Agents produce BOTH: structured output (final artifact) + progress updates (live status). They serve different consumers and timelines.

See `agent-communication` skill → "Progress Spine Protocol" for update patterns.

---

## Writing Structured Output

When an agent writes structured output, follow this pattern:

1. Complete the markdown deliverable first (primary)
2. Extract key data from the markdown into the JSON schema
3. Populate all metadata fields
4. Self-validate: check that required fields are non-null
5. Write the JSON file to `{PROJECT_DIR}/{stage}_output.json`
6. If a required field can't be populated, set it to `null` and add a note in the markdown

**This step is supplementary** — the markdown document is the primary deliverable. The JSON enables automated pipeline tracking and downstream agent consumption.
