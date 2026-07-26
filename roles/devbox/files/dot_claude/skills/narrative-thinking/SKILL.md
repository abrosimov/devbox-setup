---
name: narrative-thinking
description: Narrativization and Narrative Studies Principles Framework (NSTD) protocol for turning a source structure into a readable narrative, explanation, or learning route without letting the telling outrun the source. Use when rendering structure as story, writing tutorials or explanations, designing learning routes, grounding LLM/NLG-generated narrative, evaluating rendering quality for a declared use, or policing the engagement-versus-manipulation boundary. Also use when someone leads with "make it inspiring", "just tell the story", or "make it flow" — the skill separates carrier from admitted source. Not to be confused with `fpf-thinking` (systems framing, architecture, first-principles) — NSTD governs the narrative rendering of already-framed material and routes FPF-Core ids back to that sibling skill.
problem: "A fluent narrative is trusted as if it were the source: engagement becomes truth, viewpoint becomes responsibility, generated prose becomes admitted fact."
related: [fpf-thinking]
---

# NSTD-Guided Narrative Thinking

Protocol for using the Narrativization and Narrative Studies Principles Framework (NSTD) as a structured aid for rendering structure as narrative, explanation, tutorial, or learning route — while keeping the telling grounded in, and returnable to, its source.

NSTD is a **DPF** (Domain Principle Framework): a domain satellite of FPF Core with a hard one-way dependency on it. Core never depends back. Edition ref: `NarrativizationAndNarrativeStudiesPrinciplesFramework@2026-06-30`.

---

## Spec Location

Two sibling docs, disjoint id spaces:

- **NSTD doc** — `~/.claude/docs/Narrativization-and-Narrative-Studies-Principles-Framework.md` (~2800 lines). Owns **only** `NSTD.*` ids.
- **FPF-Spec** — `~/.claude/docs/FPF-Spec.md`. Owns all Core ids (`A.*`, `B.*`, `C.*`, `D.*`, `E.*`, `F.*`, `G.*`).

**FPF-id resolution rule.** Because NSTD hard-depends on Core, cross-references *inside* the NSTD doc constantly cite Core ids (e.g. `A.6.3.NAR`, `A.22.CGUS`, `C.33`, `D.1`–`D.5`, `G.11`). Any id that is **not** `NSTD.*` resolves into the sibling `FPF-Spec.md`, not this doc. Follow those ids with the `fpf-thinking` skill (its routing table + Pattern Anatomy). Only `NSTD.*` ids live in the NSTD doc.

**Never load the full file.** Grep by id, then targeted Read. Ids are stable; line numbers, file size, and headings drift edition to edition.

---

## Loading Protocol

1. **Grep the id, not the title** — headers are `## NSTD.<n> - Title` and `### NSTD.<n>:<slot> - Title`. Titles drift; ids and slot numbers do not. Example: `Grep(pattern="^#+ NSTD\\.4:4 ")` lands on the Solution of `NSTD.4`.
2. **Read targeted ranges** — a pattern runs a few hundred lines from `:1` to `:End`; use `:End` as the Read boundary.
3. **Translate jargon in output.** NSTD is heavily jargon-laden (`NarrativeRenderingEpiplexity`, `focalized object`, `actant`, `admitted source basis`, `rendering mediation mode`, `epiplexity`). Respond in plain language. When you must pin a coined term, route to the doc's **own glossary** — `## DPF Precision Restoration And Owner Map` (a 4-col table: Term | Kind and owner | Use | Blocked overread) — rather than inventing a definition.

---

## Pattern Anatomy

NSTD is a pattern language on the same canonical template as FPF (see `fpf-thinking` → Pattern Anatomy for the general "titles vary, numbers don't; grep the id + slot; `:End` bounds the pattern" wisdom). Slot titles (`:6` Bias-Annotation, `:8` Common Anti-Patterns and How to Avoid Them, `:11` SoTA-Echoing) match FPF's — the table below carries them. Two deltas from FPF:

- **No `:0` slot.** The "use-this-when" cue is folded into `:1`, which opens with "Use this pattern when…", "First useful move", "What goes wrong if missed", "Not this pattern when".
- **`:5` Archetypal Grounding** carries "Mature worked slice" + "What this pattern teaches about FPF" sub-slices.

| Slot | Name | Use it for |
|---|---|---|
| `:1` | Problem frame (+ folded entry cue) | Is this the right pattern? |
| `:2` | Problem | The problem addressed |
| `:3` | Forces | Tensions and trade-offs |
| `:4` | **Solution** (largest) | The pattern's core answer |
| `:5` | Archetypal Grounding | Worked slices + FPF-owner teaching |
| `:6` | Bias-Annotation | Bias / assurance notes |
| `:7` | Conformance Checklist | Normative acceptance tests — read this for "what does it require?" |
| `:8` | Common Anti-Patterns and How to Avoid Them | How it fails, how to avoid |
| `:9` | Consequences | What changes, residual risk |
| `:10` | Rationale | Why this pattern |
| `:11` | SoTA-Echoing | Ties to state of the art |
| `:12` | Relations | Cross-refs (mostly Core ids → resolve via FPF-Spec) |
| `:End` | *(sentinel)* | Boundary marker, not content |

---

## Routing Table

Eight patterns, flat single-digit ids. This is the complete set — inspect a pattern's Solution (`:4`) or Conformance Checklist (`:7`) once the situation matches.

| id | Title | Open it when… |
|---|---|---|
| `NSTD.1` | Source-Structure Intake and Narrative Purpose | Starting from a selected source structure + declared use *before* message/theme/engagement. Fires on "make it inspiring / just tell the story". |
| `NSTD.2` | Structure-to-Sequence Ordering | Choosing and justifying the ordering rule that turns non-linear source structure into a readable sequence. |
| `NSTD.3` | Source Mechanism, Event Model, and Coherence | Keeping mechanism / event / dependency / state-change reconstruction intelligible without causal claims outrunning evidence. |
| `NSTD.4` | Voice, Focalization, and Agency | Governing viewpoint / protagonist / actant so they do not fabricate agency, responsibility, or source authority. |
| `NSTD.5` | Engagement, Attention, and Motivation | Using engagement devices *without* turning attention into truth, permission, or authority (persuasion boundary). |
| `NSTD.6` | Declared-Use Narrative Rendering Quality Evaluation | Evaluating one rendering version for one declared use (values, missingness, repair, reopen conditions). |
| `NSTD.7` | Automated Narrativization and Story Planning | Keeping LLM/NLG-generated narrative grounded, constrained, admitted, evaluated, repairable — split generated carrier from admitted source. |
| `NSTD.8` | Learning-Route Narrative Rendering and Reconstruction Return | Designing / evaluating a learning route that preserves source structure, not just examples and analogies. |

### First Practical Entries (fast map)

The doc's `# Readme - First Practical Entries` (five entries) is the quickest situation-to-pattern jump when you are still deciding whether narrative work is even the right entry:

| Readme entry | Situation | Start at |
|---|---|---|
| 1 | Turn a source structure into a narrative route | `NSTD.1` → `NSTD.2` |
| 2 | Repair a fluent-but-misleading narrative | `NSTD.3` / `NSTD.4` / `NSTD.5` (by failure kind), verify with `NSTD.6` |
| 3 | Evaluate rendering quality for a declared use | `NSTD.6` |
| 4 | Use LLM/NLG output safely | `NSTD.7` |
| 5 | Build a learning route | `NSTD.8` |

Two other in-doc aids, pointed at, not duplicated: `## Pattern Index` (id → title → first-use table) and the Table-of-Contents "Work trigger → Map to open" table (routes to the four support maps and the glossary).

---

## Artifact Recipes

Produce concrete artifacts, not just prose. Format mirrors `fpf-thinking` recipes (When / source id / Produce).

### 1. Narrative Route Card
**When:** Turning a source structure into a readable narrative or explanation.
**Source:** `NSTD.1`, `NSTD.2`.
**Produce:** declared use · selected source structure + admitted source basis · ordering rule (and why) · source-return points (where the reader must go back to the basis or governing pattern) · what is carrier vs. admitted.

### 2. Rendering-Quality Evaluation
**When:** Judging whether one rendering version is good enough for one declared use.
**Source:** `NSTD.6`.
**Produce:** the one rendering version + declared use · `NarrativeRenderingEpiplexity` values (ordering recoverability, source-return readiness, bounded engagement, owner-routed claims) · missingness rules · repair actions · reopen conditions.

### 3. LLM Narrativization Grounding
**When:** Admitting generated (LLM/NLG) narrative into a reliance-bearing use.
**Source:** `NSTD.7`.
**Produce:** split of generated carrier vs. admitted source basis · grounding constraints applied · admission decision (what is claimed vs. merely fluent) · evaluation via recipe 2 · repair / regeneration path.

### 4. Learning-Route Design
**When:** Designing or evaluating a tutorial / learning route.
**Source:** `NSTD.8`, evaluate with `NSTD.6`.
**Produce:** target source structure to preserve · route steps · reconstruction-return points (where the learner rebuilds the source structure, not just recalls examples) · where analogy/example ends and source structure resumes.

---

## Anti-Patterns

Harvested from the Preface owner-routing discipline (~L115), per-pattern `:8` slots, and the generic navigation rules.

| Anti-Pattern | Why it fails | Instead |
|---|---|---|
| Engagement treated as truth | Attention is not evidence | Bound engagement (`NSTD.5`); route truth claims to their owner |
| Viewpoint treated as responsibility | Focalization is not accountability | Govern voice/agency (`NSTD.4`); responsibility routes to Core `A.13`/`D.*` |
| Protagonist treated as a role | Story-protagonist is not `U.Role` | Keep protagonist a narrative device; role claims → FPF-Core |
| Actant treated as a role assignment | Narrative actant is not `U.RoleAssignment` | Keep actant a narrative device; assignment → FPF-Core |
| Generated fluency treated as admission | LLM prose is carrier, not admitted source | Split carrier from admitted basis (`NSTD.7`) before relying |
| Learning route treated as the source framework | A route is a rendering, not the source | Preserve reconstruction return (`NSTD.8`) |
| Improving before evaluating | "Beautiful in general" is not fitness for a declared use | Evaluate one version for one use first (`NSTD.6`) |
| Loading the full 268KB file | Floods context | Grep the `NSTD.*` id, Read the pattern range |
| Following a Core id inside the NSTD doc | `A.*`/`B.*`/`C.*`… live in FPF-Spec, not here | Resolve non-`NSTD.*` ids via `fpf-thinking` + FPF-Spec |
| Using NSTD jargon in output | User asked for plain language | Translate; pin coined terms via the doc's glossary map |

---

## Integration Notes

- **Relationship to `fpf-thinking`.** Disjoint problem surfaces. FPF frames the problem and owns the systems/architecture/first-principles vocabulary; NSTD renders already-framed material as narrative. NSTD's `:12` Relations and support maps hand Core ids **back** to FPF-Spec — follow them with `fpf-thinking`. Core never depends on NSTD.
- **`/techne-think`.** When the user asks to explain, tell the story of, tutor, or make readable an already-structured subject — or to check whether a narrative overreaches its source — activate this skill's routing table. When the problem is still being framed (what is this system, which options, is X causing Y), that is `fpf-thinking`.
- **Output routing.** The recipe artifacts above are conversational by default — deliver them inline. Persist to a file only when the user asks (or names a ticket); if persisting, follow the `fpf-thinking` Artifact Persistence routing rather than re-inventing paths.
- **Drift monitoring.** Both docs evolve; ids are the stable handle. If pattern content or slot wording seems stale, check the edition ref and header lines rather than trusting cached line numbers. This mirrors the shared drift discipline in `fpf-thinking`.
