---
name: fpf-thinking
description: First Principles Framework (FPF) protocol for systems thinking, domain modelling, and architectural trade-offs. Use when tackling complex analysis, first-principles reasoning, project characterisation, or naming discipline. Not to be confused with `mcp-sequential-thinking` (step-by-step reasoning) or `diverge-synthesize-select` (option generation + choice) — FPF frames the problem itself.
---

# FPF-Guided Systems Thinking

Protocol for using the First Principles Framework as a structured reasoning aid for complex systems problems.

---

## Spec Location

The full FPF spec is at `~/.claude/docs/FPF-Spec.md` (~94,000 lines, ~9.3MB, ~7,000 headings across eight Parts A–G and I). The spec grows continuously — it roughly doubled between two editions — so treat every line count as approximate and **navigate by id, never by absolute line number**.

**Never load the full file.** Use Grep and targeted Read (offset + limit) to retrieve relevant sections on demand. The routing table below maps problem types to section *ids*; resolve each id to its current line with Grep, then Read from there.

---

## Loading Protocol

From FPF README (mandatory):

1. **Use FPF patterns to structure your analysis** — apply the framework's reasoning architecture
2. **Respond in plain language** — no FPF-specific terminology in output unless the user explicitly requests it
3. **FPF steers, you think** — the framework is a scaffold for reasoning, not a substitute for it. Without good problem framing, you get confident nonsense

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

When facing a complex problem, identify the problem type and read the corresponding FPF sections.

### How to navigate the spec

The spec uses `## Section-ID - Title` headers. **The id is the stable handle; the title drifts** (casing and wording change edition to edition, ids do not). Grep for the id, not the title:
```
Grep(pattern="^#+ A\\.1 ", path="~/.claude/docs/FPF-Spec.md")
```
Then Read with offset/limit from the matched line number (~200-400 lines per section). To jump *inside* a section straight to the slot you need (see Pattern Anatomy below), grep the slot header — e.g. `Grep(pattern="^#+ A\\.2\\.1:4 ")` lands on the Solution of `A.2.1`.

### Problem → Section Map

| Problem Type | What You Need | FPF Sections to Read |
|---|---|---|
| **"What is this system/project?"** — Bounding and decomposing a complex entity | Holonic decomposition, boundary definition, context scoping | A.1 (Holonic Foundation), A.1.1 (Bounded Context), A.2 (Role Taxonomy) |
| **"How confident are we in X?"** — Evaluating trust in claims, evidence, assumptions | Trust calculus, evidence graphs, epistemic debt | B.3 (Trust & Assurance F-G-R), A.10 (Evidence Graph), B.3.4 (Evidence Decay) |
| **"How do we define and measure success?"** — Establishing measurable characteristics | Measurement typing, comparability governance, indicators | A.17-A.18 (Characteristics, CSLC), A.19.CN (CN-frame), G.0 (CG-Spec) |
| **"What are the options / state of the art?"** — Surveying and comparing alternatives | SoTA packs, method families, portfolio selection | Part G (G.0-G.10), C.18 (NQD search), C.19 (E/E-LOG) |
| **"How do parts compose into a whole?"** — Aggregation, composition, emergence | Universal aggregation algebra, cross-scale invariants, mereology | B.1 (Gamma), A.14 (Mereology), A.9 (Cross-Scale), B.2 (Meta-Holon Transition) |
| **"What does this term actually mean?"** — Vocabulary alignment, disambiguation | Term harvesting, sense clustering, bridges, unified term sheets | F.0.1-F.3 (Lexical Principles, Harvesting, Clustering), F.9 (Bridges), F.17 (UTS) |
| **"How should this evolve?"** — Change management, versioning, lifecycle | Evolution loops, design-run duality, design rationale records | B.4 (Evolution Loop), A.4 (Temporal Duality), E.9 (DRR) |
| **"How to frame the problem?"** — Structuring inquiry, hypothesis generation | Canonical reasoning cycle, abductive loop, explore-shape-evidence-operate | B.5 (Reasoning Cycle), B.5.1 (Explore→Shape→Evidence→Operate), B.5.2 (Abductive Loop) |
| **"How to generate creative alternatives?"** — Systematic ideation, portfolio search | Creativity characterization, novelty-quality-diversity, explore-exploit | C.17 (Creativity-CHR), C.18 (NQD-CAL), C.19 (E/E-LOG), B.5.2.1 (Creative Abduction) |
| **"Who does what and why?"** — Roles, responsibilities, accountability | Role-method-work alignment, contextual enactment, separation of duties | A.2 (Roles), A.15 (Role-Method-Work), A.2.1 (Role Assignment), A.13 (Agency) |
| **"How to make this decision auditable?"** — Traceability, rationale capture | Design rationale records, evidence graphs, assurance levels | E.9 (DRR), A.10 (Evidence Graph), B.3.3 (Assurance Levels) |
| **"How to compare across different contexts?"** — Cross-domain alignment with loss awareness | Bridges with congruence levels, cross-context mapping, loss notes | F.9 (Bridges), A.6.9 (Cross-Context Sameness), C.3.3 (KindBridge) |
| **"What are the boundary contracts?"** — Interface discipline, promise vs. work | Boundary norm routing, contract unpacking, service facets | A.6 (Signature Stack), A.6.B (Boundary Norm Square), A.6.C (Contract Unpacking), A.6.8 (Service Polysemy) |
| **"How should an AI agent plan its tool use?"** — Call planning, tool selection, role-bound action | Agentic tool-use calculus, role-method-work alignment | C.24 (Agentic Tool-Use & Call Planning), A.15 (Role-Method-Work), A.13 (Agency Spectrum) |
| **"Which option do we choose (under uncertainty)?"** — Decision-making, selection policy | Decision theory, explore-exploit governance | C.11 (Decision Theory), C.19 (Explore-Exploit), C.18 (NQD search) |
| **"Is X actually causing Y?"** — Causal claims, counterfactuals, intervention | Causal-use questions, causality ladder, identification | C.28 (CausalUse-CAL) |
| **"Will this hold over time?"** — Forecasts, trends, state-vs-rate claims | Temporal claim adequacy, state readings, trends | C.27 (Temporal Claim Adequacy) |
| **"What are the ethical trade-offs?"** — Value conflict across levels, bias, mediation | Multi-scale ethics, interlevel conflict, ethical mediation | D.1 (Value Plurality), D.2 (Multilevel Ethics), D.3 (Interlevel Conflict), D.4 (Mediation), D.5 (Bias Audit) |
| **"Design or critique an architecture."** — Structure selection, modularity, synthesis | Grounded architecture, modularity, candidate synthesis, structural adequacy | C.30 (Grounded Architecture), C.31 (Modularity), C.32 (Candidate Synthesis), C.33–C.35 (Structural Adequacy) |
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
| Loading the full ~9.3MB spec | Floods context, agent can't reason | Grep for section headers, Read targeted ranges |
| Using FPF jargon in output | User asked for plain language; jargon obscures | Translate every FPF concept to everyday terms |
| Treating FPF as a checklist | FPF is generative, not prescriptive | Use patterns to structure thinking, not to tick boxes |
| Applying all sections at once | Overwhelming; most problems need 2-3 sections | Use routing table to select relevant sections only |
| Skipping evidence assessment | Claims without trust evaluation are folklore | Always produce a Trust Assessment for key claims |
| Single-winner conclusions | FPF emphasises portfolios and Pareto fronts | Present options as a set with trade-offs, not "the answer" |

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
