---
name: fpf-thinking
description: First Principles Framework (FPF) protocol for systems thinking, domain modelling, and architectural trade-offs. Use when tackling complex analysis, first-principles reasoning, project characterisation, or naming discipline. Not to be confused with `mcp-sequential-thinking` (step-by-step reasoning) or `diverge-synthesize-select` (option generation + choice) — FPF frames the problem itself.
problem: "Complex systems problems get solved before they are framed, producing well-executed answers to the wrong question."
related: [diverge-synthesize-select, mcp-sequential-thinking]
---

# FPF-Guided Systems Thinking

Protocol for using the First Principles Framework as a structured reasoning aid for complex systems problems.

---

## Spec Location

The full FPF spec is at `~/.claude/docs/FPF-Spec.md`. It is a very large monolith spanning eight Parts A–G and I and grows edition to edition, so **navigate by id, never by absolute line number**. Ids are stable; line counts, file size, and heading counts drift.

**Never load the full file.** Use Grep and targeted Read (offset + limit) to retrieve relevant sections on demand. The routing table below maps problem types to section *ids*; resolve each id to its current line with Grep, then Read from there.

---

## Loading Protocol

From FPF README (July 2026 edition, mandatory):

1. **Use FPF patterns to structure your analysis** — apply the framework's reasoning architecture
2. **Respond in plain language** — no FPF-specific terminology in output unless the user explicitly requests it
3. **FPF steers, you think** — the framework is a scaffold for reasoning, not a substitute for it. Without good problem framing, you get confident nonsense
4. **Enter via a Practical-Use Card, not a pattern id.** The July readme organises entry through fifteen semantic cards (see Card Index below). Recognise the current situation and question, pick the card, then follow its ordinary rhythm: `E.11` (which card) → `E.11.PUA` (apply one direct pattern to the current situation, get the first useful result) → `E.11.PUR` (only when reliance-bearing applicability, recommendation, or coordination among candidate uses is current). Materialise comparison, archive, or ordering records only when a named receiving use relies on them

---

## Pattern Anatomy

FPF is a **pattern language**: nearly every concept section (an id like `A.2.1`, `C.11`, `E.9`) is written to one canonical template. The sub-headings inside a section are addressed with a colon — `A.2.1:4` is the Solution slot of pattern `A.2.1` — and the slot **number** is far more stable than its wording. Knowing the anatomy lets you fetch the one part you need instead of reading the whole pattern.

| Slot | Canonical name | Typical content | Almost always present |
|---|---|---|---|
| `:0` | Use this when | Applicability / entry cue | sometimes |
| `:1` | Problem frame | How the problem is set up | yes |
| `:2` | Problem | The problem addressed | yes |
| `:3` | Forces | Tensions and trade-offs | yes |
| `:4` | **Solution** | The pattern's core answer (largest slot) | yes |
| `:5` | Archetypal Grounding | Worked cases (Tell–Show–Show) | yes |
| `:6` | Bias-Annotation | Bias/assurance notes | yes |
| `:7` | Conformance Checklist | Normative acceptance tests | yes |
| `:8` | Common Anti-Patterns | How it fails, how to avoid | yes |
| `:9` | Consequences | What changes, residual risk | usually |
| `:10` | Rationale | Why this pattern | usually |
| `:11` | SoTA-Echoing | Ties to state of the art | often |
| `:12` | Relations | Cross-references to other patterns | often |
| `:End` | *(sentinel)* | Empty marker — ends the pattern | yes |

How to use the anatomy:

- **Targeted retrieval.** For "what does A.2.1 *require*?" read `A.2.1:7` (Conformance Checklist), not the whole section. For "why?" read `:10` (Rationale). For "how does it connect?" read `:12` (Relations).
- **Titles vary, numbers don't.** Grep the id + slot number (`^#+ C\.11:7 `); do not assume the exact slot wording.
- **`:End` is a boundary, not content** — it marks where a pattern stops. Use it to bound a Read.
- **Not every section is a pattern.** Overview/glossary/front-matter sections (e.g. `A.0`, Part-level intros, Preface) do not follow the template — read them whole.

---

## Routing Table

Two entries exist. **Prefer the Practical-Use Card Index** — it matches the July 2026 readme structure and yields an exact first useful result. Fall back to the semantic Problem → Section Map when the current question does not obviously match any card.

### How to navigate the spec

The spec uses `## Section-ID - Title` headers. **The id is the stable handle; the title drifts** (casing and wording change edition to edition, ids do not). Grep for the id, not the title:
```
Grep(pattern="^#+ A\\.1 ", path="~/.claude/docs/FPF-Spec.md")
```
Then Read with offset/limit from the matched line number (~200-400 lines per section). To jump *inside* a section straight to the slot you need (see Pattern Anatomy above), grep the slot header — e.g. `Grep(pattern="^#+ A\\.2\\.1:4 ")` lands on the Solution of `A.2.1`.

### Practical-Use Card Index (primary entry)

The July 2026 readme organises entry through fifteen semantic cards. Recognise the situation, pick the card, inspect the listed direct patterns' Solutions (`:4`), and stop at the exact first useful result. The card keys below are stable identifiers, not steps — do not read them in order.

| Card key | Situation cue (one line) | Primary direct patterns to inspect |
|---|---|---|
| **ARCHITECTURE** | Problem pressure must become candidate, selected, expected, or actual structures | `C.32.P2S`, `C.30.AD`, `C.32`, `C.32.PAD`, `A.22.CGUS` |
| **WORKING-DOCUMENTS** | Document a participant will use — first pick a branch: meaning, enactment, reliance, or publication | Meaning: `A.6`, `A.3.2`, `A.2.8`, `A.6.RSIR` · Enactment: `A.15.2`, `C.24`, `A.15.5` · Reliance: `A.10`, `B.3`, `A.21` · Publication: `E.17` |
| **OPTION-COMPARISON** | Several options — the current need is comparison frame, archive, front, live pool, published set, or one choice | `A.19.ECS`, `C.18`, `C.19`, `G.5`, `C.11` |
| **PROBLEM-SHAPING** | Vague pressure — how far has articulation actually progressed? | `A.16.1`, `B.4.1`, `B.5.2.0`, `C.22.2` (then `C.22` for TaskSignature) |
| **IMPROVEMENT** | Object should improve, but evaluation purpose/scale/proposal effect is unsettled | `E.22`, `C.25`, `A.19.ECS`, `E.23` (loop stays provisional until `A.22.CGUS` admission) |
| **COSTLY-ACTION** | Expensive, committing, safety-relevant, or hard-to-reverse action | `A.10`, `B.3`, `A.20`, `A.21`, `C.28`, `C.11`, `A.15.5` |
| **TIME** | Rate, rhythm, delay, currentness, or validity-window claim used for action | `C.27`, `G.11` |
| **CAUSAL-USE** | Causal, intervention, effect, or counterfactual language supporting a decision | `C.28` |
| **DESCRIPTION-USE** | Description, view, dashboard, model, report, or publication being created or relied on | `E.17.0`, `A.6.3.RT`, `C.33`, `E.17.ID.CR`, `C.30.AD` |
| **NAMING** | A governed value needs a stable Tech or Plain label across a bounded context | `F.18` (use `F.17` only when publishing term rows) |
| **WORDING** | Fluent sentence hides which object, relation, slot, use position, or claim kind is active | `E.10` (then `F.19` for phrase-level prose, `F.18` for durable naming) |
| **MATHEMATICAL-MODELING** | Could one cheap mathematical lens change the next admissible action? | `C.29` |
| **SOTA-PORTFOLIO** | Need the plural current field of methods, theories, technologies, or sources | `G.2` (then `C.18`, `C.19`, `G.5` as conditional continuations) |
| **DPF-AUTHORING** | Building a reusable FPF-grounded domain or local practice framework edition | `E.4.DPF`, `E.4.PFAD`, `C.30.AD` |
| **SYSTEM-IN-CONTEXT** | System named but the current system question (identity, composition, participation, structures, planned or performed work) is not explicit | `A.1`, `B.1.2`, `C.30`, `A.15.2`, `A.15.1` |

> Each row lists the ordinary walkthrough — inspect only the branch whose stated condition is current in the working project, not every listed pattern. When multiple cards seem plausible, compare their situations and first-result differences in the conversation before opening any pattern body.

### Problem → Section Map (semantic fallback)

Use this when the current question does not obviously match a card key — e.g. cross-cutting theory questions, meta-authoring questions, or historical inspection.

| Problem Type | What You Need | FPF Sections to Read |
|---|---|---|
| **"What is this system/project?"** — Bounding and decomposing a complex entity | Holonic decomposition, boundary definition, context scoping | A.1 (Holonic Foundation), A.1.1 (Bounded Context), A.2 (Role Taxonomy) |
| **"How confident are we in X?"** — Evaluating trust in claims, evidence, assumptions | Trust calculus, evidence graphs, epistemic debt | B.3 (Trust & Assurance F-G-R), A.10 (Evidence Graph), B.3.4 (Evidence Decay) |
| **"How do we define and measure success?"** — Establishing measurable characteristics | Measurement typing, comparability governance, indicators, currentness | A.17-A.18 (Characteristics, CSLC), A.19.CN (CN-frame), G.0 (CG-Spec), G.11 (Currentness) |
| **"What are the options / state of the art?"** — Surveying and comparing alternatives | SoTA packs, method families, portfolio selection, currentness | Part G (G.0-G.10), C.18 (NQD search), C.19 (E/E-LOG), G.11 (Currentness) |
| **"How do parts compose into a whole?"** — Aggregation, composition, emergence | Universal aggregation algebra, cross-scale invariants, mereology | B.1 (Gamma), A.14 (Mereology), A.9 (Cross-Scale), B.2 (Meta-Holon Transition) |
| **"What does this term actually mean?"** — Vocabulary alignment, disambiguation | Term harvesting, sense clustering, bridges, unified term sheets | F.0.1-F.3 (Lexical Principles, Harvesting, Clustering), F.9 (Bridges), F.17 (UTS), F.18 (NameCard) |
| **"How should this evolve?"** — Change management, versioning, lifecycle | Evolution loops, design-run duality, design rationale records, problem-to-work carry-through | B.4 (Evolution Loop), A.4 (Temporal Duality), E.9 (DRR), E.18.1 (P2W Problem-to-Work Carry-Through) |
| **"How to frame the problem?"** — Structuring inquiry, pattern-use rhythm, hypothesis generation | Practical-use guidance, canonical reasoning cycle, abductive loop | E.11 (Practical-Use Guidance), E.11.PUA (Apply Pattern to Situation), E.11.PUR (Applicability & Coordination), B.5 (Reasoning Cycle), B.5.2 (Abductive Loop) |
| **"How to generate creative alternatives?"** — Systematic ideation, portfolio search | Creativity characterization, novelty-quality-diversity, explore-exploit | C.17 (Creativity-CHR), C.18 (NQD-CAL), C.19 (E/E-LOG), B.5.2.1 (Creative Abduction) |
| **"Who does what and why?"** — Roles, responsibilities, accountability | Role-method-work alignment, contextual enactment, separation of duties | A.2 (Roles), A.15 (Role-Method-Work), A.2.1 (Role Assignment), A.13 (Agency) |
| **"How to make this decision auditable?"** — Traceability, rationale capture | Design rationale records, evidence graphs, assurance levels | E.9 (DRR), A.10 (Evidence Graph), B.3.3 (Assurance Levels) |
| **"How to compare across different contexts?"** — Cross-domain alignment with loss awareness | Bridges with congruence levels, cross-context mapping, loss notes | F.9 (Bridges), A.6.9 (Cross-Context Sameness), C.3.3 (KindBridge) |
| **"What are the boundary contracts?"** — Interface discipline, promise vs. work | Boundary norm routing, contract unpacking, service facets | A.6 (Signature Stack), A.6.B (Boundary Norm Square), A.6.C (Contract Unpacking), A.6.8 (Service Polysemy) |
| **"How should an AI agent plan its tool use?"** — Call planning, tool selection, role-bound action | Agentic tool-use calculus, role-method-work alignment | C.24 (Agentic Tool-Use & Call Planning), A.15 (Role-Method-Work), A.13 (Agency Spectrum) |
| **"Which option do we choose (under uncertainty)?"** — Decision-making, selection policy | Decision theory, explore-exploit governance | C.11 (Decision Theory), C.19 (Explore-Exploit), C.18 (NQD search) |
| **"Is X actually causing Y?"** — Causal claims, counterfactuals, intervention | Causal-use questions, causality ladder, identification | C.28 (CausalUse-CAL) |
| **"Will this hold over time?"** — Forecasts, trends, state-vs-rate claims | Temporal claim adequacy, state readings, trends, currentness | C.27 (Temporal Claim Adequacy), G.11 (Currentness) |
| **"What are the ethical trade-offs?"** — Value conflict across levels, bias, mediation | Multi-scale ethics, interlevel conflict, ethical mediation | D.1 (Value Plurality), D.2 (Multilevel Ethics), D.3 (Interlevel Conflict), D.4 (Mediation), D.5 (Bias Audit) |
| **"Design or critique an architecture."** — Structure selection, modularity, synthesis | Grounded architecture, modularity, candidate synthesis, structural adequacy, constraint-governed unfolding | C.30 (Grounded Architecture), C.31 (Modularity), C.32 (Candidate Synthesis), C.33–C.35 (Structural Adequacy), A.22.CGUS (Constraint-Governed Unfolding Structure) |
| **"What kind of problem is this?"** — Problem typing, task signatures | Problem typing, TaskSignature assignment | C.22 (Problem Typing), C.3 (Kinds & Typed Reasoning), C.2 (Epistemic Composition) |
| **"How do we author/quality-gate an FPF pattern?"** — Writing or reviewing patterns | Authoring conventions, quality gates, mechanism introduction | E.8 (Authoring Conventions), E.19 (Pattern Quality Gates), E.20 (Mechanism Introduction), E.10 (Lexical Rules) |
| **"How does culture/organisation evolve?"** — Cultural evolution engineering | Cultural-evolution characterisation and engineering | C.36 (Cultural Evolution) |

> The map is a **starting set, not a table of contents** — it points at the load-bearing sections for common problem types. Most Part A–G/I chapters are *not* listed; when a problem doesn't match a row, Grep the spec's own headers (`^#+ [A-G]\.` ) or its ToC to locate the nearest chapter, then apply the Pattern Anatomy above.

---

## Artifact Recipes

FPF-guided analysis should produce concrete artifacts, not just prose. Below are the key artifact types agents should produce, described in plain language.

### 1. System Characterization Card

**When:** Decomposing a complex system or project.
**FPF source:** A.1, A.1.1, A.2.
**Produce:**

- **Name** — what is this system/entity
- **Boundary** — what is inside vs. outside (and what crosses the boundary)
- **Parts** — sub-systems, components, or sub-domains
- **Roles** — who/what is responsible for what (function, not identity)
- **Context rules** — the local vocabulary, invariants, and assumptions that hold inside this boundary
- **Bridges** — explicit links to other contexts, with notes on what meaning is lost in translation

### 2. Trust Assessment

**When:** Evaluating confidence in a claim, requirement, or assumption.
**FPF source:** B.3, A.10.
**Produce:**

- **Claim** — the statement being assessed
- **Formality (F)** — how rigorous is the backing? (sketch / spec / formal proof)
- **Scope (G)** — where does this claim hold? (this project / this domain / universally)
- **Reliability (R)** — how strong is the evidence? (anecdotal / tested / independently verified)
- **Evidence chain** — what supports this claim, and is there decay risk?
- **Verdict** — unsubstantiated / partially supported / well-evidenced

### 3. Measurement & Comparability Frame

**When:** Defining what "success" or "good" means; comparing alternatives.
**FPF source:** A.17-A.19, G.0.
**Produce:**

- **Characteristics** — what properties matter (and their scale types: ordinal, interval, ratio)
- **Indicators** — how each characteristic is measured
- **Comparability rules** — what can be compared to what, and under which conditions
- **Aggregation policy** — how individual scores compose (no hidden averages)

### 4. Unified Term Sheet (UTS Entry)

**When:** Aligning vocabulary across teams, disciplines, or contexts.
**FPF source:** F.17, F.0.1-F.9.
**Produce:**

- **Term** — the word or phrase
- **Context** — where this sense applies
- **Definition** — precise local meaning
- **Bridges** — how it maps to the same word in other contexts (with loss notes)
- **Aliases** — alternative names for the same concept
- **Anti-senses** — what this term does NOT mean (common confusions)

### 5. Design Rationale Record (DRR)

**When:** Capturing why a decision was made, for future auditability.
**FPF source:** E.9.
**Produce:**

- **Decision** — what was decided
- **Context** — what situation prompted this decision
- **Options considered** — alternatives that were evaluated (portfolio, not single winner)
- **Selection rationale** — why this option, with evidence references
- **Consequences** — what changes and what risks remain
- **Review trigger** — when should this decision be revisited

### 6. Evolution Roadmap

**When:** Planning how a system, process, or body of knowledge should change over time.
**FPF source:** B.4, A.4.
**Produce:**

- **Current state** — where we are (with evidence)
- **Target state** — where we want to be (with measurable characteristics)
- **Evolution steps** — sequence of changes (each auditable)
- **Feedback loops** — how we detect drift and course-correct
- **Evidence refresh** — when to re-validate assumptions

### 7. SoTA Pack

**When:** Surveying the state of the art in a domain or method family.
**FPF source:** Part G.
**Produce:**

- **Scope** — what discipline/domain/method family
- **Traditions** — major schools of thought or approaches
- **Method families** — grouped alternatives with evidence levels
- **Comparison frame** — characteristics used to compare (from Artifact 3)
- **Portfolio** — the set of viable alternatives (not a single "winner")
- **Gaps** — where evidence is missing or stale

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Instead |
|---|---|---|
| Loading the full spec | Floods context, agent can't reason | Grep for section ids, Read targeted ranges |
| Using FPF jargon in output | User asked for plain language; jargon obscures | Translate every FPF concept to everyday terms |
| Treating FPF as a checklist | FPF is generative, not prescriptive | Use patterns to structure thinking, not to tick boxes |
| Applying all sections at once | Overwhelming; most problems need 2-3 sections | Use routing table to select relevant sections only |
| Skipping evidence assessment | Claims without trust evaluation are folklore | Always produce a Trust Assessment for key claims |
| Single-winner conclusions | FPF emphasises portfolios and Pareto fronts | Present options as a set with trade-offs, not "the answer" |
| Reading all 15 Practical-Use Cards before picking one | Each card is a stable identifier, not a step; enumeration wastes context | Recognise the situation, pick one card, follow its ordinary rhythm |
| Conflating `E.11`, `E.11.PUA`, and `E.11.PUR` | They govern different relations — card guidance, pattern application, and applicability/coordination | Use `E.11` to locate the card, `E.11.PUA` to apply one direct pattern, `E.11.PUR` only when reliance-bearing applicability or coordination is current |
| Materialising archive, front, shortlist, or ordering records eagerly | The July readme keeps ordinary comparison conversational | Materialise only when a named receiving use relies on the record |

---

## Integration Notes

- This skill is for **systems thinking**, not code. It does not replace language-specific engineering skills
- Agents should use `mcp__sequentialthinking` alongside FPF for multi-step reasoning
- When the user says "think about X" or uses `/techne-think`, activate this skill's routing table
- The FPF spec evolves — check `~/.claude/docs/FPF-Spec.md` freshness if patterns seem outdated

---

## Artifact Persistence

FPF thinking produces durable artifacts, not just ephemeral reasoning. All thoughts are streamed to console for visibility, then persisted.

### Routing Logic

| Scope | Detection | Location |
|-------|-----------|----------|
| **Ticket-scoped** | Problem mentions Jira issue (e.g., "PROJ-123") or current branch follows convention | `{PROJECT_DIR}/analysis.md` |
| **Cross-cutting decision** | Problem is project-wide, strategic, or spans tickets | `docs/decisions/NNN-<topic>.md` |
| **Cross-cutting design** | Problem is architectural exploration | `docs/design/<topic>.md` |

### File Naming

**Ticket-scoped**: Always `analysis.md` within `{PROJECT_DIR}` — one per ticket/branch.

**Cross-cutting ADRs**: Sequential numbering with semantic slug:
```
docs/decisions/
├── 001-auth-strategy.md
├── 002-database-choice.md
└── 003-caching-approach.md
```

To get next number: `ls docs/decisions/*.md | wc -l` + 1, zero-padded to 3 digits.

**Cross-cutting design docs**: Semantic slug only:
```
docs/design/
├── caching-architecture.md
└── api-versioning.md
```

### Human-Readable Format

All FPF artifacts follow this template:

```markdown
# <Title>

## Context

<!-- What prompted this analysis? Link to ticket if applicable. -->

## Thought Process

### 1. <First thought summary>

<Prose explanation>

### 2. <Second thought summary>

<Prose explanation>

### 3. [Revision] <What was reconsidered>    <!-- Mark revisions -->

<Prose explanation of why previous thinking changed>

### 4. [Branch] <Alternative explored>       <!-- Mark branches -->

<Prose explanation of alternative path>

...

## Conclusion

<!-- Final decision or recommendation -->

## Consequences

<!-- What changes? What risks remain? -->

## Open Questions

- [ ] <Unresolved item 1>
- [ ] <Unresolved item 2>

## Review Trigger

<!-- When should this be revisited? -->
```


### Dialogue Mode

After writing the artifact, offer refinement:

> **Analysis saved to `<path>`.** Want to:
> - **Refine** a specific section?
> - **Extend** the analysis with more depth?
> - **Proceed** to implementation planning?
