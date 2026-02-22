---
name: diverge-synthesize-select
description: >
  Diverge-Synthesize-Select (DSS) protocol for generating genuinely diverse solution options,
  synthesising the best elements, and presenting structured choices to the user.
  Complexity-calibrated option counts, forced strategy-axis diversity, explicit synthesis step.
  Triggers on: options, alternatives, diverge, synthesise, explore options, solution space,
  DSS, compare approaches, trade-offs, which approach.
alwaysApply: false
---

# Diverge-Synthesize-Select (DSS) Protocol

Systematic method for generating genuinely diverse alternatives, evaluating them against explicit criteria, synthesising compatible strengths, and presenting a structured choice to the user. Produces `dss_output.json` conforming to `schemas/dss_output.schema.json`.

## When to Use (Complexity Gate)

DSS activates ONLY for Tier 3 decisions with wide scope. Use the decision classification from `code-writing-protocols` skill:

| Decision Type | Action |
|---|---|
| Tier 1 (Routine) | Apply rule directly. Skip DSS. |
| Tier 2 (Standard) | Quick 2-3 option comparison. Skip DSS. |
| Tier 3 Narrow (single function, local pattern) | Use the existing lightweight Tier 3 protocol (5-7 approaches in `code-writing-protocols`). Skip DSS. |
| Tier 3 Wide (architecture, API design, new patterns, multi-component) | **Activate full DSS.** |

### Tier 3 Wide Indicators

- Affects 3+ components or packages
- Introduces a new pattern not yet in the codebase
- API/contract decision visible to consumers
- Technology or framework selection
- Reversing the decision requires significant rework
- User explicitly asks for options (`/options`, "explore alternatives", "what are our options")

---

## Phase 0: Calibrate N

Determine how many options to generate. Base N=5.

### Sub-Factor Scoring

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| **Reversibility** | Easy to change later (config, feature flag) | Moderate effort to change (internal refactor) | Costly to reverse (public API, data model, wire format) |
| **Blast radius** | Single component | Multiple components in one service | Cross-service or user-facing |
| **Novelty** | Well-understood problem, team has done before | Some unknowns, partial precedent | First time for team, no precedent in codebase |
| **Ambiguity** | Requirements are clear | Some open questions | Requirements are actively debated |

### Calibration Formula

```
N = 5 + count(sub_factors where level == "high")
N = clamp(N, 5, 10)
```

Record the calibration in the structured output:

```json
{
  "complexity": {
    "tier": "tier_3_wide",
    "n_options": 7,
    "sub_factors": {
      "reversibility": "high",
      "blast_radius": "medium",
      "novelty": "high",
      "ambiguity": "low"
    }
  }
}
```

---

## Phase 1: Identify Strategy Axes

**Before generating any options**, identify 2-5 orthogonal dimensions along which solutions can vary. This is the anti-superficial-diversity mechanism.

### What Makes a Good Axis

- **Orthogonal**: Changing position on one axis doesn't force a position on another
- **Meaningful**: Different positions lead to genuinely different architectures or trade-offs
- **Binary minimum**: Each axis has at least 2 distinct values

### Examples

| Problem | Axis 1 | Axis 2 | Axis 3 |
|---------|--------|--------|--------|
| Auth system | Session storage (server / client / hybrid) | Identity provider (built-in / external IdP) | Token format (JWT / opaque) |
| Caching layer | Invalidation (TTL / event-driven / hybrid) | Storage (in-process / distributed) | Granularity (per-entity / per-query) |
| Event processing | Delivery (sync / async / hybrid) | Ordering (strict / best-effort) | Consumer model (push / pull) |

### Validation

If fewer than 2 meaningful axes can be identified, the problem is likely Tier 3 Narrow. Fall back to the lightweight protocol in `code-writing-protocols`.

Record axes:

```json
{
  "strategy_axes": [
    { "name": "session storage", "values": ["server-side", "client-side", "hybrid"] },
    { "name": "identity provider", "values": ["built-in", "external IdP"] }
  ]
}
```

---

## Phase 2: Diverge

Generate all N options BEFORE evaluating any. This prevents premature convergence.

### Rules

1. **No evaluation during generation** — list options without judging them
2. **Axis coverage** — each option must occupy a different combination of axis positions. Two options at the same axis position get collapsed into one
3. **Mandatory boring option** — at least one option tagged `boring` (simplest possible approach, per Prime Directive)
4. **Mandatory unconventional option** — at least one option tagged `unconventional` (challenges assumptions about how the problem "should" be solved)
5. **Collapse duplicates** — if two options are superficially different but structurally identical (same axis positions, same trade-offs), merge them

### Format

Each option gets exactly 3 lines maximum:

```
**OPT-1: [Name]** (boring)
[One-sentence summary of the approach]
Differentiator: [What makes this genuinely different]
```

Full list in a single block. No prose between options.

### Output Structure

```json
{
  "options": [
    {
      "id": "OPT-1",
      "name": "Direct DB Queries",
      "axis_position": { "session storage": "server-side", "identity provider": "built-in" },
      "summary": "Store sessions in PostgreSQL, authenticate against local user table.",
      "differentiator": "Zero external dependencies, simplest deployment.",
      "tag": "boring"
    }
  ]
}
```

---

## Phase 3: Evaluate

### Standard Criteria (always apply)

| Criterion | Weight | Question |
|-----------|--------|----------|
| **Simplicity** | high | Which adds least complexity? (Prime Directive) |
| **Consistency** | high | Which matches existing codebase patterns? |
| **Reversibility** | medium | Which is easiest to change later? |
| **Testability** | medium | Which is easiest to test? |

Add domain-specific criteria as needed (e.g., latency, throughput, security posture). Each additional criterion must have an explicit weight.

### Evaluation Protocol

1. **Shuffle evaluation order** — do not evaluate options in generation order (prevents anchor bias toward OPT-1)
2. Score each option against each criterion: `strong`, `adequate`, `weak`
3. **Eliminate** options that:
   - Violate Prime Directive without strong justification
   - Contradict codebase conventions without compelling reason
   - Require changes outside current scope
   - Have any `weak` score on a `high`-weight criterion
4. **Select top 3** — highest overall scores after elimination

### Output Structure

```json
{
  "evaluation": {
    "criteria": [
      { "name": "simplicity", "weight": "high" },
      { "name": "consistency", "weight": "high" },
      { "name": "reversibility", "weight": "medium" },
      { "name": "testability", "weight": "medium" }
    ],
    "eliminated": [
      { "option_id": "OPT-3", "reason": "Weak on consistency — introduces pattern not used elsewhere" }
    ],
    "top_candidates": [
      {
        "option_id": "OPT-1",
        "scores": { "simplicity": "strong", "consistency": "strong", "reversibility": "adequate", "testability": "strong" },
        "strengths": ["Zero dependencies", "Matches existing patterns"],
        "weaknesses": ["Doesn't scale past 10K concurrent sessions"]
      }
    ]
  }
}
```

---

## Phase 4: Synthesise

Extract per-option strengths from the top 3 and check compatibility.

### Synthesis Protocol

1. List each top candidate's primary strength
2. Check pairwise compatibility:
   - Can strength A coexist with strength B architecturally?
   - Do they require contradictory axis positions?
3. If compatible: produce a synthesis option that combines the strengths
4. If not compatible: document the conflicts and confirm the best individual option

### Key Rule

Synthesis is **additional**, not a replacement. The top 3 individual options remain valid choices. Synthesis is offered as a bonus option when strengths are genuinely combinable.

### When Synthesis Is NOT Viable

This is a valid and common outcome. Document why:

```json
{
  "synthesis": {
    "viable": false,
    "description": "OPT-1's server-side sessions are architecturally incompatible with OPT-4's stateless JWT approach. No meaningful combination exists.",
    "conflicts": ["Server-side session state contradicts stateless token design"]
  }
}
```

Do NOT force a Frankenstein hybrid just to have a synthesis option.

---

## Phase 5: Present and Select

### Presentation Format

```markdown
## DSS Analysis: [Problem Statement]

### Strategy Axes
| Axis | Values |
|------|--------|
| [name] | [value1], [value2], ... |

### All Options (N generated, M after dedup)
| ID | Name | Tag | Key Differentiator |
|----|------|-----|--------------------|
| OPT-1 | ... | boring | ... |
| OPT-2 | ... | standard | ... |
| ... | | | |

### Top 3

**OPT-X: [Name]**
- Strengths: ...
- Weaknesses: ...
- Best when: [scenario]

**OPT-Y: [Name]**
- Strengths: ...
- Weaknesses: ...
- Best when: [scenario]

**OPT-Z: [Name]**
- Strengths: ...
- Weaknesses: ...
- Best when: [scenario]

### Synthesis
[Description of combined approach, or "Not viable because: ..."]

### Recommendation
**OPT-X** because [specific reasoning].

**[Awaiting your decision]** — Pick an option number, pick the synthesis, describe a custom combination, say "more options", or say "different axes".
```

### User Response Handling

| User Says | Action |
|-----------|--------|
| "OPT-3" / "option 3" / "3" | Record selection, proceed |
| "synthesis" / "the combined one" | Record synthesis selection, proceed |
| Custom combination description | Record as `choice: "custom"`, capture rationale |
| "more options" | Generate N more along under-explored axis positions |
| "different axes" | Re-run Phase 1 with user-suggested axes |
| Follow-up question | Answer, keep waiting for selection |

---

## Phase 6: Record Selection

Write `dss_output.json` to `{PROJECT_DIR}/` conforming to `schemas/dss_output.schema.json`.

```json
{
  "selected": {
    "choice": "OPT-2",
    "rationale": "Best balance of simplicity and scalability for current requirements.",
    "decided_by": "user"
  }
}
```

### Pipeline Mode

In `PIPELINE_MODE=true`, DSS still presents options to the user. Tier 3 Wide decisions inherently require human input — autonomous selection is not permitted. Set `decided_by: "pending"` and escalate.

---

## Context Window Protection

### During Generation

- Each option: 3 lines maximum (name, summary, differentiator)
- No prose between options
- Evaluation matrix: tabular, not narrative

### After Selection

- Only the chosen approach returns to the parent agent/conversation
- Full option list and evaluation persist in `dss_output.json`
- Other options are NOT carried forward in conversation context

### Large Option Sets (N > 7)

Present the all-options summary table (1 line each), then expand only the top 3. Do not expand eliminated options unless the user asks.

---

## Anti-Patterns

| Anti-Pattern | Description | Prevention |
|---|---|---|
| **Superficial diversity** | Options differ only in naming or surface details, not structure | Strategy axes force orthogonal variation. Collapse duplicates. |
| **Option theatre** | Generating options to justify a predetermined choice | Axes identified BEFORE options. Mandatory boring + unconventional tags. Shuffled evaluation. |
| **Context bloat** | Expanding all N options in detail | 3-line cap per option. Only top 3 expanded. JSON for persistence. |
| **Synthesis worship** | Forcing a hybrid when strengths are incompatible | Synthesis viability check. "Not viable" is a valid outcome. |
| **Anchor bias** | First option gets disproportionate favour | Shuffled evaluation order. Boring option required (often not first). |
| **Skipping the gate** | Using DSS for Tier 1/2 decisions | Complexity gate check. Tier 3 Narrow uses lightweight protocol. |
| **Axis gaming** | Choosing axes that make a preferred option win | Axes must be identified before options. User can request "different axes". |
