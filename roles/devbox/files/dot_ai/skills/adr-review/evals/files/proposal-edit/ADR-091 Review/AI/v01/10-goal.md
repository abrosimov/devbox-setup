---
aliases:
  - ADR-091 v01 goal
---
# ADR-091 v01 — goal

## 1. Purpose recovered
The ADR's author and the architecture committee read the comment once on the ADR page and must
see each ask, verify it and act on it before acceptance.

**The reviewed ADR**: ADR-091 "Nightly export of billing data to the warehouse", page 9191, page
version 3. **Kind**: proposes something not yet built; no part describes implemented behaviour.

**Kind of goal**: desired outcome (a first comment). **Class**: early (first version).

## 2. Method used
GOALS.1, GOALS.2, A.1.STM.

## 3. Usable results
- Review points in this version: `retry-unstated`, `partial-night` (`points.md`).
- Must keep: the facts those points use (`facts.md`).
- Checks:
  - Each ask has its deadline and appears in the top comment. Fails if an ask is only in a later
    section.
  - Each claim has a source the reader can open. Fails if a claim has no link.
  - The ADR's terms (export window, loader, landing tables) are used. Fails if another name is
    used for one of them.

## 4. Limits
None known.

## 5. Next operation
Edit: write `v01/40-comment.md` and `v01/41-changes.md`.
