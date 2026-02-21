---
name: fpf-thinking
description: >
  First Principles Framework (FPF) integration for systems thinking.
  Provides protocol for using the FPF spec as a RAG resource, routing table
  mapping problem types to spec sections, and artifact recipes.
  For complex problems beyond software: project characterization, domain
  vocabulary, naming discipline, principles-to-work mapping, SoTA harvesting.
  Triggers on: systems thinking, first principles, FPF, characterization,
  domain vocabulary, UTS, P2W, SoTA, holonic, bounded context (systems),
  trust calculus, evidence graph, think, analyse complex.
---

# FPF-Guided Systems Thinking

Protocol for using the First Principles Framework as a structured reasoning aid for complex systems problems.

---

## Spec Location

The full FPF spec is at `~/.claude/docs/FPF-Spec.md` (~50,000 lines, ~4.4MB).

**Never load the full file.** Use Grep and targeted Read (offset + limit) to retrieve relevant sections on demand. The routing table below maps problem types to section line ranges.

---

## Loading Protocol

From FPF README (mandatory):

1. **Use FPF patterns to structure your analysis** — apply the framework's reasoning architecture
2. **Respond in plain language** — no FPF-specific terminology in output unless the user explicitly requests it
3. **FPF steers, you think** — the framework is a scaffold for reasoning, not a substitute for it. Without good problem framing, you get confident nonsense

---

## Routing Table

When facing a complex problem, identify the problem type and read the corresponding FPF sections.

### How to navigate the spec

The spec uses `## Section-ID - Title` headers. Use Grep to find section starts:
```
Grep(pattern="^## A\\.1 ", path="~/.claude/docs/FPF-Spec.md")
```
Then Read with offset/limit from the matched line number (~200-400 lines per section).

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
| Loading the full 4.4MB spec | Floods context, agent can't reason | Grep for section headers, Read targeted ranges |
| Using FPF jargon in output | User asked for plain language; jargon obscures | Translate every FPF concept to everyday terms |
| Treating FPF as a checklist | FPF is generative, not prescriptive | Use patterns to structure thinking, not to tick boxes |
| Applying all sections at once | Overwhelming; most problems need 2-3 sections | Use routing table to select relevant sections only |
| Skipping evidence assessment | Claims without trust evaluation are folklore | Always produce a Trust Assessment for key claims |
| Single-winner conclusions | FPF emphasises portfolios and Pareto fronts | Present options as a set with trade-offs, not "the answer" |

---

## Integration Notes

- This skill is for **systems thinking**, not code. It does not replace language-specific engineering skills
- Agents should use `mcp__sequentialthinking` alongside FPF for multi-step reasoning
- When the user says "think about X" or uses `/think`, activate this skill's routing table
- The FPF spec evolves — check `~/.claude/docs/FPF-Spec.md` freshness if patterns seem outdated
