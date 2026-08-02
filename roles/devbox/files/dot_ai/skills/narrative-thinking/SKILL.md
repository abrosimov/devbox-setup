---
name: narrative-thinking
description: Use the Narrativization and Narrative Studies Principles Framework (NSTD) to turn an admitted source structure into a readable narrative, explanation, tutorial, or learning route without letting fluency outrun evidence. Use for narrative ordering, viewpoint and agency, bounded engagement, generated narrative, rendering-quality evaluation, and source-return design. Use fpf-thinking instead when the problem itself is not yet framed.
---

# NSTD-guided narrative thinking

Use NSTD to render an already-framed source for a declared human use. Keep the source, the selected
structure, and the narrative carrier distinct.

## References

Resolve both paths relative to this `SKILL.md` through the sibling `fpf-thinking` skill:

- `../fpf-thinking/references/Narrativization-and-Narrative-Studies-Principles-Framework.md` owns
  `NSTD.*` ids.
- `../fpf-thinking/references/FPF-Spec.md` owns FPF Core ids `A.*` through `G.*`.

NSTD depends on FPF Core; Core does not depend on NSTD. When an NSTD relation cites a non-`NSTD.*`
id, resolve it through `fpf-thinking` and the Core reference.

Never load either reference in full. Search for an anchored id, enumerate the matching headings,
then read only the range ending at that pattern's `:End` marker. Use distinctive slot titles rather
than assuming a slot number.

## Workflow

1. Confirm that the live task is narrative rendering. If the system, claim, evidence, or decision
   is still being framed, use `fpf-thinking` first.
2. Name the admitted source basis, the selected source structure, the intended reader or listener,
   and the declared use.
3. Choose the smallest matching `NSTD.*` pattern from the index below.
4. Read its `Solution` and, for reliance-bearing output, its `Conformance Checklist`.
5. Produce the smallest rendering or evaluation that serves the declared use. Keep loss,
   uncertainty, and source-return points visible.
6. State what came from the source, what was selected or reordered, and what remains a narrative
   device rather than evidence or authority.

Do not expose private chain-of-thought. Present the selected route, source basis, important choices,
limitations, and concise rationale.

## Pattern index

| Pattern | Use when |
|---|---|
| `NSTD.1` | Establishing source-structure intake and narrative purpose before choosing a message or theme |
| `NSTD.2` | Choosing the sequence that turns non-linear source structure into a readable route |
| `NSTD.3` | Preserving mechanism, events, dependencies, or state changes without inventing causality |
| `NSTD.4` | Governing voice, viewpoint, focalisation, protagonist, or agency cues |
| `NSTD.5` | Using engagement and motivation without converting attention into truth or permission |
| `NSTD.6` | Evaluating one rendering version for one declared use |
| `NSTD.7` | Grounding and admitting LLM or NLG-generated narrative |
| `NSTD.8` | Designing a learning route that lets the learner reconstruct the source structure |

Fast routes:

- New narrative or explanation: `NSTD.1` then `NSTD.2`.
- Fluent but misleading narrative: choose `NSTD.3`, `NSTD.4`, or `NSTD.5`, then verify with
  `NSTD.6`.
- Quality evaluation: `NSTD.6`.
- Generated narrative: `NSTD.7`, then `NSTD.6` if it will be relied on.
- Tutorial or learning path: `NSTD.8`, evaluated with `NSTD.6`.

## Output forms

### Narrative route

Include the declared use, admitted source basis, selected structure, ordering rule, preserved and
lost structure, and explicit points where the reader must return to the source.

### Rendering-quality evaluation

Identify one exact rendering version and one declared use. Evaluate ordering recoverability,
source-return readiness, evidence and owner routing, bounded engagement, missingness, repair actions,
and reopen conditions.

### Generated narrative grounding

Separate generated carrier from admitted source, identify grounding constraints, state what is
admitted versus merely fluent, and define the repair or regeneration path.

### Learning route

Name the source structure the learner must reconstruct, the route steps, reconstruction-return
points, and where an analogy or example ends and the source structure resumes.

## Boundaries

- Engagement is not evidence, authority, permission, or assurance.
- Viewpoint, protagonist, and actant are narrative devices, not responsibility assignments.
- Generated fluency is not admission into a reliance-bearing use.
- A learning route is a rendering of the source, not the source framework itself.
- Evaluate one exact version for one declared use before claiming improvement.
- Translate specialised vocabulary into plain language; use a coined term only when the distinction
  matters.
- Default to an inline result. Persist a file only when the user asks or the task explicitly requires
  one, using the repository's existing conventions.
