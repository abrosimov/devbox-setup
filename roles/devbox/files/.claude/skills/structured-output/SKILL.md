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
  "metadata": { "agent": "domain-expert", "version": "1.0", "..." : "..." },
  "assumptions": [
    { "id": "A1", "claim": "string", "status": "validated | invalidated | needs_validation", "evidence": "string", "risk_if_wrong": "string" }
  ],
  "domain_model": {
    "entities": [
      { "name": "string", "description": "string", "key_attributes": ["string"], "constraints": ["string"] }
    ],
    "relationships": [
      { "from": "string", "to": "string", "type": "string", "cardinality": "string" }
    ],
    "invariants": ["string"]
  },
  "constraints": [
    { "name": "string", "type": "technical | organisational | external", "impact": "string", "addressed_by_spec": "boolean" }
  ],
  "risks": [
    { "description": "string", "likelihood": "high | medium | low", "impact": "high | medium | low", "mitigation": "string" }
  ],
  "cynefin_classification": "clear | complicated | complex | chaotic | confused"
}
```

### Implementation Planner — `plan_output.json`

```json
{
  "metadata": { "agent": "implementation-planner-*", "version": "1.0", "..." : "..." },
  "requirements": [
    {
      "id": "FR-001",
      "description": "string",
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
  "implementation_order": ["string (FR IDs in suggested order)"],
  "test_scenarios": [
    { "area": "string", "scenario": "string", "inputs": "string", "expected_outcome": "string" }
  ]
}
```

### Designer — `design_output.json`

```json
{
  "metadata": { "agent": "designer", "version": "1.0", "..." : "..." },
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
    "designer": { "status": "...", "output": "design.md", "selected_option": "string | null", "approved_at": null },
    "impl_planner": { "status": "...", "output": "plan.md", "approved_at": null },
    "api_designer": { "status": "...", "output": "api_design.md", "approved_at": null },
    "software_engineer": { "status": "...", "approved_at": null },
    "test_writer": { "status": "...", "approved_at": null },
    "code_reviewer": { "status": "...", "approved_at": null }
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

## Writing Structured Output

When an agent writes structured output, follow this pattern:

1. Complete the markdown deliverable first (primary)
2. Extract key data from the markdown into the JSON schema
3. Populate all metadata fields
4. Self-validate: check that required fields are non-null
5. Write the JSON file to `{PROJECT_DIR}/{stage}_output.json`
6. If a required field can't be populated, set it to `null` and add a note in the markdown

**This step is supplementary** — the markdown document is the primary deliverable. The JSON enables automated pipeline tracking and downstream agent consumption.
