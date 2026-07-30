---
name: fpf-thinking
description: First Principles Framework (FPF) protocol for systems thinking, domain modelling, and architectural trade-offs. Use when tackling complex analysis, first-principles reasoning, project characterisation, or naming discipline. Not to be confused with `mcp-sequential-thinking` (step-by-step reasoning), `diverge-synthesize-select` (option generation + choice), or `narrative-thinking` (rendering already-framed material as narrative, explanation, or learning route) — FPF frames the problem itself.
problem: "Complex systems problems get solved before they are framed, producing well-executed answers to the wrong question."
related: [diverge-synthesize-select, mcp-sequential-thinking, narrative-thinking]
---

# FPF-Guided Systems Thinking

Protocol for using the First Principles Framework as a structured reasoning aid for complex systems problems.

---

## Spec Location

The full FPF spec is at `~/.claude/docs/FPF-Spec.md`. It is a very large monolith spanning eight Parts A–G and I (Part H is reserved) and grows edition to edition, so **navigate by id, never by absolute line number**. Ids are stable; line counts, file size, and heading counts drift.

**Never load the full file.** Use Grep and targeted Read (offset + limit) to retrieve relevant sections on demand. The routing table below maps problem types to section *ids*; resolve each id to its current line with Grep, then Read from there.

---

## Loading Protocol

From FPF README (July 2026 edition, mandatory):

1. **Use FPF patterns to structure your analysis** — apply the framework's reasoning architecture
2. **Respond in plain language** — keep the answer readable for engineer-managers. Let an FPF term enter only when it makes the reasoning more precise; never as decoration or proof of effort
3. **FPF steers, you think** — the framework is a scaffold for reasoning, not a substitute for it. Without good problem framing, you get confident nonsense
4. **Enter via a Practical-Use Card, not a pattern id.** Recognise the current situation and question, pick the card (see Card Index below), then inspect **only** the branch whose stated condition is current and open that pattern's `Solution`. Materialise comparison, archive, or ordering records only when a named receiving use relies on them
5. **Close with the Result test** — every one of the fifteen cards now ends with it. An answer that skips it is not an FPF answer. See the next section
6. **Pattern-use coordination is a separate relation.** Once one direct pattern is current, `E.11.PUA` governs applying it and returning the smallest independently governed result usable now; `E.11.PUR` applies only when a named receiving use needs an addressable applicability finding, recommendation, coordination, or ordering relation. `E.11` itself is discovery guidance — it is *not* the card index; the cards live in the spec's README section

---

## Result Test (mandatory close)

The July 2026 edition ends **every** practical-use card with a Result test. It is the acceptance gate for an FPF answer, and it is the part most easily faked by producing a nice-looking document.

For the selected branch, answer three questions in this order:

1. **What exact kind could be returned?** Name the result kind the branch actually promises — `ProblemCard@Context`, `ChoiceResult`, `Assurance(H, C | K, S)`, `NameCard`, `EvaluationCharacteristicSpaceSpec`, `U.WorkPlan`, dated `U.Work`, … — and how its direct pattern would identify it or make its relation obtain.
2. **Which use-object does it answer?** Name the exact method, plan, dated `U.Work`, transformation, evaluation, decision, gate, or publication occurrence that would use the result.
3. **What makes it the result *for that object*?** Name the direct relation occurrence, `A.6.1` application binding, or well-formed local claim.

Three hard rules:

- **A branch is a promise, not a delivery.** Selecting a branch states what a later use *could* return, or an honest stop. It does not assert that a project result already exists.
- **Missing governor beats a weakened promise.** When a needed governor or fact is absent, stop and say exactly what is missing. Never soften the claim so the answer can land.
- **Carriers are not results.** A generated note, measurement, dashboard, ticket, log, or plan does not stand for machining, treatment, organisational change, learning, or any other downstream result.

Name a next pattern only when that continuation is actually current.

---

## Pattern Anatomy

FPF is a **pattern language**: nearly every concept section (an id like `A.2.1`, `C.11`, `E.9`) is written to one canonical template. The sub-headings inside a section are addressed with a colon — `A.2.1:4` is the Solution slot of pattern `A.2.1`. The table below is the *majority* layout, not a guarantee; see the caveat under it.

| Slot | Canonical name | Typical content | Almost always present |
|---|---|---|---|
| `:0` | Use This When | Applicability / entry cue | sometimes (~85 patterns) |
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
| `:End` | *(sentinel)* | Empty marker — ends the pattern | yes (288 patterns) |

How to use the anatomy:

- **Slot numbers drift; enumerate before you read.** Measured on the July 2026 edition: `Solution` sits at `:4` in 241 of 275 patterns (88%) but also turns up at `:2`, `:3`, `:5`, `:6`, and `:7`; `Conformance Checklist` sits at `:7` in only 173 of 258 (67%), at `:6` in 40 more, and as far out as `:21`. **Grep the id with an open slot — `^#+ C\.11:` — to list that pattern's actual slots, then Read the one you want.**
- **Slot titles are the more reliable handle.** When you know what you want but not where it sits, grep title + wildcard number: `^#+ C\.11:[0-9]+ - Conformance`. Titles do vary in wording (`Conformance Checklist (normative)`, `Common Anti-Patterns and How to Avoid Them`), so anchor on the distinctive word, not the full string.
- **Targeted retrieval.** For "what does A.2.1 *require*?" read its Conformance Checklist, not the whole section. For "why?" read Rationale. For "how does it connect?" read Relations.
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
Then Read with offset/limit from the matched line number (~200-400 lines per section). To jump *inside* a section, first enumerate its slots (`^#+ A\\.2\\.1:`) as described under Pattern Anatomy.

### Practical-Use Card Index (primary entry)

The July 2026 readme organises entry through fifteen semantic cards. Recognise the situation, pick the card, inspect the listed direct patterns' Solutions, and stop at the exact first useful result — then run the Result test. The card keys below are stable identifiers, not steps; do not read them in order.

| Card key | Situation cue (one line) | Direct patterns (branch = template) |
|---|---|---|
| **ARCHITECTURE** | Problem pressure must become candidate, selected, expected, or actual structures | `C.32.P2S` (flow) · `C.30.AD` (existing description) |
| **WORKING-DOCUMENTS** | Document a participant will use — first pick a branch: meaning, enactment, reliance, or publication | Meaning: `A.6`, `A.3.2`, `A.2.8`, `A.2.8.PER`, `A.6.RSIR` · Enactment: `A.15.2`, `C.24`, `A.15.5` · Reliance: `A.10`, `B.3`, `A.21` · Publication: `E.17` |
| **OPTION-COMPARISON** | Several options — the current need is comparison frame, archive, front, live pool, published set, or one choice | `A.19.ECS`, `C.18`, `C.19`, `G.5`, `C.11` |
| **PROBLEM-SHAPING** | Vague pressure — how far has articulation actually progressed? | `A.16.1`, `B.4.1`, `B.5.2.0`, `C.22.2` (then `C.22` for TaskSignature) |
| **IMPROVEMENT** | Object should improve, but evaluation purpose/scale/proposal effect is unsettled | `E.22`, `C.25`, `A.19.ECS`, `E.23` |
| **COSTLY-ACTION** | Expensive, committing, safety-relevant, or hard-to-reverse action | `A.10`, `B.3`, `A.20`, `A.21`, `C.28`, `C.11`, `A.15.5` |
| **TIME** | Rate, rhythm, delay, currentness, or validity-window claim used for action | `C.27`, `G.11` |
| **CAUSAL-USE** | Causal, intervention, effect, or counterfactual language supporting a decision | `C.28` |
| **DESCRIPTION-USE** | Description, view, dashboard, model, report, or publication being created or relied on | `E.17.0` (episteme identified under `C.2.1`), `A.6.3.RT`, `C.33`, `E.17.ID.CR`, `C.30.AD` |
| **NAMING** | A governed value needs a stable Tech or Plain label across a bounded context | `F.18` → `F.17` gate only when a public row is current → `E.24.PUB` for publication |
| **WORDING** | Fluent sentence leaves the reader unable to tell what it says about the project | `E.10` (relation-like branch: `A.6.5` SlotSpec, `A.6.P`, `A.6.RCD`, `A.6.P.WMR`; then `F.19` for prose, `F.18` for durable naming) |
| **MATHEMATICAL-MODELING** | Could one cheap mathematical lens change the next admissible action? | `C.29` |
| **SOTA-PORTFOLIO** | Need the plural current field of methods, theories, technologies, or sources | `G.2` (then `C.18`, `C.19`, `G.5` as conditional continuations) |
| **DPF-AUTHORING** | Building a reusable FPF-grounded domain or local practice framework edition | `E.4.DPF` (proposal), `E.4.PFAD` (decision), `C.30.AD`, `E.4.DPF` (dependency description) |
| **SYSTEM-IN-CONTEXT** | System named but the current system question (identity, composition, participation, structures, planned or performed work, production) is not explicit | `A.1`, `B.1.2`, *direct subject pattern*, `C.30`, `A.15.2`, `A.15.1`, `A.15.PROD` |

> Each row lists the ordinary walkthrough — inspect only the branch whose stated condition is current in the working project, not every listed pattern. When multiple cards seem plausible, compare their situations, first-result differences, and stop/return conditions in the conversation before opening any pattern body.
>
> **Stronger neighbours are not templates.** Card bodies list neighbours to escalate to (e.g. ARCHITECTURE names `C.32`, `C.32.PAD`, `A.15`, `E.23`, `G.11`; TIME names `C.16`, `C.28`, `A.15`). Open a neighbour only when the next claim is actually current — do not treat it as one of the card's branches.
>
> **Outside the fifteen cards:** when independently identified transformation-flow structures must be joined through exact direct relation occurrences (build-the-builder, product vs production system), the readme routes to `E.18.NET`. Several stages, paths, or valuations of *one* flow stay in `E.18`; bounded transformations over admitted positions go to `E.18.3`.

### Problem → Section Map (semantic fallback)

Use this when the current question does not obviously match a card key — e.g. cross-cutting theory questions, meta-authoring questions, or historical inspection.

| Problem Type | What You Need | FPF Sections to Read |
|---|---|---|
| **"What is this system/project?"** — Bounding and decomposing a complex entity | Holonic decomposition, boundary definition, context scoping | A.1 (Holonic Foundation), A.1.1 (Bounded Model-Use Structure), A.2 (Role Taxonomy) |
| **"How confident are we in X?"** — Evaluating trust in claims, evidence, assumptions | Trust calculus, evidence graphs, epistemic debt | B.3 (Trust & Assurance F-G-R), A.10 (Evidence Graph), B.3.4 (Evidence Decay) |
| **"How do we define and measure success?"** — Establishing measurable characteristics | Measurement typing, comparability governance, indicators, currentness | A.17-A.18 (Characteristics, CSLC), A.19.CN (CN-frame), G.0 (CG-Spec), G.11 (Currentness) |
| **"What are the options / state of the art?"** — Surveying and comparing alternatives | SoTA packs, method families, portfolio selection, currentness | Part G (G.0-G.10), C.18 (NQD search), C.19 (E/E-LOG), G.11 (Currentness) |
| **"How do parts compose into a whole?"** — Aggregation, composition, emergence | Universal aggregation algebra, cross-scale invariants, mereology | B.1 (Gamma), A.14 (Mereology), A.9 (Cross-Scale), B.2 (Meta-Holon Transition) |
| **"What does this term actually mean?"** — Vocabulary alignment, disambiguation | Term harvesting, sense clustering, bridges, unified term sheets | F.0.1-F.3 (Lexical Principles, Harvesting, Clustering), F.9 (Bridges), F.17 (UTS), F.18 (NameCard) |
| **"How should this evolve?"** — Change management, versioning, lifecycle | Evolution loops, design-run duality, design rationale records, problem-to-work carry-through | B.4 (Evolution Loop), A.4 (Temporal Duality), E.9 (DRR), E.18.1 (P2W Problem-to-Work Carry-Through) |
| **"How do several flows hang together?"** — Build-the-builder, product vs production system, delivery chains | Transformation-flow structure, networks of flows, project/process/case recovery | E.18 (Transformation Flow Structure), E.18.NET (Network of TFS), E.18.3 (bounded transformations), A.15.6 (Project/Process/Case Recovery) |
| **"How to frame the problem?"** — Structuring inquiry, pattern-use rhythm, hypothesis generation | Practical-use guidance, canonical reasoning cycle, abductive loop | E.11 (Practical-Use Guidance), E.11.PUA (Apply Pattern to Situation), E.11.PUR (Applicability & Coordination), B.5 (Reasoning Cycle), B.5.2 (Abductive Loop) |
| **"How to generate creative alternatives?"** — Systematic ideation, portfolio search | Creativity characterisation, novelty-quality-diversity, explore-exploit | C.17 (Creativity-CHR), C.18 (NQD-CAL), C.19 (E/E-LOG), B.5.2.1 (Creative Abduction) |
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

These are **renderings**, not results. The result is identified under its direct pattern; a rendering only makes it readable, and it inherits the Result test above. Each recipe names the FPF result kind it renders — when a recipe has no single result kind, say so rather than presenting the document as an FPF result.

### 1. System Characterisation Card

**When:** Decomposing a complex system or project.
**FPF source:** A.1, A.1.1, A.2. **Renders:** the A.1 candidate holon-recognition result or an exact direct delimitation claim.

- **Name** — what is this system/entity
- **Boundary** — what is inside vs. outside (and what crosses the boundary)
- **Parts** — sub-systems, components, or sub-domains
- **Roles** — who/what is responsible for what (function, not identity)
- **Context rules** — the local vocabulary, invariants, and assumptions that hold inside this boundary
- **Bridges** — explicit links to other contexts, with notes on what meaning is lost in translation

### 2. Trust Assessment

**When:** Evaluating confidence in a claim, requirement, or assumption.
**FPF source:** B.3, A.10. **Renders:** `Assurance(H, C | K, S)` — or an explicit no-assurance-claim disposition — over A.10's claim-bound evidence-provenance graph relation.

- **Claim** — the statement being assessed
- **Formality (F)** — how rigorous is the backing? (sketch / spec / formal proof)
- **Scope (G)** — where does this claim hold? (this project / this domain / universally)
- **Reliability (R)** — how strong is the evidence? (anecdotal / tested / independently verified)
- **Evidence chain** — what supports this claim, and is there decay risk?
- **Verdict** — unsubstantiated / partially supported / well-evidenced, **or** an explicit no-assurance disposition

### 3. Measurement & Comparability Frame

**When:** Defining what "success" or "good" means; comparing alternatives.
**FPF source:** A.19.ECS, A.17-A.19, G.0. **Renders:** `EvaluationCharacteristicSpaceSpec`.

- **Characteristics** — what properties matter (and their scale types: ordinal, interval, ratio)
- **Indicators** — how each characteristic is measured
- **Comparability rules** — what can be compared to what, and under which conditions
- **Aggregation policy** — how individual scores compose (no hidden averages)
- **Protected trade-offs** — what may not be silently traded away

### 4. Naming Card (UTS Entry)

**When:** Aligning vocabulary across teams, disciplines, or contexts.
**FPF source:** F.18, F.0.1-F.9. **Renders:** a `NameCard` (a `C.2.1` episteme). A public `F.17` term row is a *separate* result — reach for it only when public, Core-facing, or cross-context reuse is current; `E.24.PUB` governs publishing that row.

- **Governed value** — the exact thing being named, and its direct governing pattern (recover this *first*)
- **Context & sense** — effective by-value reference scheme, local sense, intended use
- **Designations** — selected Tech and Plain labels
- **Candidates & rejections** — smallest candidate set covering live head-term families, plus why each was rejected
- **Bridges** — actual F.9 links to other contexts (with loss notes)
- **Reopen condition** — the smallest change that reopens this settlement

### 5. Design Rationale Record (DRR)

**When:** Capturing why a decision was made, for future auditability.
**FPF source:** E.9. **Renders:** the DRR. The decision itself is a `C.11 ChoiceResult` — the record does not make the choice.

- **Decision** — what was decided
- **Context** — what situation prompted this decision
- **Options considered** — alternatives that were evaluated (portfolio, not single winner)
- **Selection rationale** — why this option, with evidence references
- **Consequences** — what changes and what risks remain
- **Review trigger** — when should this decision be revisited

### 6. Evolution Roadmap

**When:** Planning how a system, process, or body of knowledge should change over time.
**FPF source:** B.4, A.4. **Renders:** no single FPF result kind — this is a working aid. When a repeated improvement loop is genuinely current, the result is `E.23 QualityImprovementLoopRecord`; when the plan is dated intended work, it is an `A.15.2 U.WorkPlan`.

- **Current state** — where we are (with evidence)
- **Target state** — where we want to be (with measurable characteristics)
- **Evolution steps** — sequence of changes (each auditable)
- **Feedback loops** — how we detect drift and course-correct
- **Evidence refresh** — when to re-validate assumptions

### 7. SoTA Pack

**When:** Surveying the state of the art in a domain or method family.
**FPF source:** G.2, Part G. **Renders:** `SoTA Synthesis Pack@CG-Frame` with its `SoTA_Set@CG-Frame` and `SoTAPaletteDescription`.

- **Scope** — what discipline/domain/method family
- **Traditions** — major schools of thought or approaches (rivals kept, not merged)
- **Method families** — grouped alternatives with evidence anchors
- **Comparison frame** — characteristics used to compare (from Artifact 3)
- **Portfolio** — the set of viable alternatives (not a single "winner")
- **Gaps** — where evidence is missing or stale

> Archive (`C.18`), live pool (`C.19`), and published shortlist (`G.5`) are different results with different membership and policy — no prose summary may collapse them into "the options".

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Instead |
|---|---|---|
| Loading the full spec | Floods context, agent can't reason | Grep for section ids, Read targeted ranges |
| Using FPF jargon in output | User asked for plain language; jargon obscures | Translate to everyday terms; admit a term only when it makes reasoning more precise |
| Treating FPF as a checklist | FPF is generative, not prescriptive | Use patterns to structure thinking, not to tick boxes |
| Applying all sections at once | Overwhelming; most problems need 2-3 sections | Use routing table to select relevant sections only |
| Skipping evidence assessment | Claims without trust evaluation are folklore | Always produce a Trust Assessment for key claims |
| Single-winner conclusions | FPF emphasises portfolios and Pareto fronts | Present options as a set with trade-offs, not "the answer" |
| **Ending with a document instead of a named result** | A card, note, or dashboard is a carrier — the receiving use gets nothing it can rely on | Run the Result test: result kind → receiving use-object → the relation/binding that makes it that use's result |
| **Weakening a promise to avoid stopping** | Produces confident output with no governor behind it | Stop and name the exact missing governor, fact, or basis |
| **Treating a selected branch as delivered** | A branch says what a later use *could* return, not that a result exists | Say what would be returned and under which condition; only then produce it |
| Reading all 15 Practical-Use Cards before picking one | Each card is a stable identifier, not a step; enumeration wastes context | Recognise the situation, pick one card, follow its ordinary rhythm |
| Treating a card's stronger neighbours as its branches | Neighbours are escalation targets for the *next* claim, not templates to walk | Open a neighbour only when its claim is current |
| Conflating `E.11`, `E.11.PUA`, and `E.11.PUR` | They govern different relations — discovery guidance, pattern application, and applicability/coordination | `E.11` for discovery, `E.11.PUA` to apply one direct pattern, `E.11.PUR` only when reliance-bearing applicability or coordination is current |
| Materialising archive, front, shortlist, or ordering records eagerly | The July readme keeps ordinary comparison conversational | Materialise only when a named receiving use relies on the record |
| **Grepping a slot number without enumerating slots** | Slot numbering is not stable — `:7` is the Conformance Checklist only 67% of the time | Grep `^#+ <id>:` first to list the pattern's actual slots |

---

## Integration Notes

- This skill is for **systems thinking**, not code. It does not replace language-specific engineering skills
- Agents should use `mcp__sequentialthinking` alongside FPF for multi-step reasoning
- When the user says "think about X" or uses `/techne-think`, activate this skill's routing table
- The FPF spec evolves — check `~/.claude/docs/FPF-Spec.md` freshness if patterns seem outdated. `make validate-claude` verifies that every id cited here still resolves in the vendored spec

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

## Result

<!-- Result test: the exact result kind, the use-object it answers, and the relation/binding
     that makes it that use's result. If a governor is missing, name it here instead. -->

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
