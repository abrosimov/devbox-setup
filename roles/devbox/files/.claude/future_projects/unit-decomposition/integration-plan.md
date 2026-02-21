# Integration Plan: Atomic Implementation Units

## Prerequisites

- [ ] RAG agent operational (`/Users/kirillabrosimov/Projects/agentic-rag-mcp/`)
- [ ] RAG can analyze codebase structure (file tree, types, interfaces)
- [ ] RAG can find exemplar patterns (similar code in existing codebase)

## Phase 1: Schema (no behavior change)

### 1.1 Add unit spec schema

- **File**: `schemas/unit_spec.schema.json` (NEW -- copy from this directory)
- **Change**: Add the JSON Schema for unit specifications
- **Test**: `bin/validate-pipeline-output` should accept the new schema

### 1.2 Extend execution DAG schema

- **File**: `schemas/execution_dag.schema.json`
- **Change**: Add optional `unit_id` field to DAG node objects
- **Test**: Existing DAGs without `unit_id` still validate

### 1.3 Extend stream completion schema

- **File**: `schemas/stream_completion.schema.json`
- **Change**: Add optional `units_completed` array to track per-unit status
- **Test**: Existing completions without `units_completed` still validate

## Phase 2: Planner produces units

### 2.1 Update Go implementation planner

- **File**: `agents/implementation_planner_go.md`
- **Change**: Add "Implementation Units" section to plan template. Within each Work Stream, planner produces a `units` array with: id, title, layer, depends_on_units, requirements, description, verification, codebase_anchor
- **Key**: The planner uses RAG to find codebase anchors for each unit
- **Test**: Run `/plan` on a multi-FR feature and verify units appear in plan_output.json

### 2.2 Update Python implementation planner

- **File**: `agents/implementation_planner_python.md`
- **Change**: Same as 2.1 adapted for Python verification commands (`ruff check`, `mypy`, `pytest`)
- **Test**: Same as 2.1

### 2.3 Update structured output skill

- **File**: `skills/structured-output/SKILL.md`
- **Change**: Add `units` array to the `plan_output.json` schema documentation
- **Test**: Review that plan_output.json examples include units

## Phase 3: Orchestrator handles units

### 3.1 Update /implement command

- **File**: `commands/implement.md`
- **Change**: Support `--unit U-001` flag for single-unit execution. When a unit ID is provided, the SE agent receives only that unit's spec plus completed-units context.
- **Test**: `/implement --unit U-001` spawns SE with unit-scoped prompt

### 3.2 Update /full-cycle command

- **File**: `commands/full-cycle.md`
- **Change**: Phase 4 gains unit-level DAG construction:
  1. Read units from plan_output.json
  2. Build per-unit DAG (topological sort)
  3. Execute foundation units sequentially
  4. Execute logic units sequentially
  5. Execute vertical-slice units in parallel (independent ones)
  6. Micro-commit after each unit (`wip(PROJ-123): U-NNN title`)
  7. Write `units_execution_log.md`
  8. After review gate: squash micro-commits via `git reset --soft`
- **Test**: Run `/full-cycle` on a feature with 3+ FRs, verify per-unit execution and squash

### 3.3 Update agent communication skill

- **File**: `skills/agent-communication/SKILL.md`
- **Change**: Update Artifact Registry to include unit specs. Update Work Stream Handoffs to document per-unit context passing.
- **Test**: Review that the handoff protocol covers unit-level handoffs

## Phase 4: Verification

### 4.1 End-to-end test

- Run `/full-cycle` on a real multi-FR feature
- Verify: units appear in plan, DAG is built, SE receives one unit at a time, verification gates work, parallel units actually parallelize, squash produces clean history

### 4.2 Backward compatibility test

- Run `/full-cycle` on a plan WITHOUT units
- Verify: falls back to current monolithic behavior without errors

## Summary

| Phase | Files | Complexity | Depends On |
|-------|-------|-----------|-----------|
| Phase 1: Schema | 3 (1 new, 2 modified) | Low | Nothing |
| Phase 2: Planner | 3 modified | Medium | Phase 1 + RAG agent |
| Phase 3: Orchestrator | 3 modified | High (especially full-cycle.md) | Phase 2 |
| Phase 4: Verification | 0 (testing only) | Medium | Phase 3 |

Total: ~9 files, heaviest change in `commands/full-cycle.md`.
