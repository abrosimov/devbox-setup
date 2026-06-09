# Proposal: Implementation Plan as an Obsidian-style Vault

**Status**: proposal (not yet implemented)
**Scope**: the `implementation-planner` agent only — its **output** form (and, later, its
input and planning process). Orchestration, workflow, and downstream consumers are
explicitly **out of scope** for this proposal.

---

## Problem

The planner currently emits two parallel representations of the same plan:

- `plan.md` — prose (human-readable)
- `plan_output.json` — `work_streams` + `parallelism_groups` (machine-readable DAG)

Two issues fall out of this:

1. **No schema** backs `plan_output.json` (it is the only structured agent output
   without a file in `schemas/`), so its shape is unvalidated.
2. **No reconciliation** between the prose and the JSON — they are written in one
   agent pass and can silently drift. The DAG actually lives in three places
   (prose, `plan_output.json`, and the orchestrator's `execution_dag.json`).

## Idea

Replace the `plan.md` + `plan_output.json` pair with a **directory of interlinked
prose notes** under `implementation_plans/<spec-name>/`. Each note carries:

- **YAML frontmatter** — metadata + graph edges (machine-readable)
- **`[[wikilinks]]`** — the same edges, navigable by a human / Obsidian graph view

The notes *are* the output. There is no separate JSON. The DAG is derived from
frontmatter + links. The only consistency check that remains is **"frontmatter edges ≡
body wikilinks"** — a structural comparison, not prose parsing.

This also helps the original brainstorm goals: small focused notes mean an agent reads
only what it needs (less context pollution), and phase notes give a natural home for
iterative planning (skeleton → PoC → MVP → growth).

---

## Output structure

```
implementation_plans/PROJ-123-widget-management/
├── index.md                      # MOC: entry point, overview, links to everything
├── requirements/
│   ├── FR-1-create-widget.md
│   ├── FR-2-get-widget.md
│   └── FR-3-list-widgets.md
├── work-streams/
│   ├── WS-1-schema.md
│   ├── WS-2-backend.md
│   └── WS-3-api.md
├── phases/
│   └── phase-1-mvp.md
└── notes/
    ├── assumptions.md
    ├── open-questions.md
    └── security.md
```

**Granularity**: one note = one FR / one WS / one phase. Acceptance criteria live
inside their FR note (no note explosion). `assumptions` / `open-questions` / `security`
are single list-notes.

### `index.md`

```markdown
---
type: plan
id: PROJ-123
feature: Widget management
stack: go
created: 2026-06-07
status: draft
phases: ["[[phase-1-mvp]]"]
---

# Widget Management

One-paragraph overview from the user's perspective.

## Requirements
- [[FR-1-create-widget]] — create a widget
- [[FR-2-get-widget]] — get by id
- [[FR-3-list-widgets]] — list with pagination

## Work streams
- [[WS-1-schema]] · [[WS-2-backend]] · [[WS-3-api]]

## Context
[[assumptions]] · [[open-questions]] · [[security]]
```

### `requirements/FR-1-create-widget.md`

```markdown
---
type: requirement
id: FR-1
title: Create widget
agent_hint: backend
satisfied_by: ["[[WS-2-backend]]"]
status: draft
---

# FR-1 · Create widget

What the system does, from the user's perspective. Prose.

## Inputs
| Field | Type | Constraints |
|-------|------|-------------|
| name | string | required, 1–100 |
| description | string | optional, ≤500 |

## Behaviour
1. ...
2. ...

## Error cases
| Condition | Expected |
|-----------|----------|
| empty name | 400 "name is required" |

## Acceptance
**AC-1** — Given valid input, When create, Then 201 + generated id.
**AC-2** — Given empty name, When create, Then 400 "name is required".

Implemented by [[WS-2-backend]].
```

### `work-streams/WS-2-backend.md` — the DAG is encoded here

```markdown
---
type: work_stream
id: WS-2
title: Backend logic
agent: software-engineer-go
command: /implement
phase: "[[phase-1-mvp]]"
requirements: ["[[FR-1-create-widget]]", "[[FR-2-get-widget]]"]
depends_on: ["[[WS-1-schema]]"]
status: draft
---

# WS-2 · Backend logic

Prose: what this stream does, its boundaries, what the SE should watch for.

## Requirements
- [[FR-1-create-widget]]
- [[FR-2-get-widget]]

## Depends on
- [[WS-1-schema]]
```

DAG edges appear **twice**: in `depends_on` (frontmatter, for machines) and in the
`## Depends on` section (wikilinks, for humans / graph view). The redundancy is
deliberate — it is what makes a drift *detectable* (see consistency check below).

### `phases/phase-1-mvp.md`

```markdown
---
type: phase
id: phase-1-mvp
title: MVP
order: 1
work_streams: ["[[WS-1-schema]]", "[[WS-2-backend]]", "[[WS-3-api]]"]
---

# Phase 1 · MVP

What this increment includes and why. Prose.
```

### `notes/assumptions.md` (same pattern for open-questions, security)

```markdown
---
type: assumptions
---

# Assumptions

| # | Assumption | Impact if wrong | Resolved? |
|---|-----------|-----------------|-----------|
| A-1 | names are not unique | duplicates possible | ask |
```

---

## Validation (what becomes checkable)

A `validate-plan-vault` step (parse frontmatter + `\[\[([^\]]+)\]\]`):

1. **Frontmatter schema per `type`** (requirement / work_stream / phase / plan / notes) —
   this replaces the missing `plan_output.schema.json`.
2. **Link integrity** — every `[[target]]` resolves to an existing note; no orphans.
3. **Consistency** — frontmatter `depends_on` (and `requirements`) equals the set of
   wikilinks in the corresponding body section. *This is the only prose↔structure check
   that remains.*
4. **DAG invariant** — `depends_on` is acyclic; a topological order exists.
5. **Coverage** — every FR is `satisfied_by` ≥1 WS; every WS belongs to a phase; every
   AC traces to an FR.

The existing `pre-plan-code-guard` hook extends from `plan.md` to
`implementation_plans/**/*.md` (no source code in any plan note).

---

## Decisions captured so far

- **Output form**: `implementation_plans/<spec-name>/` vault of prose notes. **Decided.**
- **DAG**: stays, but encoded in frontmatter + wikilinks (no standalone JSON DAG).
- **No `plan_output.json`** — the vault is the single source of truth.
- **Granularity**: one note per FR / WS / phase; AC inside FR notes.

## Open / deferred (not part of this proposal)

- **Input**: what the planner reads (still `spec.md` for now — to be detailed).
- **Planning process**: how the planner builds the vault (to be detailed).
- **Orchestration / workflow / downstream consumers**: out of scope. If/when this lands,
  a separate decision is needed on whether consumers read the vault directly or a
  compiler renders a derived artifact for them.
- **Wikilink portability**: Obsidian `[[ ]]` is not rendered as links by GitHub —
  accepted trade-off for graph-view ergonomics (revisit if needed).
