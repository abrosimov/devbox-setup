# Unit Decomposition Integration

**Status**: Waiting for dependency (RAG agent at `/Users/kirillabrosimov/Projects/agentic-rag-mcp/`)
**ADR**: See `adr-001-atomic-units.md`
**Date**: 2026-02-22

## What This Is

Design and integration plan for adding **atomic implementation units** to the agent pipeline. Currently, the Implementation Planner produces coarse Work Streams and the SE agent implements them in one monolithic pass. This causes cascading refactoring when later requirements break earlier implementations.

The solution: decompose Work Streams into small, DAG-ordered units with per-unit verification gates. Independent units run in parallel.

## Dependency: RAG Agent

The decomposition requires codebase intelligence that a RAG system provides:
- Finding similar patterns in the existing codebase (exemplar anchoring)
- Understanding file structure and module boundaries
- Identifying type definitions, interface signatures, and their consumers
- Detecting which files a new feature needs to create or modify

The RAG project lives at `/Users/kirillabrosimov/Projects/agentic-rag-mcp/`. Its `docs/` directory contains the full research and architecture decisions that inform this integration.

## When RAG Is Ready

1. Read `integration-plan.md` for the ordered list of file changes
2. Copy `unit-spec-schema.json` to `schemas/unit_spec.schema.json`
3. Modify the planner agents to produce units (using RAG for codebase analysis)
4. Modify the orchestrator commands to handle per-unit DAG execution
5. Update structured output schemas
6. Test with a multi-FR feature on a real project

## Files in This Directory

| File | Purpose |
|------|---------|
| `README.md` | This file -- overview and dependency tracking |
| `adr-001-atomic-units.md` | Architecture Decision Record -- the full design |
| `integration-plan.md` | Ordered list of files to modify with change descriptions |
| `unit-spec-schema.json` | JSON Schema for unit specifications (ready to deploy) |
