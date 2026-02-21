# ADR-001: Atomic Implementation Units with DAG-Ordered Execution

**Status**: Accepted (pending RAG dependency)
**Date**: 2026-02-22

## Context

The pipeline has a granularity gap between the Implementation Planner (coarse Work Streams) and the Software Engineer agent (monolithic implementation). This causes:

1. Cascading refactoring when later FRs break earlier implementations within the same stream
2. No verification gates between requirements within a stream
3. No parallelism for independent requirements within the same stream
4. Entire stream restarts on failure

Research from MetaGPT (ICLR 2024), Spotify Honk (1500+ PRs), Anthropic's harness, Google Small CLs, and Factory.ai converges on contract-first decomposition with micro-commits and DAG-ordered execution.

## Decision

**Option C: Hybrid** -- extend the planner to produce atomic units within work streams, extend the orchestrator to build per-unit DAGs with micro-commits and squash-on-complete.

No new agent. The planner handles decomposition (WHAT), the orchestrator handles execution (HOW).

### Unit Model

Each unit has a layer classification:

| Layer | Purpose | Verification Gate |
|-------|---------|------------------|
| `foundation` | Types, interfaces, repo stubs | compile |
| `logic` | Service/business logic | compile + lint |
| `vertical-slice` | Complete feature (handler + test) | compile + lint + test |
| `integration` | Cross-stream integration | full suite |

Foundation locks types before logic. Logic locks before slices. This is contract-first decomposition.

### Execution Model

- SE agent receives ONE unit at a time (not the whole plan)
- Per-unit verification: compile -> lint -> test (layer-dependent)
- Micro-commit after each unit: `wip(PROJ-123): U-001 description`
- Independent vertical slices run in PARALLEL (separate SE agent Tasks)
- Parallel coding, sequential commits (orchestrator serializes)
- Squash-on-complete: `git reset --soft` + semantic commit after review gate
- Audit trail preserved in `units_execution_log.md` before squash

### Backward Compatible

- Streams without `units` arrays -> current monolithic behavior
- 1-unit streams allowed (near-zero overhead)
- Always decompose unless pure refactoring/bugfix/config

## Alternatives Considered

| Option | Description | Why Not |
|--------|-------------|---------|
| A: New Task Decomposer Agent | Separate agent between planner and SE | Unnecessary entity; planner already has context; lossy handoff; additional cost |
| B: Expand Planner Only | Planner produces units but orchestrator unchanged | Doesn't achieve per-unit execution and verification |

## Resolved Decisions

### 1. Cross-stream unit dependencies: No

API contract stream is the synchronization point between frontend/backend. Once agreed, agents work independently. Within-stream units can depend on each other. Between-stream deps use the existing `depends_on` field on work streams.

### 2. File-lock enforcement: Advisory

SE documents cross-unit modifications in a structured table in its work log. Reviewer checks. Hard enforcement would block legitimate additive modifications (e.g., adding a method to a type from a foundation unit).

### 3. Squash strategy: git reset --soft

`git reset --soft $PRE_EXECUTION_SHA` + recommit. Interactive rebase is forbidden in the agent system. Parallel units code concurrently but commit sequentially. Audit trail in `units_execution_log.md`.

### 4. Granularity threshold: Always decompose

1-unit streams are fine (near-zero overhead). Only skip for refactoring/bugfix/config. Estimated line counts are unreliable -- let the planner naturally produce however many units the feature needs.

### 5. No new agent (Hybrid architecture)

Planner produces units (WHAT). Orchestrator builds DAG and handles execution (HOW). A separate decomposer would re-derive context the planner already has.

**Future reconsideration**: If the RAG system develops codebase analysis capabilities exceeding what the planner can do, a dedicated decomposer agent may become worthwhile. The unit spec format is producer-agnostic.

## Consequences

### Positive

- Cascading refactoring eliminated: types locked before logic, logic before endpoints
- Failures isolated: broken endpoint doesn't require re-implementing entire service layer
- Parallel execution: independent vertical slices run concurrently
- Better token efficiency: SE works on smaller, focused units
- Cleaner git history: semantic commits after squash
- Targeted retries: only failed unit is retried

### Negative

- Planner slightly more complex (must produce unit decomposition)
- Orchestrator logic substantially more complex (per-unit DAG)
- More git operations (micro-commits, squash)
- Parallel execution introduces merge conflict risk on shared files

### Risks

| Risk | Mitigation |
|------|-----------|
| Poor unit decompositions | Layer classification guardrails; feedback from cross-unit modification metrics |
| Merge conflicts between parallel units | Foundation units create scaffolding first; orchestrator serializes commits |
| Squash failure | `git reset --soft` is simple and reliable; fall back to keeping micro-commits |
| Over-engineering simple features | Backward compatible -- no units = current behavior; 1-unit streams are fine |
